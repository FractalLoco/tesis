import json
from pathlib import Path

import pytest

from analizador.analisis import modelo

ML = Path(__file__).resolve().parent.parent / "ml"

def nodo(tipo, hijos=(), **campos):
    return {"Node Type": tipo, "Total Cost": 10.0, "Startup Cost": 1.0, "Plan Rows": 100,
            "Plan Width": 8, **campos, "Plans": list(hijos)}

def scan(tabla, tipo="Seq Scan"):
    return nodo(tipo, **{"Relation Name": tabla, "Alias": tabla})

def hash_join(a, b):
    return nodo("Hash Join", [a, nodo("Hash", [b])], **{"Join Type": "Inner"})

# Plan de 4 tablas con la forma de los de entrenamiento: count(*) sobre JOIN.
PLAN_4 = [{"Plan": nodo("Aggregate", [hash_join(hash_join(scan("lineitem"), scan("orders")),
                                                hash_join(scan("customer"), scan("nation")))],
                        **{"Total Cost": 500.0, "Startup Cost": 499.0, "Plan Rows": 1})}]

PLAN_BITMAP = [{"Plan": nodo("Nested Loop", [
    nodo("Bitmap Heap Scan", [nodo("Bitmap Index Scan", **{"Index Name": "ix"})], **{"Relation Name": "a"}),
    scan("b", "Index Only Scan")], **{"Join Type": "Inner"})}]

def extraer_features_del_notebook():
    """Toma extraer_features tal como está en el notebook con el que se entrenó."""
    nb = json.loads((ML / "modelo_join_order_colab.ipynb").read_text(encoding="utf-8"))
    fuente = next("".join(c["source"]) for c in nb["cells"]
                  if c["cell_type"] == "code" and "def extraer_features" in "".join(c["source"]))
    espacio = {}
    exec(fuente.split("registros = []")[0], espacio)
    return espacio["extraer_features"]

def test_features_tienen_exactamente_las_columnas_de_features_json():
    esperadas = json.loads((ML / "features.json").read_text(encoding="utf-8"))
    assert list(modelo.extraer_features(PLAN_4, 4)) == esperadas

@pytest.mark.parametrize("plan, n_tablas", [(PLAN_4, 4), (PLAN_BITMAP, 2)])
def test_features_iguales_a_las_del_notebook(plan, n_tablas):
    del_notebook = extraer_features_del_notebook()
    assert modelo.extraer_features(plan, n_tablas) == del_notebook(plan[0]["Plan"], n_tablas)

def test_conteos_del_plan():
    f = modelo.extraer_features(PLAN_4, 4)
    assert (f["n_Seq Scan"], f["n_Hash Join"], f["n_Hash"], f["n_Aggregate"]) == (4, 3, 3, 1)
    assert (f["n_nodos"], f["prof_max"], f["n_scans"]) == (11, 5, 4)
    assert (f["raiz_costo"], f["raiz_costo_ini"], f["raiz_filas_est"]) == (500.0, 499.0, 1)

def test_predice_milisegundos_positivos():
    assert modelo.disponible()
    ms = modelo.predecir_ms(PLAN_4, 4)
    assert isinstance(ms, float) and ms >= 0

def test_sin_archivos_queda_no_disponible(monkeypatch, tmp_path):
    monkeypatch.setattr(modelo, "ARCHIVO_MODELO", tmp_path / "no_existe.pkl")
    modelo._cargar.cache_clear()
    try:
        assert not modelo.disponible()
        with pytest.raises(modelo.ModeloNoDisponible):
            modelo.predecir_ms(PLAN_4, 4)
    finally:
        monkeypatch.undo()
        modelo._cargar.cache_clear()
