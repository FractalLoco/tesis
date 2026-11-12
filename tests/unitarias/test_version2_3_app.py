# Pruebas de la V2 y la V3 dentro de la app (analizador/analisis/indices_ml.py y
# gemela.py) con planes escritos a mano y modelos falsos, sin PostgreSQL.
import numpy as np
import pytest

from analizador.analisis import gemela, indices_ml

def leer(tabla, filas, costo, filtro=None, tipo="Seq Scan"):
    n = {"Node Type": tipo, "Relation Name": tabla, "Alias": tabla, "Plan Rows": filas,
         "Total Cost": costo, "Startup Cost": 0.0, "Plan Width": 8}
    return {**n, "Filter": filtro} if filtro else n

PLAN = {"Node Type": "Hash Join", "Total Cost": 1000.0, "Startup Cost": 1.0, "Plan Rows": 50, "Plan Width": 8,
        "Hash Cond": "(orders.o_custkey = customer.c_custkey)",
        "Plans": [leer("orders", 50, 800.0, "(o_totalprice > 80000)"),
                  {"Node Type": "Hash", "Total Cost": 150.0, "Plan Rows": 200,
                   "Plans": [leer("customer", 200, 100.0)]}]}
T = {"orders": {"filas": 10_000}, "customer": {"filas": 200}}
C = {("orders", "o_totalprice"): {"distintos": 0.9, "correlacion": 0.1, "ancho": 8},
     ("orders", "o_custkey"): {"distintos": 0.02, "correlacion": 0.0, "ancho": 4}}
CLAVES = {"customer": {"c_custkey"}, "orders": {"o_orderkey"}}

class Fijo:
    def __init__(self, valor):
        self.valor = valor
    def predict(self, filas):
        return np.full(len(filas), self.valor)

@pytest.fixture
def modelos_falsos(monkeypatch):
    # El modelo de planes predice log1p(ms) = log1p(100); el de índices, 30% de mejora.
    p = {"caracteristicas": list(indices_ml.modelo.extraer_features(PLAN, 2)),
         "caracteristicas_indice": ["log_filas_tabla", "es_filtro", "es_join", "selectividad", "lee_entera",
                                    "parte_del_costo", "distintos", "correlacion", "n_tablas", "es_tabla_mas_grande"],
         "umbral": 0.1, "presupuesto": 0.6, "corte": 0.05, "peso_plan": 0.5, "peso_indice": 0.5}
    monkeypatch.setattr(indices_ml, "cargar", lambda: (Fijo(np.log1p(100.0)), Fijo(0.3), p))

def test_v2_candidatas_sin_claves_primarias_ni_columnas_con_indice():
    con_indice = {"orders": [{"columnas": ["o_custkey"]}]}
    assert indices_ml.columnas_candidatas(PLAN, CLAVES, {}) == {
        ("orders", "o_custkey"): "join", ("orders", "o_totalprice"): "filtro"}
    assert indices_ml.columnas_candidatas(PLAN, CLAVES, con_indice) == {("orders", "o_totalprice"): "filtro"}

def test_v2_recomienda_los_indices_que_mejoran_mas_de_10_por_ciento(modelos_falsos, monkeypatch):
    r = indices_ml.evaluar(PLAN, T, C, CLAVES, {})
    assert r["tiempo_actual_ms"] == pytest.approx(100.0)
    assert r["tiempo_con_indices_ms"] == pytest.approx(70.0)       # 30% de mejora predicha
    assert [(c["columna"], c["mejora_pct"], c["recomendado"]) for c in r["candidatos"]] == [
        ("o_custkey", 30.0, True), ("o_totalprice", 30.0, True)]
    # Si el modelo predice 5%, se muestran pero no se recomiendan. customer (200 filas) nunca es candidata.
    m_plan, _, p = indices_ml.cargar()
    monkeypatch.setattr(indices_ml, "cargar", lambda: (m_plan, Fijo(0.05), p))
    r = indices_ml.evaluar(PLAN, T, C, CLAVES, {})
    assert [c["recomendado"] for c in r["candidatos"]] == [False, False]
    assert r["tiempo_con_indices_ms"] == pytest.approx(100.0)

class PlanificadorFalso:
    """Tiempo del mejor plan según los índices hipotéticos que haya."""
    def __init__(self, tiempos):
        self.tiempos = tiempos
    def mejor(self, indices):
        return (self.tiempos.get(tuple(sorted(indices)), 100.0), {}, {})

def test_v3_agrega_indices_solo_si_superan_el_corte():
    a, b = ("t", "a"), ("t", "b")
    planificador = PlanificadorFalso({(a,): 60.0, (b,): 99.0, (a, b): 59.0})
    mejoras = {a: 0.4, b: 0.0}
    r = gemela.busqueda_conjunta(planificador, mejoras, {a: 1.0, b: 1.0}, presupuesto=1.0, corte=0.05, pesos=(0.5, 0.5))
    # a: 100 * (1 - (0,5*0,4 + 0,5*0,4)) = 60 ms. b después baja menos del 5%: no entra.
    assert r["indices"] == [a]
    assert (r["pred_inicio"], r["pred_final"]) == (pytest.approx(100.0), pytest.approx(60.0))

def test_v3_la_gemela_copia_la_distribucion_de_los_valores_frecuentes():
    st = {"nulos": 0.0, "distintos": 3, "frecuentes": ["CHILE", "PERU"], "frecuencias": [0.6, 0.3],
          "histograma": ["ARGENTINA", "BRAZIL", "USA"], "correlacion": 0.0, "ancho": 6}
    valores = gemela.columna_gemela(st, "text", 1000, False, np.random.default_rng(0))
    assert len(valores) == 1000
    assert (valores == "CHILE").mean() == pytest.approx(0.6, abs=0.01)
    assert (valores == "PERU").mean() == pytest.approx(0.3, abs=0.01)

def test_v3_sin_base_gemela_configurada_avisa(monkeypatch, modelos_falsos):
    monkeypatch.setattr(gemela, "GEMELA_DSN", "")
    r = gemela.recomendar("SELECT 1")
    assert r["disponible"] is False and "GEMELA_DSN" in r["motivo"]

def test_v3_no_cambia_el_plan_si_la_otra_configuracion_gana_poco(monkeypatch):
    # El plan por defecto tarda 100 ms y el de otra configuración 98 ms (2% mejor).
    class Cursor:
        def execute(self, *a):
            pass
    monkeypatch.setattr(gemela, "_variantes", lambda: [{"enable_hashjoin": False}])
    monkeypatch.setattr(gemela, "_explain", lambda cur, q, ajustes: {"ajustes": bool(ajustes)})
    monkeypatch.setattr(gemela, "forma_del_plan", lambda plan: plan["ajustes"])
    monkeypatch.setattr(gemela, "raiz", lambda plan: {"Total Cost": 1.0})
    monkeypatch.setattr(indices_ml, "predecir_ms", lambda plan, n: 98.0 if plan["ajustes"] else 100.0)
    assert gemela.Planificador(Cursor(), "q", 2, 0.0).mejor([])[1] == {"enable_hashjoin": False}
    planificador = gemela.Planificador(Cursor(), "q", 2, 0.05)
    assert planificador.mejor([])[1] == {}
    # El tiempo de hoy (contra el que se mide la mejora) es siempre el del plan por defecto.
    assert planificador.defecto[()] == 100.0
