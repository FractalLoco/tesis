# Pruebas de lo que se devuelve al navegador: valores recortados y cabeceras.
from fastapi.testclient import TestClient

from analizador.pagina.texto import MAX_LARGO_VALOR, a_texto
from backend.main import app

cliente = TestClient(app)

def test_los_valores_enormes_se_recortan():
    texto = "x" * (MAX_LARGO_VALOR + 10)
    recortado = a_texto(texto)
    assert recortado.endswith("(recortado)")
    assert len(recortado) <= MAX_LARGO_VALOR + 20
    assert a_texto(None) == ""

def test_cabeceras_de_seguridad_y_sin_cache_en_la_api():
    r = cliente.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["Cache-Control"] == "no-store"
