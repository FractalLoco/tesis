# Pruebas de integración de la conexión (/api/conectar): la API funcionando
# junto a un PostgreSQL real. No se reemplaza nada: cada prueba hace una
# petición HTTP y recorre API → servicios → analizador → PostgreSQL.
# Usan la base del .env con el usuario de solo lectura, así que no modifican datos.
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from tests.base_de_prueba import CONEXION, hay_base

# Si no hay base de prueba (por ejemplo en GitHub Actions) se omiten en vez de fallar.
pytestmark = pytest.mark.skipif(not hay_base(), reason="sin base de prueba en el .env")

cliente = TestClient(app)

def test_conecta_y_detecta_usuario_de_solo_lectura():
    r = cliente.post("/api/conectar", json=CONEXION)
    assert r.status_code == 200                       # 200 = todo bien
    datos = r.json()
    assert datos["ok"] is True
    assert datos["usuario_solo_lectura"] is True
    assert datos["n_tablas"] == 7

def test_clave_incorrecta_responde_401():
    # {**CONEXION, "password": ...} copia los datos cambiando solo la clave.
    r = cliente.post("/api/conectar", json={**CONEXION, "password": "otra"})
    assert r.status_code == 401                       # 401 = no autorizado
    assert r.json()["codigo"] == "credenciales_invalidas"

def test_base_que_no_existe_responde_404():
    r = cliente.post("/api/conectar", json={**CONEXION, "dbname": "no_existe"})
    assert r.status_code == 404                       # 404 = no encontrado
    assert r.json()["codigo"] == "base_no_existe"

def test_puerto_sin_servidor_responde_502():
    # En el puerto 1 no hay ningún PostgreSQL escuchando.
    r = cliente.post("/api/conectar", json={**CONEXION, "port": "1"})
    assert r.status_code == 502                       # 502 = no se pudo llegar al servidor
    assert r.json()["codigo"] == "servidor_inalcanzable"
