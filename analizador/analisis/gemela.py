"""V3: índices y plan elegidos juntos, en una base gemela con HypoPG.

El servidor del usuario solo se lee (columnas, claves, índices y pg_stats, en una
conexión de solo lectura). Con esas estadísticas se arma una base "gemela" en un
PostgreSQL propio de la aplicación (GEMELA_DSN en el .env), con datos sintéticos
que siguen la misma distribución, y ahí se prueban índices hipotéticos con HypoPG.
Así nunca se instala nada ni se crea un índice en el servidor del usuario.

Es lo mismo que los bloques 11.1 y 11.2 de ml/modelo_ml_v1_v2_v3.ipynb, para una
sola consulta: la V2 propone candidatos y su mejora, el modelo de planes estima
el tiempo de cada variante del plan con y sin esos índices, y se combinan con los
pesos aprendidos. Un índice entra solo si baja el tiempo más que el corte.
"""
import hashlib
import logging
import threading
import time

import numpy as np
import psycopg
from psycopg import sql

from analizador.analisis import indices_ml
from analizador.analisis.orden_join import COSTO_DESACTIVADO, _describir, _variantes, sql_optimizado
from analizador.analisis.plan_parser import raiz, recorrer
from analizador.conexion import get_db_config, get_readonly_connection
from backend.config import GEMELA_DSN

log = logging.getLogger("analizador.gemela")

MAX_FILAS_GEMELA = 2_000_000      # por tabla; más que eso no se copia
VIGENCIA_S = 24 * 3600            # después de un día la gemela se vuelve a armar
SEMILLA = 42
_candado = threading.Lock()

def configurada() -> bool:
    return bool(GEMELA_DSN.strip())

# --- Lectura del servidor (bloque 11.1) ---

def leer_servidor(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT table_name, column_name, data_type FROM information_schema.columns c "
                    "JOIN pg_class k ON k.relname = c.table_name AND k.relkind IN ('r', 'p') "
                    "AND k.relnamespace = 'public'::regnamespace "
                    "WHERE table_schema = 'public' ORDER BY table_name, ordinal_position")
        columnas = {}
        for t, c, tipo in cur.fetchall():
            columnas.setdefault(t, []).append((c, tipo))
        cur.execute(indices_ml.SQL_CLAVES_PRIMARIAS)
        claves = {}
        for t, c in cur.fetchall():
            claves.setdefault(t, []).append(c)
        cur.execute("SELECT indexdef FROM pg_indexes i JOIN pg_index x ON x.indexrelid = "
                    "(quote_ident(i.schemaname) || '.' || quote_ident(i.indexname))::regclass "
                    "WHERE i.schemaname = 'public' AND NOT x.indisprimary")
        indices = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT relname, reltuples FROM pg_class WHERE relnamespace = 'public'::regnamespace "
                    "AND relkind IN ('r', 'p')")
        filas = {t: int(max(n, 0)) for t, n in cur.fetchall()}
        cur.execute("SELECT tablename, attname, null_frac, n_distinct, most_common_vals::text::text[], "
                    "most_common_freqs, histogram_bounds::text::text[], correlation, avg_width "
                    "FROM pg_stats WHERE schemaname = 'public'")
        stats = {(r[0], r[1]): dict(nulos=r[2] or 0, distintos=r[3] or 0, frecuentes=r[4] or [],
                                    frecuencias=r[5] or [], histograma=r[6] or [], correlacion=r[7] or 0,
                                    ancho=r[8] or 8) for r in cur.fetchall()}
    conn.rollback()
    return dict(columnas=columnas, claves=claves, indices=indices, filas=filas, stats=stats)

# --- Datos sintéticos con la misma distribución (bloque 11.1) ---

NUMERICOS = ("integer", "bigint", "smallint", "numeric", "real", "double precision")
TEXTO = ("text", "character varying", "character")

def a_numero(valores, tipo):
    if tipo == "date":
        return np.array(valores, dtype="datetime64[D]").astype(np.int64).astype(float)
    return np.array(valores, dtype=float)

def de_numero(v, tipo):
    if tipo == "date":
        return np.round(v).astype(np.int64).astype("datetime64[D]").astype(str)
    if tipo in ("integer", "bigint", "smallint"):
        return np.round(v).astype(np.int64)
    return np.round(v, 2)

