"""V2: recomendación de índices con el modelo de Machine Learning.

Usa los modelos que exporta el bloque 15 de ml/modelo_ml_v1_v2_v3.ipynb:
- modelo_v3.pkl: tiempo de un plan (log1p de ms) a partir de sus 24 características.
- modelo_indices.pkl: cuánto mejora una consulta si se crea un índice en una columna.
- parametros_v2_v3.json: umbral, presupuesto, corte y pesos aprendidos en validación.

Todo sale del plan estimado (EXPLAIN, sin ejecutar la consulta) y de las
estadísticas que PostgreSQL ya tiene (pg_class, pg_stats), en una conexión de solo
lectura. Nunca crea un índice: entrega el CREATE INDEX para que el usuario decida.
"""
import json
import logging
import math
import warnings
from functools import lru_cache
from pathlib import Path

from analizador.analisis import modelo
from analizador.analisis.plan_parser import raiz, recorrer
from analizador.analisis.recomendador import (
    _columnas_de_expr,
    _columnas_de_filtro,
    _cubierta,
    _recolectar_alias,
)
from analizador.conexion import get_readonly_connection
from analizador.pagina.indices import listar_todos_indices

log = logging.getLogger("analizador.indices_ml")

DIR_ML = Path(__file__).resolve().parents[2] / "ml"
ARCHIVOS = {"plan": DIR_ML / "modelo_v3.pkl", "indice": DIR_ML / "modelo_indices.pkl"}
ARCHIVO_PARAMETROS = DIR_ML / "parametros_v2_v3.json"

# El modelo de índices se evaluó en el notebook diciendo si un índice mejora la
# consulta más de 10% (acierta 81% en consultas que no vio). Aquí se usa igual.
AYUDA = 0.10
# Tablas chicas: se leen enteras en un instante, un índice no cambia nada.
MIN_FILAS = 1000

class ModelosNoDisponibles(RuntimeError):
    pass

@lru_cache(maxsize=1)
def cargar():
    """Devuelve (modelo de planes, modelo de índices, parámetros) o None si faltan."""
    try:
        import joblib
        p = json.loads(ARCHIVO_PARAMETROS.read_text(encoding="utf-8"))
        m_plan, m_indice = joblib.load(ARCHIVOS["plan"]), joblib.load(ARCHIVOS["indice"])
        _predecir(m_plan, [[0.0] * len(p["caracteristicas"])])
        _predecir(m_indice, [[0.0] * len(p["caracteristicas_indice"])])
    except Exception as exc:
        log.warning("Modelos de la V2 y la V3 no disponibles: %s", exc)
        return None
    return m_plan, m_indice, p

def disponible() -> bool:
    return cargar() is not None

def _predecir(m, filas) -> list[float]:
    # Los modelos se entrenaron con un DataFrame; aquí se les pasan listas en el
    # mismo orden de columnas, y scikit-learn avisa por eso. El aviso no aplica.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return [float(v) for v in m.predict(filas)]

def _cargados():
    c = cargar()
    if c is None:
        raise ModelosNoDisponibles("Faltan los modelos de la V2 y la V3 en ml/.")
    return c

def contar_tablas(plan) -> int:
    return sum(1 for n, _ in recorrer(raiz(plan)) if n.get("Relation Name"))

def predecir_ms(plan, n_tablas: int) -> float:
    """Tiempo estimado de un plan con el modelo de la V3 (el mismo que usa la V2)."""
    m_plan, _, p = _cargados()
    f = modelo.extraer_features(plan, n_tablas)
    return max(0.0, math.expm1(_predecir(m_plan, [[float(f[k]) for k in p["caracteristicas"]]])[0]))

# --- Lo mismo que el bloque 10.1 del notebook ---

def lecturas_por_tabla(plan) -> dict:
    salida = {}
    for n, _ in recorrer(raiz(plan)):
        if n.get("Relation Name") and n["Relation Name"] not in salida:
            salida[n["Relation Name"]] = n
    return salida

def caracteristicas_indice(plan, tablas_q, tabla, columna, uso, T, C) -> dict:
    nodo = lecturas_por_tabla(plan).get(tabla, {})
    filas = T[tabla]["filas"]
    return dict(
        log_filas_tabla=math.log10(filas),
        es_filtro=int(uso == "filtro"), es_join=int(uso == "join"),
        selectividad=min(1.0, (nodo.get("Plan Rows") or filas) / filas),
        lee_entera=int(nodo.get("Node Type") == "Seq Scan"),
        parte_del_costo=(nodo.get("Total Cost") or 0) / max(raiz(plan)["Total Cost"], 1e-3),
        distintos=C.get((tabla, columna), {}).get("distintos", 0),
        correlacion=C.get((tabla, columna), {}).get("correlacion", 0),
        n_tablas=len(tablas_q),
        es_tabla_mas_grande=int(filas >= max(T[x]["filas"] for x in tablas_q)),
    )

def mb_estimado(T, C, tabla, columna) -> float:
    ancho = C.get((tabla, columna), {}).get("ancho") or 8
    return T[tabla]["filas"] * (ancho + 16) * 1.15 / 2**20

# --- Lectura del plan y de la base ---

