# Pruebas E2E de las pantallas de análisis: se escribe una consulta, se aprieta
# el botón y se revisa el resultado que muestra la página.
from playwright.sync_api import Page, expect

from tests.e2e.ayudas import ir_a

CONSULTA_4_TABLAS = ("SELECT count(*) FROM lineitem"
                     " JOIN orders ON l_orderkey = o_orderkey"
                     " JOIN customer ON o_custkey = c_custkey"
                     " JOIN nation ON c_nationkey = n_nationkey"
                     " WHERE n_name = 'CHILE'")

def test_optimizacion_muestra_el_plan_y_la_recomendacion(conectado: Page):
    ir_a(conectado, "Optimización de consulta")
    conectado.fill("#op-sql", CONSULTA_4_TABLAS)
    conectado.click("#op-ejecutar")
    resultado = conectado.locator("#op-resultado")
    # EXPLAIN ANALYZE ejecutó la consulta: se muestran el tiempo real y el plan.
    expect(resultado).to_contain_text("Tiempo real", timeout=20000)
    expect(resultado).to_contain_text("Plan de ejecución")
    # Bloque del modelo de ML con el orden de JOIN recomendado.
    expect(resultado).to_contain_text("Mejor tiempo estimado")

def test_prediccion_sugiere_un_indice(conectado: Page):
    ir_a(conectado, "Predicción de índice")
    conectado.fill("#pi-sql", "SELECT * FROM orders WHERE o_totalprice > 80000")
    conectado.click("#pi-ejecutar")
    expect(conectado.locator("#pi-resultado")).to_contain_text(
        "CREATE INDEX idx_orders_o_totalprice ON orders (o_totalprice);", timeout=15000)

def test_consulta_que_modifica_datos_muestra_error(conectado: Page):
    ir_a(conectado, "Optimización de consulta")
    conectado.fill("#op-sql", "DELETE FROM nation")
    conectado.click("#op-ejecutar")
    expect(conectado.locator("#op-error")).to_contain_text("Solo se permiten consultas de lectura", timeout=15000)

def test_el_ejemplo_de_optimizacion_funciona_con_la_base(conectado: Page):
    ir_a(conectado, "Optimización de consulta")
    conectado.get_by_role("button", name="Usar ejemplo").click()
    conectado.click("#op-ejecutar")
    resultado = conectado.locator("#op-resultado")
    expect(resultado).to_contain_text("Tiempo real", timeout=20000)
    expect(resultado).to_contain_text("Mejor tiempo estimado")   # el ejemplo tiene 4 tablas: aplica el modelo

def test_el_ejemplo_de_prediccion_sugiere_un_indice(conectado: Page):
    ir_a(conectado, "Predicción de índice")
    conectado.get_by_role("button", name="Usar ejemplo").click()
    conectado.click("#pi-ejecutar")
    expect(conectado.locator("#pi-resultado")).to_contain_text("CREATE INDEX", timeout=15000)
