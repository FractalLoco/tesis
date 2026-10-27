# Prueba de parse_plan: recorre el plan que entrega EXPLAIN (FORMAT JSON).
# Un plan es un árbol: cada nodo es una operación (Hash Join, Seq Scan, ...)
# y sus hijos van en "Plans".
from analizador.analisis.plan_parser import parse_plan

def test_cuenta_los_operadores_del_plan():
    # Plan escrito a mano: un Hash Join con un Seq Scan como hijo.
    plan = [{"Plan": {"Node Type": "Hash Join", "Total Cost": 42.0,
                       "Plan Rows": 100, "Actual Total Time": 1.5,
                       "Plans": [{"Node Type": "Seq Scan", "Plans": []}]}}]
    r = parse_plan(plan)
    assert r["n_operadores"] == 2
    assert r["operadores"][0] == "Hash Join"   # el primero es la raíz del árbol
