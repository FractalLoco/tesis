def parse_plan(plan_json) -> dict:
    root = plan_json[0]["Plan"] if isinstance(plan_json, list) else plan_json["Plan"]
    operadores: list[str] = []
    _recorrer(root, operadores)
    return {
        "operadores": operadores,
        "n_operadores": len(operadores),
        "costo_total_estimado": root.get("Total Cost"),
        "filas_estimadas": root.get("Plan Rows"),
        "tiempo_real_ms": root.get("Actual Total Time"),
        "arbol": _nodo(root),
    }

def _recorrer(nodo: dict, acc: list[str]) -> None:
    acc.append(nodo.get("Node Type"))
    for hijo in nodo.get("Plans", []):
        _recorrer(hijo, acc)

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
