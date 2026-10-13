"""Recomendación del orden de JOIN con el modelo de ML.

Sobre la consulta del usuario se piden varios planes estimados (EXPLAIN, sin
ANALYZE: la consulta no se ejecuta) cambiando la configuración del planificador
con SET LOCAL dentro de una transacción de solo lectura. El modelo estima el
tiempo de cada plan y se elige el más rápido. El plan "actual" es el que
PostgreSQL elige con su configuración por defecto.

Si la consulta aplica o no se decide leyendo ese plan (no el texto SQL): se
cuentan las tablas recorridas y se revisan los tipos de JOIN.
"""
import itertools
from collections import Counter

from analizador.analisis import modelo
from analizador.analisis.plan_parser import raiz, recorrer
from analizador.conexion import get_readonly_connection

# Rango de tablas con el que se entrenó el modelo.
MIN_TABLAS, MAX_TABLAS = 3, 5

METODOS = {"enable_hashjoin": "Hash Join", "enable_mergejoin": "Merge Join", "enable_nestloop": "Nested Loop"}

# Con un método de JOIN desactivado que igual hay que usar, PostgreSQL 17 y
# anteriores le suman un costo enorme (disable_cost = 1e10) al plan. Ese plan no
# se parece a nada de lo que vio el modelo, así que se descarta.
COSTO_DESACTIVADO = 1e9

NODOS_NO_APLICA = {"CTE Scan": "usa un CTE (WITH)", "Subquery Scan": "usa una subconsulta"}

# PostgreSQL puede invertir un LEFT JOIN (lo muestra como Right): se informan
# juntos. Semi y Anti salen de IN / EXISTS con subconsulta.
JOIN_NO_APLICA = {"Left": "tiene un JOIN externo (LEFT/RIGHT/FULL)", "Right": "tiene un JOIN externo (LEFT/RIGHT/FULL)",
                  "Full": "tiene un JOIN externo (LEFT/RIGHT/FULL)"}

def _motivo_no_aplica(n: dict) -> str | None:
    tipo_join = n.get("Join Type")
    if tipo_join and tipo_join != "Inner":
        return JOIN_NO_APLICA.get(tipo_join, "usa una subconsulta (IN / EXISTS)")
    if n.get("Node Type") in NODOS_NO_APLICA:
        return NODOS_NO_APLICA[n["Node Type"]]
    if str(n.get("Subplan Name", "")).startswith("CTE "):
        return NODOS_NO_APLICA["CTE Scan"]
    if n.get("Parent Relationship") in ("SubPlan", "InitPlan") or n.get("Subplan Name"):
        return "usa una subconsulta"
    return None

def _variantes():
    """Configuraciones del planificador a probar, además de la por defecto.

    join_collapse_limit = 1 respeta el orden en que están escritos los JOIN; 8 es
    el valor por defecto (el planificador reordena). En cada caso se prueban las
    combinaciones de métodos de JOIN con al menos uno activo. geqo no se varía:
    solo actúa con 12 tablas o más (geqo_threshold)."""
    for limite in (8, 1):
        for activos in itertools.product((True, False), repeat=len(METODOS)):
            if any(activos):
                yield {"join_collapse_limit": limite, **dict(zip(METODOS, activos))}

def evaluar_aplicacion(plan) -> dict:
    """Decide, a partir del plan estimado, si el modelo aplica a la consulta."""
    n_tablas = 0
    motivo = None
    for n, _ in recorrer(raiz(plan)):
        if n.get("Relation Name"):
            n_tablas += 1
        motivo = motivo or _motivo_no_aplica(n)
    if motivo:
        return {"aplica": False, "n_tablas": n_tablas,
                "motivo": f"El modelo de orden de JOIN no aplica a esta consulta ({motivo})."}
    if n_tablas < MIN_TABLAS:
        return {"aplica": False, "n_tablas": n_tablas,
                "motivo": "No aplica: no hay orden de JOIN que reordenar."}
    aviso = None
    if n_tablas > MAX_TABLAS:
        aviso = (f"Fuera del rango entrenado ({MIN_TABLAS}-{MAX_TABLAS} tablas): "
                 "predicción menos confiable.")
    return {"aplica": True, "n_tablas": n_tablas, "aviso": aviso}

