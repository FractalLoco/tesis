from collections.abc import Iterator

def raiz(plan_json) -> dict:
    """Nodo raíz de la salida de EXPLAIN (FORMAT JSON). Acepta la salida completa
    ([{"Plan": ...}]), un solo elemento ({"Plan": ...}) o el nodo ya extraído."""
    if isinstance(plan_json, list):
        plan_json = plan_json[0]
    return plan_json.get("Plan", plan_json)

def recorrer(nodo: dict, profundidad: int = 0) -> Iterator[tuple[dict, int]]:
    """Recorre el árbol del plan en preorden: entrega (nodo, profundidad)."""
    yield nodo, profundidad
    for hijo in nodo.get("Plans", []):
        yield from recorrer(hijo, profundidad + 1)

def parse_plan(plan_json) -> dict:
    root = raiz(plan_json)
    operadores = [n.get("Node Type") for n, _ in recorrer(root)]
    return {
        "operadores": operadores,
        "n_operadores": len(operadores),
        "costo_total_estimado": root.get("Total Cost"),
        "filas_estimadas": root.get("Plan Rows"),
        "tiempo_real_ms": root.get("Actual Total Time"),
        "arbol": _nodo(root),
    }

def _nodo(n: dict) -> dict:
    return {
        "tipo": n.get("Node Type"),
        "relacion": n.get("Relation Name"),
        "alias": n.get("Alias"),
        "indice": n.get("Index Name"),
        "costo_inicial": n.get("Startup Cost"),
        "costo_total": n.get("Total Cost"),
        "filas_estimadas": n.get("Plan Rows"),
        "ancho_fila": n.get("Plan Width"),
        "tiempo_inicial_ms": n.get("Actual Startup Time"),
        "tiempo_total_ms": n.get("Actual Total Time"),
        "filas_reales": n.get("Actual Rows"),
        "loops": n.get("Actual Loops"),
        "filtro": n.get("Filter"),
        "cond_join": n.get("Hash Cond") or n.get("Join Filter") or n.get("Merge Cond") or n.get("Index Cond"),
        "filas_eliminadas_filtro": n.get("Rows Removed by Filter"),
        "orden": n.get("Sort Key"),
        "hijos": [_nodo(h) for h in n.get("Plans", [])],
    }
