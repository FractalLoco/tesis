# Pruebas de integración de las rutas que leen la estructura de la base:
# tablas, vista previa, diagrama e índices. Revisan los datos reales de la
# base de prueba (esquema tipo TPC-H con 7 tablas).
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.base_de_prueba import CONEXION, hay_base

pytestmark = pytest.mark.skipif(not hay_base(), reason="sin base de prueba en el .env")

cliente = TestClient(app)
BODY = {"conexion": CONEXION}

def test_lista_las_7_tablas_de_la_base():
    r = cliente.post("/api/tablas", json=BODY)
    assert r.status_code == 200
    nombres = {t["tabla"] for t in r.json()["tablas"]}
    assert nombres == {"region", "nation", "supplier", "customer", "part", "orders", "lineitem"}

def test_vista_previa_de_una_tabla():
    r = cliente.post("/api/tabla", json={**BODY, "esquema": "public", "tabla": "nation", "limit": 5})
    assert r.status_code == 200
    datos = r.json()
    assert [c["nombre"] for c in datos["columnas"]] == ["n_nationkey", "n_name", "n_regionkey"]
    assert datos["n_filas"] == 5                      # respeta el límite pedido
    assert datos["filas"][0][1] == "CHILE"

def test_vista_previa_de_tabla_inexistente_responde_400():
    r = cliente.post("/api/tabla", json={**BODY, "esquema": "public", "tabla": "no_existe"})
    assert r.status_code == 400                       # 400 = la petición tiene un problema
    assert r.json()["codigo"] == "tabla_no_existe"

def test_diagrama_trae_tablas_y_relaciones():
    r = cliente.post("/api/diagrama", json=BODY)
    assert r.status_code == 200
    datos = r.json()
    assert len(datos["tablas"]) == 7
    assert len(datos["relaciones"]) == 7
    # Ejemplo de relación: customer.c_nationkey apunta a nation.n_nationkey.
    rel = next(x for x in datos["relaciones"] if x["desde"]["tabla"] == "customer")
    assert rel["hacia"]["tabla"] == "nation"

def test_indices_de_la_base():
    r = cliente.post("/api/indices", json=BODY)
    assert r.status_code == 200
    nombres = {i["indice"] for i in r.json()["indices"]}
    assert len(nombres) == 16
    assert "lineitem_l_orderkey_idx" in nombres
