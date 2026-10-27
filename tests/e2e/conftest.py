# Preparación compartida por las pruebas E2E. pytest carga este archivo solo,
# antes de las pruebas de esta carpeta.
#
# Para ver el navegador mientras corren (ventana maximizada, más lento, 20 s
# abierta después de ingresar y una pausa al final de cada prueba):
#   .venv/bin/python -m pytest tests/e2e --headed --slowmo 700
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from tests.base_de_prueba import CONEXION, hay_base

# Si Playwright no está instalado, estas pruebas se omiten.
pytest.importorskip("playwright")
from playwright.sync_api import Page, expect  # noqa: E402

from tests.e2e.ayudas import PUERTO, URL, ingresar  # noqa: E402

# Pausas que solo se aplican con --headed, para alcanzar a ver la ventana:
PAUSA_INGRESO_MS = 20000   # después de ingresar, con los datos de la base ya cargados
PAUSA_MS = 3000            # al terminar cada prueba
HAY_BASE = hay_base()

CARPETA_E2E = Path(__file__).parent

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # Con --headed, en algunos equipos Chromium deja de dibujar la página (por la
    # aceleración gráfica o si la ventana queda tapada) y Playwright se queda
    # esperando a que los elementos estén quietos. Sin GPU y sin pausas, no pasa.
    return {**browser_type_launch_args, "args": [
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-background-timer-throttling",
        "--disable-gpu",
        "--start-maximized",
    ]}

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, pytestconfig):
    # Con --headed la página ocupa toda la ventana maximizada en vez del tamaño
    # fijo de 1280x720 que usa Playwright por defecto.
    if pytestconfig.getoption("headed"):
        return {**browser_context_args, "no_viewport": True}
    return browser_context_args

def pytest_collection_modifyitems(items):
    # Sin base de prueba en el .env (por ejemplo en GitHub Actions) se omiten.
    # pytest pasa aquí las pruebas de todo el proyecto: solo se marcan las de esta carpeta.
    if not HAY_BASE:
        for item in items:
            if CARPETA_E2E in item.path.parents:
                item.add_marker(pytest.mark.skip(reason="sin base de prueba en el .env"))

# Un fixture prepara algo antes de las pruebas. Este levanta la app completa en
# segundo plano una sola vez y la apaga al terminar (lo que va después del yield).
@pytest.fixture(scope="session")
def servidor():
    srv = uvicorn.Server(uvicorn.Config("backend.main:app", host="127.0.0.1", port=PUERTO, log_level="warning"))
    hilo = threading.Thread(target=srv.run, daemon=True)
    hilo.start()
    while not srv.started:
        time.sleep(0.05)
    yield
    srv.should_exit = True
    hilo.join()

@pytest.fixture(autouse=True)
def pausa_al_final(request, servidor, page: Page):
    # Con --headed deja la ventana abierta unos segundos para alcanzar a ver el resultado.
    yield
    if request.config.getoption("headed"):
        page.wait_for_timeout(PAUSA_MS)

@pytest.fixture
def conectado(request, page: Page):
    """Entrega una pestaña que ya ingresó a la base y está en /tablas."""
    ingresar(page, CONEXION["password"])
    # expect espera hasta 15 s a que se cumpla (la validación tiene animación).
    expect(page).to_have_url(f"{URL}/tablas", timeout=15000)
    # Se espera a que aparezcan las tablas de la base antes de seguir.
    expect(page.locator(".acc-item").first).to_be_visible()
    if request.config.getoption("headed"):
        page.wait_for_timeout(PAUSA_INGRESO_MS)
    return page
