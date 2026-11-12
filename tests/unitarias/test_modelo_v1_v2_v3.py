# Pruebas del notebook de la versión nueva (ml/modelo_ml_v1_v2_v3.ipynb).
# Se toman las funciones tal como están en el notebook y se prueban con datos
# escritos a mano, sin PostgreSQL ni modelos entrenados:
#   V1: el modelo elige el plan de cada consulta.
#   V2: el modelo recomienda índices.
#   V3: el modelo decide índices y plan juntos (en la base gemela).
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analizador.analisis import modelo

ML = Path(__file__).resolve().parents[2] / "ml"
NOTEBOOK = ML / "modelo_ml_v1_v2_v3.ipynb"

def funciones_del_notebook(*nombres, **globales):
    """Busca las funciones pedidas en el notebook y las devuelve listas para usar.
    `globales` reemplaza lo que esas funciones usan de otros bloques."""
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    espacio = {"np": np, "pd": pd, **globales}
    for celda in nb["cells"]:
        fuente = "\n".join(linea for linea in "".join(celda["source"]).splitlines()
                           if not linea.lstrip().startswith("!"))
        for parte in ast.parse(fuente).body:
            if isinstance(parte, (ast.FunctionDef, ast.ClassDef)) and parte.name in nombres:
                exec(compile(ast.Module([parte], []), str(NOTEBOOK), "exec"), espacio)
    faltan = [n for n in nombres if n not in espacio]
    assert not faltan, f"no están en el notebook: {faltan}"
    return [espacio[n] for n in nombres]

def nodo(tipo, hijos=(), **campos):
    return {"Node Type": tipo, "Total Cost": 10.0, "Startup Cost": 1.0, "Plan Rows": 100,
            "Plan Width": 8, **campos, "Plans": list(hijos)}

# --- V1: el modelo elige el plan ---

def test_v1_caracteristicas_iguales_a_las_de_la_app():
    # Si el notebook y la app calculan distinto las 24 características, el modelo
    # nuevo no se podría usar en la página.
    NODOS = ["Seq Scan", "Index Scan", "Index Only Scan", "Bitmap Heap Scan", "Bitmap Index Scan",
             "Nested Loop", "Hash Join", "Merge Join", "Hash", "Sort", "Aggregate", "Materialize", "Gather"]
    (extraer,) = funciones_del_notebook("extraer_caracteristicas", NODOS=NODOS)
    plan = nodo("Aggregate", [nodo("Nested Loop", [
        nodo("Seq Scan", **{"Relation Name": "pedidos"}),
        nodo("Index Scan", **{"Relation Name": "clientes", "Index Name": "clientes_pkey"})])],
        **{"Total Cost": 300.0, "Plan Rows": 1})
    del_notebook = extraer(plan, 2)
    assert list(del_notebook) == json.loads((ML / "features.json").read_text(encoding="utf-8"))
    assert del_notebook == modelo.extraer_features([{"Plan": plan}], 2)

def test_v1_solo_cambia_el_plan_si_la_mejora_supera_el_umbral():
    NATIVO = "(PostgreSQL decide)"
    (puntaje_prudente,) = funciones_del_notebook("puntaje_prudente", NATIVO=NATIVO)
    planes = pd.DataFrame({"orden": [NATIVO, "a > b > c"]})
    def elegido(pred_ms, umbral):
        return int(np.argmin(puntaje_prudente(planes, np.log1p(pred_ms), umbral)))
    assert elegido([100.0, 95.0], umbral=0.10) == 0     # 5% de mejora: se queda con PostgreSQL
    assert elegido([100.0, 80.0], umbral=0.10) == 1     # 20% de mejora: cambia el plan
    assert elegido([100.0, 95.0], umbral=0.0) == 1      # sin umbral elige el más rápido

# --- V2: el modelo recomienda índices ---

