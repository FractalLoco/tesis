# Pruebas de lo que se devuelve al navegador: valores recortados y cabeceras.
from analizador.pagina.texto import MAX_LARGO_VALOR, a_texto

def test_los_valores_enormes_se_recortan():
    texto = "x" * (MAX_LARGO_VALOR + 10)
    recortado = a_texto(texto)
    assert recortado.endswith("(recortado)")
    assert len(recortado) <= MAX_LARGO_VALOR + 20
    assert a_texto(None) == ""
