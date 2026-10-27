# Funciones que usan varias pruebas E2E: ingresar a la base y moverse por el menú.
from playwright.sync_api import Page, expect

from tests.base_de_prueba import CONEXION

PUERTO = 8765
URL = f"http://127.0.0.1:{PUERTO}"

def ingresar(page: Page, password):
    """Llena la pantalla de conexión y aprieta Ingresar. "#host" busca el
    elemento con id="host" en el HTML."""
    page.goto(f"{URL}/conexion")
    page.fill("#host", CONEXION["host"])
    page.fill("#port", CONEXION["port"])
    page.fill("#dbname", CONEXION["dbname"])
    page.fill("#user", CONEXION["user"])
    page.fill("#password", password)
    # Antes de enviar se confirma que los campos quedaron bien (el autocompletado
    # del navegador podría cambiarlos).
    expect(page.locator("#user")).to_have_value(CONEXION["user"])
    expect(page.locator("#password")).to_have_value(password)
    page.get_by_role("button", name="Ingresar").click()

def ir_a(page: Page, nombre):
    # La conexión vive en memoria: recargar la página la pierde. Por eso se
    # navega con el menú, como lo haría una persona.
    page.locator("#navbar").get_by_role("link", name=nombre).click()
