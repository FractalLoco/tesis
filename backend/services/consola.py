from analizador.consola import ejecutar_consulta as ejecutar
from backend.services.reglas import PARA_CONSOLA, validar_consulta

def ejecutar_consulta(sql: str, limit: int, config: dict | None = None) -> dict:

    return ejecutar(validar_consulta(sql, PARA_CONSOLA), limit, config)