def columnas_candidatas(plan, claves_primarias: dict, indices_por_tabla: dict) -> dict:
    """(tabla, columna) -> "filtro" o "join", para columnas de tablas de la consulta
    que no son clave primaria ni tienen ya un índice que empiece por ellas."""
    root = raiz(plan)
    alias_tabla: dict[str, str] = {}
    _recolectar_alias(root, alias_tabla)
    usos = {}
    for n, _ in recorrer(root):
        tabla = n.get("Relation Name")
        for clave in ("Filter", "Recheck Cond"):
            for al, col in _columnas_de_filtro(n.get(clave), tabla):
                usos[(alias_tabla.get(al, tabla), col)] = "filtro"
        for clave in ("Hash Cond", "Merge Cond", "Join Filter", "Index Cond"):
            for al, col in _columnas_de_expr(n.get(clave)):
                if al in alias_tabla:
                    usos.setdefault((alias_tabla[al], col), "join")
    tablas = set(alias_tabla.values())
    return {(t, c): uso for (t, c), uso in sorted(usos.items())
            if t in tablas and c not in claves_primarias.get(t, set()) and not _cubierta(indices_por_tabla, t, c)}

def leer_estadisticas(conn, tablas) -> tuple[dict, dict, dict]:
    """Como estadisticas() del notebook: filas de cada tabla y, por columna, fracción
    de valores distintos, correlación con el orden en disco y ancho promedio."""
    tablas = sorted(tablas)
    with conn.cursor() as cur:
        cur.execute("SELECT c.relname, c.reltuples FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND c.relname = ANY(%s)", (tablas,))
        T = {t: {"filas": max(float(f), 1.0)} for t, f in cur.fetchall()}
        cur.execute("SELECT tablename, attname, n_distinct, correlation, avg_width FROM pg_stats "
                    "WHERE schemaname = 'public' AND tablename = ANY(%s)", (tablas,))
        C = {}
        for t, c, nd, corr, ancho in cur.fetchall():
            filas = T.get(t, {"filas": 1.0})["filas"]
            distintos = -nd * filas if nd < 0 else nd
            C[(t, c)] = {"distintos": min(1.0, distintos / filas), "correlacion": abs(corr or 0), "ancho": ancho}
        cur.execute("SELECT tc.table_name, kcu.column_name FROM information_schema.table_constraints tc "
                    "JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name "
                    "AND kcu.table_schema = tc.table_schema "
                    "WHERE tc.table_schema = 'public' AND tc.constraint_type = 'PRIMARY KEY'")
        claves = {}
        for t, c in cur.fetchall():
            claves.setdefault(t, set()).add(c)
    conn.rollback()
    return T, C, claves

def _explain(conn, query: str) -> dict:
    try:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute("SET LOCAL statement_timeout = '5s'")
            cur.execute("EXPLAIN (FORMAT JSON) " + query)
            return raiz(cur.fetchone()[0])
    finally:
        conn.rollback()

def evaluar(plan, T, C, claves, indices_por_tabla) -> dict:
    """La V2 sobre un plan ya leído. Separada de la conexión para probarla sin base."""
    m_plan, m_indice, p = _cargados()
    n_tablas = contar_tablas(plan)
    tablas_q = [t for t in lecturas_por_tabla(plan) if t in T]
    candidatas = {k: uso for k, uso in columnas_candidatas(plan, claves, indices_por_tabla).items()
                  if k[0] in T and T[k[0]]["filas"] >= MIN_FILAS}
    t_actual = predecir_ms(plan, n_tablas)
    mejora, mb = {}, {}
    for (t, c), uso in candidatas.items():
        x = caracteristicas_indice(plan, tablas_q, t, c, uso, T, C)
        mejora[(t, c)] = _predecir(m_indice, [[float(x[k]) for k in p["caracteristicas_indice"]]])[0]
        mb[(t, c)] = mb_estimado(T, C, t, c)
    # En el notebook el presupuesto de espacio se aprendió para muchas consultas a la
    # vez; con una sola, el índice más útil suele ser el más grande y nunca cabría.
    elegidos = [k for k in mejora if mejora[k] > AYUDA]
    mejor = max([0.0] + [mejora[k] for k in elegidos])
    filas = [{"tabla": t, "columna": c, "uso": candidatas[(t, c)],
              "mejora_pct": round(100 * mejora[(t, c)], 1), "mb": round(mb[(t, c)], 2),
              "recomendado": (t, c) in elegidos,
              "sql_sugerido": f"CREATE INDEX idx_{t}_{c} ON {t} ({c});"}
             for t, c in sorted(candidatas, key=lambda k: mejora[k], reverse=True)]
    return {"disponible": True, "n_tablas": n_tablas, "tiempo_actual_ms": round(t_actual, 3),
            "indices_sql": [f["sql_sugerido"] for f in filas if f["recomendado"]],
            "tiempo_con_indices_ms": round(t_actual * (1 - mejor), 3), "mejora_pct": round(100 * mejor, 1),
            "mb_recomendados": round(sum(mb[k] for k in elegidos), 2),
            "candidatos": filas, "mejora_por_indice": mejora, "mb_por_indice": mb}

def recomendar_detalle(query: str, config: dict | None = None) -> dict:
    """La V2 completa, con lo que necesita la V3 (plan y mejora por índice)."""
    with get_readonly_connection(config) as conn:
        conn.commit()
        plan = _explain(conn, query)
        T, C, claves = leer_estadisticas(conn, lecturas_por_tabla(plan))
    por_tabla = {}
    for ix in listar_todos_indices(config):
        por_tabla.setdefault(ix["tabla"], []).append(ix)
    return {**evaluar(plan, T, C, claves, por_tabla), "plan": plan}

def recomendar(query: str, config: dict | None = None) -> dict:
    if not disponible():
        return {"disponible": False, "motivo": "Faltan los modelos de la V2 y la V3 en ml/."}
    r = recomendar_detalle(query, config)
    for interno in ("mejora_por_indice", "mb_por_indice", "plan"):
        r.pop(interno)
    return r
