"""Valores de la base como texto para el navegador, recortando los enormes."""

MAX_LARGO_VALOR = 4000

def a_texto(valor) -> str:
    if valor is None:
        return ""
    texto = str(valor)
    if len(texto) > MAX_LARGO_VALOR:
        return texto[:MAX_LARGO_VALOR] + "… (recortado)"
    return texto
