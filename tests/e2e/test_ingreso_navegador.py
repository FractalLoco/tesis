# Pruebas E2E del ingreso: un navegador real (Playwright + Chromium) usa la
# aplicación como una persona, recorriendo navegador → frontend → API → PostgreSQL.
from playwright.sync_api import Page, expect

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
