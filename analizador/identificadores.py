"""Cita nombres de tablas, columnas e índices en el SQL sugerido.

Un nombre con mayúsculas, espacios, comillas o palabra reservada se escribe entre
comillas dobles; los nombres normales quedan igual.
"""
import re

_SIMPLE = re.compile(r"^[a-z_][a-z0-9_]*$")

# Palabras reservadas de PostgreSQL (sin comillas no sirven como nombre).
_RESERVADAS = frozenset("""
    all analyse analyze and any array as asc asymmetric both case cast check
    collate column constraint create current_catalog current_date current_role
    current_time current_timestamp current_user default deferrable desc distinct
    do else end except false fetch for foreign from grant group having in
    initially intersect into lateral leading limit localtime localtimestamp not
    null offset on only or order placing primary references returning select
    session_user some symmetric table then to trailing true union unique user
    using variadic when where window with
""".split())

def citar(nombre: str) -> str:
    texto = str(nombre)
    if _SIMPLE.fullmatch(texto) and texto not in _RESERVADAS:
        return texto
    return '"' + texto.replace('"', '""') + '"'
