"""Reglas de negocio sobre las consultas que el usuario envía a su base.

El sistema promete no modificar nunca la base analizada. La conexión ya es de
solo lectura, pero además se valida la consulta ANTES de enviarla: una sola
sentencia y solo de lectura. Así se rechaza con un mensaje claro algo como
"SET default_transaction_read_only = off; DELETE FROM t", que intenta
desactivar la protección en la misma petición.
"""
import re

from backend.errores import ErrorNegocio

# Sentencias aceptadas según el módulo que las recibe.
PARA_ANALISIS = ("SELECT", "WITH", "VALUES", "TABLE")
PARA_CONSOLA = PARA_ANALISIS + ("SHOW", "EXPLAIN")

# Un WITH puede esconder una escritura: WITH x AS (DELETE FROM t RETURNING *) SELECT ...
_ESCRITURA_EN_CTE = re.compile(
    r"\b(INSERT\s+INTO|UPDATE\s+[\w.\"]+\s+SET|DELETE\s+FROM|MERGE\s+INTO)\b", re.IGNORECASE
)
_DOLAR = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")

def _sin_literales(sql: str) -> str:
    """Devuelve el SQL sin comentarios, textos entre comillas ni bloques $$...$$,
    para poder buscar ';' y palabras clave sin falsos positivos."""
    salida, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if sql.startswith("--", i):
            fin = sql.find("\n", i)
            i = n if fin < 0 else fin
        elif sql.startswith("/*", i):
            fin = sql.find("*/", i + 2)
            i = n if fin < 0 else fin + 2
            salida.append(" ")
        elif c in ("'", '"'):
            j = i + 1
            while j < n:
                if sql[j] == c and sql.startswith(c * 2, j):
                    j += 2
                elif sql[j] == c:
                    break
                else:
                    j += 1
            i = j + 1
            salida.append(" x ")
        elif c == "$" and (m := _DOLAR.match(sql, i)):
            fin = sql.find(m.group(0), m.end())
            i = n if fin < 0 else fin + len(m.group(0))
            salida.append(" x ")
        else:
            salida.append(c)
            i += 1
    return "".join(salida)

def validar_consulta(sql: str, permitidas: tuple[str, ...] = PARA_ANALISIS) -> str:
    """Valida que sea UNA sentencia de lectura. Devuelve el SQL sin el ';' final."""
    sql = (sql or "").strip()
    if not sql:
        raise ErrorNegocio("consulta_vacia", "Escribe una consulta antes de continuar.")

    limpio = _sin_literales(sql).strip().rstrip(";").strip()
    if not limpio:
        raise ErrorNegocio("consulta_vacia", "La consulta solo contiene comentarios.")
    if ";" in limpio:
        raise ErrorNegocio("varias_sentencias",
                           "Envía una sola consulta a la vez (sin varias sentencias separadas por ';').")

    primera = limpio.lstrip("( \n\t").split(None, 1)[0].upper()
    if primera not in permitidas:
        raise ErrorNegocio("consulta_no_permitida",
                           f"Solo se permiten consultas de lectura ({', '.join(permitidas)}). "
                           f"La consulta empieza con {primera}.",
                           status=403)
    if primera == "WITH" and _ESCRITURA_EN_CTE.search(limpio):
        raise ErrorNegocio("consulta_no_permitida",
                           "La consulta WITH incluye una escritura (INSERT, UPDATE, DELETE o MERGE), "
                           "que no está permitida.",
                           status=403)

    return sql.rstrip().rstrip(";").rstrip()
