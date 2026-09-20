"""Recomendador heurístico de índices (todavía sin Machine Learning).

Analiza el plan ESTIMADO de una consulta (EXPLAIN, sin ANALYZE: no la ejecuta)
y sugiere columnas que podrían beneficiarse de un índice nuevo: filtros
costosos sin índice, condiciones de JOIN y columnas de ORDER BY. Nunca ejecuta
ningún DDL; solo devuelve el SQL sugerido para que el usuario lo revise.
"""
import re

from analizador.explain import get_plan
from analizador.indices import listar_todos_indices

UMBRAL_FILAS = 500  # por debajo de esto no vale la pena sugerir un índice

# Comparaciones calificadas ("alias.columna = ...") y sin calificar ("columna = ...").
# Esto último es lo normal cuando el Filter pertenece a una sola tabla: PostgreSQL no
# antepone el nombre de la tabla si no hace falta para desambiguar.
_CALIFICADO = re.compile(
    r"\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|<>|<=|>=|<|>|~~|~~\*|IS)"
)
_SIMPLE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|<>|<=|>=|<|>|~~|~~\*|IS)")

def _columnas_de_expr(expr: str | None) -> set[tuple[str, str]]:
    if not expr:
        return set()
    return set(_CALIFICADO.findall(expr))

def _columnas_de_filtro(expr: str | None, tabla_actual: str | None) -> set[tuple[str, str]]:
    """Como _columnas_de_expr, pero además reconoce columnas sin calificar
    ('columna = ...') y las asigna a la tabla del nodo de escaneo actual."""
    pares = _columnas_de_expr(expr)
    if not expr or not tabla_actual:
        return pares
    calificadas = {c for _, c in pares}
    for m in _SIMPLE.finditer(expr):
        col = m.group(1)
        inicio = m.start(1)
        if inicio > 0 and expr[inicio - 1] == ".":
            continue  # es la parte "columna" de un "tabla.columna" ya capturado
        if col not in calificadas:
            pares.add((tabla_actual, col))
    return pares

def _cubierta(indices_por_tabla: dict, tabla: str, columna: str) -> bool:
    for ix in indices_por_tabla.get(tabla, []):
        cols = ix.get("columnas") or []
        if cols and cols[0] == columna:
            return True
    return False

def _recolectar_alias(nodo: dict, alias_tabla: dict) -> None:
    """Primera pasada: registra alias->tabla de TODO el plan antes de mirar
    filtros/orden, porque un ORDER BY suele estar en un nodo Sort que envuelve
    a los Seq Scan (aparece antes que ellos al recorrer el árbol)."""
    tabla = nodo.get("Relation Name")
    alias = nodo.get("Alias") or tabla
    if tabla and alias:
        alias_tabla[alias] = tabla
    for hijo in nodo.get("Plans", []):
        _recolectar_alias(hijo, alias_tabla)

def _recorrer(nodo: dict, alias_tabla: dict, sugerencias: dict) -> None:
    tabla = nodo.get("Relation Name")
    filas = nodo.get("Plan Rows", 0) or 0

    if nodo.get("Node Type") == "Seq Scan" and nodo.get("Filter") and tabla and filas >= UMBRAL_FILAS:
        for al, col in _columnas_de_filtro(nodo["Filter"], tabla):
            t = alias_tabla.get(al, tabla)
            sugerencias.setdefault((t, col), []).append(
                f"Filtro sobre {t}.{col} revisa ~{int(filas):,} filas sin índice (Seq Scan).".replace(",", ".")
            )

    for clave in ("Hash Cond", "Merge Cond", "Index Cond"):
        cond = nodo.get(clave)
        if cond:
            for al, col in _columnas_de_expr(cond):
                t = alias_tabla.get(al)
                if t:
                    sugerencias.setdefault((t, col), []).append(
                        f"Se usa {t}.{col} en una condición de unión ({clave})."
                    )

    for clave_orden in nodo.get("Sort Key") or []:
        ref = clave_orden.split()[0] if clave_orden else ""  # descarta " DESC"/" NULLS LAST"/etc.
        if "." in ref:
            al, col = ref.split(".", 1)
            t = alias_tabla.get(al, al)
            sugerencias.setdefault((t, col), []).append(
                f"Se ordena por {t}.{col} (ORDER BY); un índice evita el paso de Sort."
            )

    for hijo in nodo.get("Plans", []):
        _recorrer(hijo, alias_tabla, sugerencias)

def recomendar_indices(query: str, config: dict | None = None) -> dict:
    plan = get_plan(query, analyze=False, config=config)
    root = plan[0]["Plan"] if isinstance(plan, list) else plan["Plan"]

    alias_tabla: dict[str, str] = {}
    _recolectar_alias(root, alias_tabla)
    sugerencias: dict[tuple[str, str], list[str]] = {}
    _recorrer(root, alias_tabla, sugerencias)

    existentes = listar_todos_indices(config)
    por_tabla: dict[str, list[dict]] = {}
    for ix in existentes:
        por_tabla.setdefault(ix["tabla"], []).append(ix)

    recomendaciones = []
    for (tabla, columna), motivos in sugerencias.items():
        if _cubierta(por_tabla, tabla, columna):
            continue
        recomendaciones.append({
            "tabla": tabla,
            "columna": columna,
            "motivos": sorted(set(motivos)),
            "sql_sugerido": f"CREATE INDEX idx_{tabla}_{columna} ON {tabla} ({columna});",
        })
    recomendaciones.sort(key=lambda r: (r["tabla"], r["columna"]))

    return {
        "consulta": query,
        "n_recomendaciones": len(recomendaciones),
        "recomendaciones": recomendaciones,
        "nota": "Sugerencias heurísticas a partir del plan estimado (EXPLAIN). "
                "La recomendación por Machine Learning llegará más adelante.",
    }
