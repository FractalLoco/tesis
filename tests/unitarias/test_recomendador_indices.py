# Pruebas del recomendador de índices por reglas con planes escritos a mano,
# sin PostgreSQL: se reemplazan el EXPLAIN y la lista de índices existentes.
from analizador.analisis import recomendador

def recomendar(monkeypatch, plan, indices=()):
    monkeypatch.setattr(recomendador, "get_plan", lambda q, analyze, config: [{"Plan": plan}])
    monkeypatch.setattr(recomendador, "listar_todos_indices", lambda config: list(indices))
    return [r["sql_sugerido"] for r in recomendador.recomendar_indices("SELECT ...")["recomendaciones"]]

def ordenar(clave, *hijos):
    return {"Node Type": "Sort", "Sort Key": [clave], "Plans": list(hijos)}

def leer(tabla, alias=None, filas=60_000):
    return {"Node Type": "Seq Scan", "Relation Name": tabla, "Alias": alias or tabla, "Plan Rows": filas}

def test_order_by_sin_tabla_adelante_sugiere_indice(monkeypatch):
    # Con una sola tabla PostgreSQL escribe "o_totalprice DESC", sin "orders.".
    plan = {"Node Type": "Limit", "Plans": [ordenar("o_totalprice DESC", leer("orders"))]}
    assert recomendar(monkeypatch, plan) == ["CREATE INDEX idx_orders_o_totalprice ON orders (o_totalprice);"]

def test_order_by_no_sugiere_si_ya_hay_indice_o_es_una_expresion(monkeypatch):
    con_indice = ordenar("o_orderdate", leer("orders"))
    assert recomendar(monkeypatch, con_indice, [{"tabla": "orders", "columnas": ["o_orderdate"]}]) == []
    expresion = ordenar("(o_totalprice * 2)", leer("orders"))
    assert recomendar(monkeypatch, expresion) == []
