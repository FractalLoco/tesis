# Pruebas E2E de las pantallas que muestran la base: datos de una tabla,
# índices y diagrama. Cada una entra a la base, va a la pantalla por el menú
# y revisa que aparezcan los datos reales.
from playwright.sync_api import Page, expect

from tests.e2e.ayudas import ir_a

def test_abrir_una_tabla_muestra_sus_filas(conectado: Page):
    # Clic en la fila de "nation" para desplegar su vista previa.
    conectado.click(".acc-item[data-tabla=nation] .acc-head")
    expect(conectado.get_by_text("filas 1–10 de 25")).to_be_visible()
    expect(conectado.get_by_role("cell", name="CHILE")).to_be_visible()

def test_la_pantalla_de_indices_lista_los_indices(conectado: Page):
    conectado.get_by_text("Índices", exact=True).first.click()
    expect(conectado.get_by_role("heading", name="Índices de la base de datos")).to_be_visible()
    expect(conectado.locator("#idx-resumen")).to_contain_text("16")   # 16 índices en la base
    expect(conectado.get_by_text("lineitem_l_orderkey_idx").first).to_be_visible()

def test_el_diagrama_muestra_tablas_y_relaciones(conectado: Page):
    ir_a(conectado, "Diagrama de tablas")
    expect(conectado.locator("#diag-resumen")).to_contain_text("7 tablas · 7 relaciones")
    expect(conectado.locator("#diag-lienzo svg")).to_be_visible()