def _firma(plan) -> tuple:
    """Identifica la forma del plan, para no evaluar dos veces el mismo."""
    return tuple((n.get("Node Type"), n.get("Relation Name"), n.get("Alias"), prof)
                 for n, prof in recorrer(raiz(plan)))

def _describir(plan, ajustes: dict) -> str:
    """Descripción legible de una variante: orden de las tablas, métodos de JOIN
    usados y qué se cambió en la configuración."""
    tablas, joins = [], Counter()
    for n, _ in recorrer(raiz(plan)):
        rel = n.get("Relation Name")
        if rel:
            alias = n.get("Alias")
            tablas.append(rel if not alias or alias == rel else f"{rel} ({alias})")
        if n.get("Join Type"):
            joins[n["Node Type"]] += 1
    partes = [f"orden: {' → '.join(tablas)}"]
    if joins:
        partes.append(", ".join(f"{tipo} ×{k}" for tipo, k in joins.items()))
    cambios = []
    if ajustes.get("join_collapse_limit") == 1:
        cambios.append("respetando el orden escrito de los JOIN (join_collapse_limit = 1)")
    cambios += [f"sin {METODOS[m]} ({m} = off)" for m in METODOS if ajustes.get(m) is False]
    partes.append("configuración: " + ("; ".join(cambios) if cambios else "la de PostgreSQL por defecto"))
    return " · ".join(partes)

def _resultado(**campos) -> dict:
    base = {"disponible": True, "aplica": False, "motivo": None, "aviso": None, "n_tablas": None,
            "tiempo_actual_ms": None, "tiempo_mejor_ms": None, "mejora_pct": None,
            "descripcion": None, "mejor_es_actual": None, "variantes_evaluadas": 0}
    base.update(campos)
    return base

def evaluar_variantes(explicar) -> dict:
    """explicar(ajustes) devuelve el plan estimado con esos ajustes ({} = por defecto)."""
    actual = explicar({})
    app = evaluar_aplicacion(actual)
    if not app["aplica"]:
        return _resultado(**app)

    n = app["n_tablas"]
    t_actual = modelo.predecir_ms(actual, n)
    mejor = (t_actual, actual, {})
    vistas = {_firma(actual)}
    for ajustes in _variantes():
        try:
            plan = explicar(ajustes)
        except Exception:
            continue
        firma = _firma(plan)
        if firma in vistas or (raiz(plan).get("Total Cost") or 0) >= COSTO_DESACTIVADO:
            continue
        vistas.add(firma)
        t = modelo.predecir_ms(plan, n)
        if t < mejor[0]:
            mejor = (t, plan, ajustes)

    t_mejor, plan_mejor, ajustes_mejor = mejor
    mejora = (t_actual - t_mejor) / t_actual * 100 if t_actual > 0 else 0.0
    return _resultado(
        **app,
        tiempo_actual_ms=round(t_actual, 3),
        tiempo_mejor_ms=round(t_mejor, 3),
        mejora_pct=round(mejora, 1),
        mejor_es_actual=plan_mejor is actual,
        descripcion=_describir(plan_mejor, ajustes_mejor),
        variantes_evaluadas=len(vistas),
    )

def _explain(conn, query: str, ajustes: dict) -> dict:
    """EXPLAIN (sin ANALYZE) en su propia transacción de solo lectura. SET LOCAL
    dura solo hasta el ROLLBACK: no queda configuración pegada en la conexión."""
    try:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute("SET LOCAL statement_timeout = '5s'")
            for nombre, valor in ajustes.items():
                # Nombres y valores salen de _variantes(), nunca del usuario.
                v = valor if isinstance(valor, int) and not isinstance(valor, bool) else ("on" if valor else "off")
                cur.execute(f"SET LOCAL {nombre} = {v}")
            cur.execute("EXPLAIN (FORMAT JSON) " + query)
            return raiz(cur.fetchone()[0])
    finally:
        conn.rollback()

def recomendar_orden_join(query: str, config: dict | None = None) -> dict:
    if not modelo.disponible():
        return _resultado(disponible=False)
    with get_readonly_connection(config) as conn:
        conn.commit()   # deja fijo el "solo lectura" de la conexión antes de las variantes
        return evaluar_variantes(lambda ajustes: _explain(conn, query, ajustes))
