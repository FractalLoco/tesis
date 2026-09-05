from analizador.plan_parser import parse_plan

def test_parse_plan():
    plan = [{"Plan": {"Node Type": "Hash Join", "Total Cost": 42.0,
                       "Plan Rows": 100, "Actual Total Time": 1.5,
                       "Plans": [{"Node Type": "Seq Scan", "Plans": []}]}}]
    r = parse_plan(plan)
    assert r["n_operadores"] == 2
    assert r["operadores"][0] == "Hash Join"