def test_v2_caracteristicas_de_un_indice_candidato():
    caracteristicas_indice, _ = funciones_del_notebook("caracteristicas_indice", "lecturas_por_tabla")
    plan = nodo("Hash Join", [
        nodo("Seq Scan", **{"Relation Name": "pedidos", "Plan Rows": 50, "Total Cost": 800.0}),
        nodo("Seq Scan", **{"Relation Name": "clientes", "Plan Rows": 200, "Total Cost": 100.0})],
        **{"Total Cost": 1000.0})
    T = {"pedidos": {"filas": 10_000}, "clientes": {"filas": 200}}
    C = {("pedidos", "estado"): {"distintos": 0.001, "correlacion": 0.2}}
    x = caracteristicas_indice(plan, ["pedidos", "clientes"], "pedidos", "estado", "filtro", T, C)
    assert (x["es_filtro"], x["es_join"], x["lee_entera"], x["es_tabla_mas_grande"]) == (1, 0, 1, 1)
    assert x["selectividad"] == pytest.approx(50 / 10_000)
    assert x["parte_del_costo"] == pytest.approx(0.8)
    assert x["log_filas_tabla"] == pytest.approx(4.0)

def test_v2_respeta_el_presupuesto_y_descarta_indices_que_no_ayudan():
    tamanos = {("a", "x"): 10.0, ("b", "y"): 10.0, ("c", "z"): 30.0, ("d", "w"): 5.0}
    (elegir_indices,) = funciones_del_notebook("elegir_indices", mb_estimado=lambda base, t, c: tamanos[(t, c)])
    ganancia = {("a", "x"): 500.0, ("b", "y"): 100.0, ("c", "z"): 900.0, ("d", "w"): 0.0}
    elegidos, limite = elegir_indices("base", ganancia, presupuesto=0.4)   # 40% de 55 MB = 22 MB
    assert limite == pytest.approx(22.0)
    assert elegidos == [("a", "x"), ("b", "y")]       # c no cabe; d no ayuda
    assert sum(tamanos[k] for k in elegidos) <= limite

# --- V3: índices y plan juntos ---

def test_v3_combina_las_opiniones_de_los_dos_modelos_con_los_pesos():
    # Sin índices el mejor plan tarda 100 ms; con el índice, 80 ms (20% según el
    # modelo de planes). El modelo de índices dice 50%. Con pesos 0,5 y 0,5:
    # 100 * (1 - (0,5*0,2 + 0,5*0,5)) = 65 ms.
    def falso_mejor_plan(cur, q, indices, m_plan):
        return (80.0 if indices else 100.0, None)
    (tiempo_combinado,) = funciones_del_notebook("tiempo_combinado", mejor_plan=falso_mejor_plan)
    mejoras = {(1, ("pedidos", "estado")): 0.5}
    assert tiempo_combinado(None, 1, [("pedidos", "estado")], None, mejoras, (0.5, 0.5)) == pytest.approx(65.0)
    assert tiempo_combinado(None, 1, [], None, mejoras, (0.5, 0.5)) == pytest.approx(100.0)

def test_v3_elige_indices_dentro_del_espacio_y_sobre_el_corte():
    # a ahorra mucho, b casi nada (bajo el corte) y c ahorra pero no cabe.
    tamanos = {("t", "a"): 5.0, ("t", "b"): 5.0, ("t", "c"): 50.0}
    ahorro = {("t", "a"): 40.0, ("t", "b"): 0.5, ("t", "c"): 30.0}
    def falso_tiempo(cur, q, indices, m_plan, mejoras_idx, pesos):
        return 100.0 - sum(ahorro[k] for k in indices)
    (busqueda_conjunta,) = funciones_del_notebook(
        "busqueda_conjunta",
        mejoras_predichas=lambda base, consultas, m_idx: {(1, k): 0.1 for k in tamanos},
        mb_estimado=lambda base, t, c: tamanos[(t, c)],
        tiempo_combinado=falso_tiempo, PRESUPUESTO=0.4, PESO_PLAN=0.5, PESO_INDICE=0.5)
    r = busqueda_conjunta("base", None, [1], None, None, corte=0.05, limite=20.0)
    assert r["indices"] == [("t", "a")]
    assert r["mb"] <= 20.0
    assert (r["pred_inicio"], r["pred_final"]) == (pytest.approx(100.0), pytest.approx(60.0))
