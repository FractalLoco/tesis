import pytest
from fastapi.testclient import TestClient

from backend.main import app

cliente = TestClient(app)

@pytest.mark.parametrize("ruta", ["/", "/conexion", "/tablas", "/diagrama", "/optimizacion"])
def test_rutas_de_pantalla_devuelven_index(ruta):
    r = cliente.get(ruta)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")

@pytest.mark.parametrize("ruta", ["/api", "/api/", "/api/no-existe", "/css/no-existe.css"])
def test_api_y_archivos_inexistentes_siguen_dando_404(ruta):
    assert cliente.get(ruta).status_code == 404

def test_archivos_estaticos_se_sirven_tal_cual():
    r = cliente.get("/js/main.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
