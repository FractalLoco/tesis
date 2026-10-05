"""Lectura del catálogo de la base: tablas, índices, relaciones y estadísticas.

Por ahora no tiene reglas propias más allá de las de la conexión; existe para que
todas las rutas pasen por la capa de servicios y no llamen directo al analizador.
"""
from analizador.catalogo import listar_tablas, preview_tabla
from analizador.diagrama import obtener_diagrama
from analizador.estadisticas import obtener_estadisticas
from analizador.indices import listar_todos_indices

__all__ = [
    "listar_tablas",
    "listar_todos_indices",
    "obtener_diagrama",
    "obtener_estadisticas",
    "preview_tabla",
]