def columna_gemela(st, tipo, n, es_clave, rng):
    texto = tipo not in NUMERICOS and tipo != "date"
    hist = st["histograma"]
    if es_clave:
        if texto or len(hist) < 2:
            return np.arange(n) if tipo in NUMERICOS else np.array([f"g{i}" for i in range(n)], dtype=object)
        lo, hi = a_numero([hist[0], hist[-1]], tipo)
        return de_numero(lo + np.floor(np.arange(n) * max(1.0, (hi - lo) / max(n - 1, 1))), tipo)
    if tipo in TEXTO and st["distintos"] < -0.5:
        return np.array([f"g{i}".ljust(max(1, st["ancho"] - 1), "x") for i in range(n)], dtype=object)
    partes = []
    for valor, frecuencia in zip(st["frecuentes"], st["frecuencias"]):
        partes.append(np.full(int(round(frecuencia * n)), valor, dtype=object))
    resto = max(0, n - sum(len(p) for p in partes) - int(round(st["nulos"] * n)))
    if resto and len(hist) >= 2:
        tramo = rng.integers(0, len(hist) - 1, resto)
        if texto:
            partes.append(np.array(hist, dtype=object)[tramo + rng.integers(0, 2, resto)])
        else:
            limites = a_numero(hist, tipo)
            v = limites[tramo] + rng.random(resto) * (limites[tramo + 1] - limites[tramo])
            partes.append(de_numero(v, tipo).astype(object))
    elif resto and st["frecuentes"]:
        p = np.array(st["frecuencias"], dtype=float)
        partes.append(np.array(st["frecuentes"], dtype=object)[rng.choice(len(p), resto, p=p / p.sum())])
    valores = np.concatenate(partes) if partes else np.array([], dtype=object)
    valores = np.concatenate([valores, np.full(max(0, n - len(valores)), None, dtype=object)])[:n]
    rng.shuffle(valores)
    corr = st["correlacion"]
    if abs(corr) >= 0.3 and not texto:
        no_nulos = np.array([v is not None for v in valores], dtype=bool)
        orden = np.sort(a_numero(valores[no_nulos].tolist(), tipo))
        if corr < 0:
            orden = orden[::-1]
        desordenar = rng.choice(len(orden), int(len(orden) * (1 - abs(corr))), replace=False)
        orden[desordenar] = orden[rng.permutation(desordenar)]
        valores = np.concatenate([de_numero(orden, tipo).astype(object), valores[~no_nulos]])
    return valores

def _texto(v):
    return None if v is None else str(v)

# --- Armar y reutilizar la gemela ---

def nombre_gemela(config: dict) -> str:
    cfg = get_db_config(config)
    clave = f"{cfg['host']}:{cfg['port']}:{cfg['dbname']}"
    return "gemela_" + hashlib.md5(clave.encode()).hexdigest()[:12]

def _conectar(base: str | None = None) -> psycopg.Connection:
    return psycopg.connect(GEMELA_DSN, **({"dbname": base} if base else {}), autocommit=True)

def _vigente(nombre: str) -> float | None:
    """Segundos desde que se armó la gemela, o None si no existe."""
    with _conectar() as admin:
        if not admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nombre,)).fetchone():
            return None
    try:
        with _conectar(nombre) as c:
            creada = c.execute("SELECT extract(epoch FROM now() - creada) FROM gemela_info").fetchone()
            return float(creada[0])
    except psycopg.Error:
        return None

