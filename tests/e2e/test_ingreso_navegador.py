# Pruebas E2E del ingreso: un navegador real (Playwright + Chromium) usa la
# aplicación como una persona, recorriendo navegador → frontend → API → PostgreSQL.
import re

from playwright.sync_api import Page, expect

from analizador import conexion
from tests.base_de_prueba import CONEXION
from tests.e2e.ayudas import URL, ingresar, ir_a

# "conectado" y "page" son fixtures: pytest los entrega listos (ver conftest.py).
def test_ingresa_y_muestra_las_tablas(conectado: Page):
    # Las 7 tablas de la base aparecen en la lista, cada una con su cantidad de filas.
    expect(conectado.locator(".acc-item")).to_have_count(7)
    expect(conectado.locator(".acc-item[data-tabla=nation]")).to_contain_text("25 filas")

def test_clave_incorrecta_muestra_el_error(page: Page):
    ingresar(page, "otra")
    expect(page.locator("#carga-error")).to_contain_text("contraseña", timeout=15000)

def test_salir_vuelve_a_la_pantalla_de_conexion(conectado: Page):
    ir_a(conectado, "Salir de la base de datos")
    expect(conectado).to_have_url(f"{URL}/conexion")
    expect(conectado.get_by_role("button", name="Ingresar")).to_be_visible()

def test_formulario_precargado_entra_sin_escribir_la_clave(page: Page, monkeypatch):
    # Con PRECARGAR_CONEXION activo la pantalla llega llena con la base del .env
    # y la contraseña se puede dejar en blanco: basta con apretar Ingresar.
    monkeypatch.setattr(conexion, "PRECARGAR_CONEXION", True)
    page.goto(f"{URL}/conexion")
    expect(page.locator("#dbname")).to_have_value(CONEXION["dbname"])
    expect(page.locator("#user")).to_have_value(CONEXION["user"])
    expect(page.locator("#password")).to_have_attribute("placeholder", re.compile("Guardada en el servidor"))
    expect(page.locator("#password")).to_have_value("")
    page.get_by_role("button", name="Ingresar").click()
    expect(page).to_have_url(f"{URL}/tablas", timeout=15000)
