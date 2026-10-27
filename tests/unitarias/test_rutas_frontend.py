# Pruebas de cómo el backend sirve el frontend.
# TestClient simula peticiones HTTP a la app sin levantar un servidor real.
import pytest
from fastapi.testclient import TestClient

from backend.main import app

cliente = TestClient(app)

# parametrize repite la misma prueba con cada valor de la lista.
@pytest.mark.parametrize("ruta", ["/", "/conexion", "/tablas", "/diagrama", "/optimizacion"])
def test_las_pantallas_devuelven_la_pagina(ruta):
    # Las rutas de pantalla no son archivos: devuelven index.html y el router
    # del navegador decide qué mostrar.
    r = cliente.get(ruta)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")

@pytest.mark.parametrize("ruta", ["/api", "/api/", "/api/no-existe", "/css/no-existe.css"])
def test_rutas_de_api_o_archivos_que_no_existen_dan_404(ruta):
    assert cliente.get(ruta).status_code == 404

def test_los_archivos_js_se_sirven_como_javascript():
    r = cliente.get("/js/main.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