def armar(config: dict | None, nombre: str) -> dict:
    with get_readonly_connection(config) as conn:
        info = leer_servidor(conn)
    grandes = [t for t, n in info["filas"].items() if n > MAX_FILAS_GEMELA]
    if grandes:
        raise ValueError(f"tablas demasiado grandes para la base gemela: {', '.join(sorted(grandes))}")
    with _conectar() as admin:
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(nombre)))
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
    rng = np.random.default_rng(SEMILLA)
    with _conectar(nombre) as c:
        c.execute("CREATE EXTENSION IF NOT EXISTS hypopg")
        for t, cols in info["columnas"].items():
            n = info["filas"].get(t, 0)
            una_clave = info["claves"].get(t, [None])[0] if len(info["claves"].get(t, [])) == 1 else None
            ddl = sql.SQL(", ").join(
                sql.SQL("{} {}{}").format(sql.Identifier(col), sql.SQL(tipo),
                                         sql.SQL(" PRIMARY KEY" if col == una_clave else ""))
                for col, tipo in cols)
            c.execute(sql.SQL("CREATE TABLE {} ({})").format(sql.Identifier(t), ddl))
            if not n:
                continue
            datos = []
            for col, tipo in cols:
                st = info["stats"].get((t, col))
                if st is None:
                    datos.append(np.full(n, None, dtype=object))
                    continue
                try:
                    datos.append(columna_gemela(st, tipo, n, col == una_clave, rng))
                except (ValueError, TypeError):
                    datos.append(np.full(n, None, dtype=object))
            nombres = sql.SQL(", ").join(sql.Identifier(col) for col, _ in cols)
            with c.cursor() as cur, cur.copy(sql.SQL("COPY {} ({}) FROM STDIN").format(sql.Identifier(t), nombres)) as cp:
                for fila in zip(*datos):
                    cp.write_row([_texto(v) for v in fila])
        for ddl in info["indices"]:
            try:
                c.execute(ddl)
            except psycopg.Error as exc:
                log.warning("Índice no copiado a la gemela (%s): %s", ddl, exc)
        c.execute("ANALYZE")
        c.execute("CREATE TABLE gemela_info AS SELECT now() AS creada")
    return {"tablas": len(info["columnas"]), "filas": sum(info["filas"].values())}

def asegurar(config: dict | None, reconstruir: bool = False) -> tuple[str, dict]:
    nombre = nombre_gemela(config)
    with _candado:
        edad = None if reconstruir else _vigente(nombre)
        if edad is not None and edad < VIGENCIA_S:
            return nombre, {"recien_armada": False, "edad_min": round(edad / 60, 1)}
        inicio = time.time()
        datos = armar(config, nombre)
        return nombre, {"recien_armada": True, "edad_min": 0.0,
                        "segundos_en_armar": round(time.time() - inicio, 1), **datos}

# --- Búsqueda conjunta (bloque 11.2) ---

def forma_del_plan(plan) -> tuple:
    return tuple((n.get("Node Type"), n.get("Relation Name")) for n, _ in recorrer(raiz(plan)))

def _explain(cur, query: str, ajustes: dict) -> dict:
    cur.execute("BEGIN")
    try:
        cur.execute("SET LOCAL statement_timeout = '5s'")
        for nombre, valor in ajustes.items():
            v = valor if isinstance(valor, int) and not isinstance(valor, bool) else ("on" if valor else "off")
            cur.execute(f"SET LOCAL {nombre} = {v}")
        cur.execute("EXPLAIN (FORMAT JSON) " + query)
        return raiz(cur.fetchone()[0])
    finally:
        cur.execute("ROLLBACK")

class Planificador:
    """Mejor plan predicho para la consulta en la gemela con un conjunto de índices
    hipotéticos (como mejor_plan() del notebook). Guarda lo ya calculado."""

    def __init__(self, cur, query: str, n_tablas: int, umbral: float):
        self.cur, self.query, self.n_tablas, self.umbral = cur, query, n_tablas, umbral
        self.cache = {}
        self.defecto = {}  # tiempo del plan con la configuración por defecto

    def mejor(self, indices) -> tuple[float, dict, dict]:
        clave = tuple(sorted(indices))
        if clave in self.cache:
            return self.cache[clave]
        self.cur.execute("SELECT hypopg_reset()")
        for t, c in clave:
            ddl = sql.SQL("CREATE INDEX ON {} ({})").format(sql.Identifier(t), sql.Identifier(c)).as_string(self.cur)
            self.cur.execute("SELECT * FROM hypopg_create_index(%s)", (ddl,))
        opciones, vistas = [], set()
        for ajustes in [{}] + list(_variantes()):
            try:
                plan = _explain(self.cur, self.query, ajustes)
            except psycopg.Error:
                if not ajustes:
                    raise
                continue
            firma = forma_del_plan(plan)
            if firma in vistas or (ajustes and (raiz(plan).get("Total Cost") or 0) >= COSTO_DESACTIVADO):
                continue
            vistas.add(firma)
            t = indices_ml.predecir_ms(plan, self.n_tablas)
            if not ajustes:
                self.defecto[clave] = t
            # Igual que el umbral de la V1: el plan de PostgreSQL gana si la mejora es chica.
            opciones.append((t * (1 - self.umbral) if not ajustes else t, t, ajustes, plan))
        _, t, ajustes, plan = min(opciones, key=lambda o: o[0])
        self.cache[clave] = (t, ajustes, plan)
        return self.cache[clave]

