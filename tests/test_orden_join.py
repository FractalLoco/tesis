import pytest

from analizador.analisis import modelo, orden_join

def nodo(tipo, hijos=(), **campos):
    return {"Node Type": tipo, "Total Cost": 10.0, "Startup Cost": 1.0, "Plan Rows": 100,
            "Plan Width": 8, **campos, "Plans": list(hijos)}

def scan(tabla, **campos):
    return nodo("Seq Scan", **{"Relation Name": tabla, "Alias": tabla, **campos})

def join(a, b, tipo="Hash Join", join_type="Inner", **campos):
    return nodo(tipo, [a, b], **{"Join Type": join_type, **campos})

def cadena(tablas, tipo="Hash Join", join_type="Inner", **campos):
    plan = scan(tablas[0])
    for t in tablas[1:]:
        plan = join(plan, scan(t), tipo, join_type, **campos)
    return plan

CUATRO = ["lineitem", "orders", "customer", "nation"]

@pytest.mark.parametrize("plan, aplica, texto", [
    (cadena(CUATRO), True, None),
    (cadena(["a", "b"]), False, "no hay orden de JOIN que reordenar"),
    (scan("a"), False, "no hay orden de JOIN que reordenar"),
    (join(cadena(["a", "b"]), scan("c"), join_type="Left"), False, "JOIN externo"),
    # PostgreSQL muestra un LEFT JOIN invertido como Right.
    (join(cadena(["a", "b"]), scan("c"), join_type="Right"), False, "JOIN externo"),
    (join(cadena(["a", "b"]), scan("c"), join_type="Semi"), False, "IN / EXISTS"),
    (join(cadena(["a", "b"]), nodo("CTE Scan", **{"Alias": "x"})), False, "CTE"),
    # Así planifica PostgreSQL 18 un CTE materializado: el InitPlan aparece antes del CTE Scan.
    (nodo("Aggregate", [scan("customer", **{"Parent Relationship": "InitPlan", "Subplan Name": "CTE c"}),
                        join(nodo("CTE Scan", **{"Alias": "c"}), scan("orders"))]), False, "CTE"),
    (join(cadena(["a", "b"]), nodo("Subquery Scan", [scan("c")])), False, "subconsulta"),
    (nodo("Result", [scan("a", **{"Parent Relationship": "InitPlan"})]), False, "subconsulta"),
])
def test_cuando_aplica_el_modelo(plan, aplica, texto):
    r = orden_join.evaluar_aplicacion({"Plan": plan})
    assert r["aplica"] is aplica
    if texto:
        assert texto in r["motivo"]

def test_seis_tablas_aplica_con_aviso():
    r = orden_join.evaluar_aplicacion(cadena(list("abcdef")))
    assert r["aplica"] and r["n_tablas"] == 6
    assert "fuera del rango entrenado" in r["aviso"].lower()

def test_bitmap_index_scan_no_cuenta_como_tabla():
    plan = join(join(nodo("Bitmap Heap Scan", [nodo("Bitmap Index Scan", **{"Index Name": "ix"})],
                          **{"Relation Name": "a"}), scan("b")), scan("c"))
    assert orden_join.evaluar_aplicacion(plan)["n_tablas"] == 3

def test_elige_la_variante_mas_rapida(monkeypatch):
    planes = {
        "defecto": cadena(CUATRO, "Hash Join", costo="defecto"),
        "sin_hash": cadena(CUATRO, "Nested Loop", costo="sin_hash"),
        "orden_escrito": cadena(list(reversed(CUATRO)), "Hash Join", costo="orden_escrito"),
    }
    tiempos = {"defecto": 100.0, "sin_hash": 80.0, "orden_escrito": 40.0}

    def explicar(ajustes):
        if not ajustes:
            return planes["defecto"]
        if ajustes["join_collapse_limit"] == 1 and all(ajustes[m] for m in orden_join.METODOS):
            return planes["orden_escrito"]
        if not ajustes["enable_hashjoin"]:
            return planes["sin_hash"]
        return planes["defecto"]

    monkeypatch.setattr(modelo, "predecir_ms", lambda plan, n: tiempos[plan["costo"]])
    r = orden_join.evaluar_variantes(explicar)
    assert r["disponible"] and r["aplica"]
    assert (r["tiempo_actual_ms"], r["tiempo_mejor_ms"], r["mejora_pct"]) == (100.0, 40.0, 60.0)
    assert r["variantes_evaluadas"] == 3   # planes repetidos se evalúan una sola vez
    assert r["mejor_es_actual"] is False
    assert "nation → customer → orders → lineitem" in r["descripcion"]
    assert "join_collapse_limit = 1" in r["descripcion"]

def test_descarta_planes_con_metodo_desactivado(monkeypatch):
    defecto = cadena(CUATRO, costo="defecto")
    inflado = cadena(CUATRO, "Merge Join", costo="inflado", **{"Total Cost": 1e10})
    monkeypatch.setattr(modelo, "predecir_ms", lambda plan, n: {"defecto": 50.0, "inflado": 1.0}[plan["costo"]])
    r = orden_join.evaluar_variantes(lambda ajustes: inflado if ajustes else defecto)
    assert r["tiempo_mejor_ms"] == 50.0 and r["mejor_es_actual"] is True
    assert "PostgreSQL por defecto" in r["descripcion"]

def test_no_aplica_no_llama_al_modelo(monkeypatch):
    monkeypatch.setattr(modelo, "predecir_ms", lambda *a: pytest.fail("no debía predecir"))
    r = orden_join.evaluar_variantes(lambda ajustes: cadena(["a", "b"]))
    assert r["disponible"] and not r["aplica"] and r["tiempo_actual_ms"] is None

def test_sin_modelo_no_toca_la_base(monkeypatch):
    monkeypatch.setattr(modelo, "disponible", lambda: False)
    monkeypatch.setattr(orden_join, "get_readonly_connection", lambda *a: pytest.fail("no debía conectar"))
    assert orden_join.recomendar_orden_join("SELECT 1") == orden_join._resultado(disponible=False)
