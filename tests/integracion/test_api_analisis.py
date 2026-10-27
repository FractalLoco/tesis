# Pruebas de integración de las rutas que trabajan con consultas: consola,
# análisis del plan con el modelo de ML, predicción de índices y estadísticas.
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.base_de_prueba import CONEXION, hay_base

pytestmark = pytest.mark.skipif(not hay_base(), reason="sin base de prueba en el .env")

cliente = TestClient(app)
BODY = {"conexion": CONEXION}

CONSULTA_4_TABLAS = ("SELECT count(*) FROM lineitem"
                     " JOIN orders ON l_orderkey = o_orderkey"
                     " JOIN customer ON o_custkey = c_custkey"
                     " JOIN nation ON c_nationkey = n_nationkey"
                     " WHERE n_name = 'CHILE'")

def test_la_consola_devuelve_filas():
    r = cliente.post("/api/consulta", json={**BODY, "sql": "SELECT n_name FROM nation ORDER BY n_nationkey LIMIT 3"})
    assert r.status_code == 200
    assert r.json()["filas"] == [["CHILE"], ["ARGENTINA"], ["BRAZIL"]]

def test_la_consola_rechaza_un_delete():
    r = cliente.post("/api/consulta", json={**BODY, "sql": "DELETE FROM nation"})
    assert r.status_code == 403                       # 403 = prohibido
    assert r.json()["codigo"] == "consulta_no_permitida"

def test_analiza_consulta_de_4_tablas_con_el_modelo():
    r = cliente.post("/api/analizar", json={**BODY, "query": CONSULTA_4_TABLAS})
    assert r.status_code == 200
    datos = r.json()
    # EXPLAIN ANALYZE ejecutó la consulta de verdad y midió su tiempo.
    assert datos["analisis"]["tiempo_real_ms"] > 0
    # El modelo de ML aplica (4 tablas con INNER JOIN) y su mejor plan
    # nunca puede ser más lento que el que eligió PostgreSQL.
    ml = datos["recomendacion_ml"]
    assert ml["aplica"] and ml["n_tablas"] == 4
    assert ml["tiempo_mejor_ms"] <= ml["tiempo_actual_ms"]

def test_prediccion_sugiere_indice_para_un_filtro_sin_indice():
    r = cliente.post("/api/prediccion-indices", json={**BODY, "query": "SELECT * FROM orders WHERE o_totalprice > 80000"})
    assert r.status_code == 200
    sugerencias = [x["sql_sugerido"] for x in r.json()["recomendaciones"]]
    assert "CREATE INDEX idx_orders_o_totalprice ON orders (o_totalprice);" in sugerencias

def test_estadisticas_de_la_base():
    r = cliente.post("/api/estadisticas", json=BODY)
    assert r.status_code == 200
    datos = r.json()
    assert datos["conexiones"] >= 1                   # al menos la nuestra
    assert 0 <= datos["cache_hit_ratio"] <= 100       # es un porcentaje