def tiempo_combinado(planificador, indices, mejoras_idx: dict, pesos) -> float:
    t0 = planificador.mejor([])[0]
    m_p = 1 - planificador.mejor(indices)[0] / max(t0, 1e-6)
    m_i = max([0.0] + [mejoras_idx.get(k, 0.0) for k in indices])
    return t0 * (1 - float(np.clip(pesos[0] * m_p + pesos[1] * m_i, -1, 1)))

def busqueda_conjunta(planificador, mejoras_idx: dict, mb: dict, presupuesto: float, corte: float, pesos) -> dict:
    candidatos = sorted(mejoras_idx)
    limite = presupuesto * sum(mb[k] for k in candidatos)
    elegidos, usado = [], 0.0
    t_actual = t_inicio = tiempo_combinado(planificador, [], mejoras_idx, pesos)
    while True:
        opciones = []
        for k in candidatos:
            if k in elegidos or usado + mb[k] > limite:
                continue
            ganancia = t_actual - tiempo_combinado(planificador, elegidos + [k], mejoras_idx, pesos)
            opciones.append((ganancia / max(mb[k], 1e-9), ganancia, k))
        opciones = [o for o in opciones if o[1] > max(corte * t_actual, 0)]
        if not opciones:
            break
        _, ganancia, k = max(opciones)
        elegidos.append(k)
        usado += mb[k]
        t_actual -= ganancia
    return dict(indices=elegidos, mb=usado, limite=limite, pred_inicio=t_inicio, pred_final=t_actual)

def recomendar(query: str, config: dict | None = None, reconstruir: bool = False) -> dict:
    if not indices_ml.disponible():
        return {"disponible": False, "motivo": "Faltan los modelos de la V2 y la V3 en ml/."}
    if not configurada():
        return {"disponible": False,
                "motivo": "Falta configurar GEMELA_DSN en el .env (un PostgreSQL propio con HypoPG para la base gemela)."}
    _, _, p = indices_ml.cargar()
    v2 = indices_ml.recomendar_detalle(query, config)
    try:
        nombre, gemela = asegurar(config, reconstruir)
    except (psycopg.Error, ValueError) as exc:
        log.warning("No se pudo armar la base gemela: %s", exc)
        return {"disponible": False, "motivo": f"No se pudo armar la base gemela: {exc}"}
    with _conectar(nombre) as c, c.cursor() as cur:
        try:
            plan_gemela = _explain(cur, query, {})
        except psycopg.Error as exc:
            return {"disponible": False, "motivo": f"La consulta no se puede planificar en la base gemela: {exc}"}
        # Otra configuración del planificador tiene que ganar al menos el corte; si no,
        # con umbral 0 se cambiaría el plan por una mejora que no se nota.
        planificador = Planificador(cur, query, v2["n_tablas"], max(p["umbral"], p["corte"]))
        # Con una sola consulta no se limita el espacio (ver indices_ml.AYUDA): decide el corte.
        r = busqueda_conjunta(planificador, v2["mejora_por_indice"], v2["mb_por_indice"],
                              1.0, p["corte"], (p["peso_plan"], p["peso_indice"]))
        _, ajustes, plan = planificador.mejor(r["indices"])
        cur.execute("SELECT hypopg_reset()")
    # La mejora se mide contra el plan que usa PostgreSQL hoy (sin índices nuevos ni
    # cambios de configuración), así también cuenta lo que gana el cambio de plan.
    actual = planificador.defecto[()]
    mejora = 1 - r["pred_final"] / actual if actual > 0 else 0.0
    indices = [{"tabla": t, "columna": c, "mb": round(v2["mb_por_indice"][(t, c)], 2),
                "sql_sugerido": f"CREATE INDEX idx_{t}_{c} ON {t} ({c});"} for t, c in r["indices"]]
    return {
        "disponible": True,
        "indices": indices,
        "sql_optimizado": sql_optimizado(query, ajustes, [i["sql_sugerido"] for i in indices]),
        "cambia_plan": bool(ajustes),
        "descripcion_plan": _describir(plan, ajustes),
        "tiempo_actual_ms": round(actual, 3),
        "tiempo_final_ms": round(r["pred_final"], 3),
        "mejora_pct": round(100 * mejora, 1),
        "mb": round(r["mb"], 2),
        "candidatos_evaluados": len(v2["mejora_por_indice"]),
        "gemela_mismo_plan": forma_del_plan(plan_gemela) == forma_del_plan(v2["plan"]),
        "gemela": gemela,
    }
