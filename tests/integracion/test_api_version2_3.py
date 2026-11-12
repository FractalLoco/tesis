# Pruebas de integración de la V2 y la V3 contra la base de prueba. La V2 necesita
# los modelos en ml/; la V3 además un PostgreSQL propio con HypoPG (GEMELA_DSN).
import pytest
from fastapi.testclient import TestClient

from analizador.analisis import gemela, indices_ml
from backend.main import app
from tests.base_de_prueba import CONEXION, hay_base

pytestmark = [pytest.mark.skipif(not hay_base(), reason="sin base de prueba en el .env"),
              pytest.mark.skipif(not indices_ml.disponible(), reason="faltan los modelos de la V2 y la V3 en ml/")]

cliente = TestClient(app)
CONSULTA = ("SELECT count(*) FROM orders JOIN customer ON o_custkey = c_custkey"
            " JOIN nation ON c_nationkey = n_nationkey WHERE o_totalprice > 80000 AND n_name = 'CHILE'")

def test_v2_propone_indice_en_la_columna_del_filtro_sin_indice():
    r = cliente.post("/api/version2", json={"conexion": CONEXION, "query": CONSULTA})
    assert r.status_code == 200
    datos = r.json()
    columnas = {(c["tabla"], c["columna"]) for c in datos["candidatos"]}
    assert ("orders", "o_totalprice") in columnas
    # Las que ya tienen índice o son clave primaria no son candidatas.
    assert ("orders", "o_custkey") not in columnas and ("customer", "c_custkey") not in columnas
    assert all(c["recomendado"] == (c["mejora_pct"] > 10) for c in datos["candidatos"])
    assert datos["tiempo_con_indices_ms"] <= datos["tiempo_actual_ms"]

def test_v2_rechaza_consultas_que_modifican_datos():
    r = cliente.post("/api/version2", json={"conexion": CONEXION, "query": "DELETE FROM nation"})
    assert r.status_code == 403

@pytest.mark.skipif(not gemela.configurada(), reason="sin GEMELA_DSN (PostgreSQL con HypoPG para la base gemela)")
def test_v3_elige_indices_y_plan_en_la_gemela_sin_tocar_el_servidor():
    r = cliente.post("/api/version3", json={"conexion": CONEXION, "query": CONSULTA})
    assert r.status_code == 200
    datos = r.json()
    assert datos["disponible"], datos.get("motivo")
    assert datos["tiempo_final_ms"] <= datos["tiempo_actual_ms"]
    assert datos["gemela_mismo_plan"]                 # la gemela planifica igual que el servidor
    # En el servidor no aparece ningún índice nuevo ni HypoPG.
    indices = cliente.post("/api/indices", json={"conexion": CONEXION}).json()["indices"]
    assert len({i["indice"] for i in indices}) == 16

def test_el_usuario_de_solo_lectura_ve_las_claves_primarias():
    # Sin las claves, la gemela se arma sin sus índices y planifica distinto que el servidor.
    from analizador.conexion import get_readonly_connection
    with get_readonly_connection(CONEXION) as conn:
        claves = gemela.leer_servidor(conn)["claves"]
    assert claves["orders"] == ["o_orderkey"] and claves["customer"] == ["c_custkey"]
