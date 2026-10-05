"""Normaliza los errores de la API a un formato único y en español.

Toda respuesta de error tiene la forma:
    {"codigo": "credenciales_invalidas", "mensaje": "...", "detalle": "..." | null}

- codigo:  identificador estable, pensado para que el frontend decida qué hacer.
- mensaje: texto claro para el usuario.
- detalle: el texto técnico original (limpio), o null si no aporta.
"""
import logging

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("backend.errores")

class ErrorNegocio(Exception):
    """Error esperado de una regla del sistema (por ejemplo, una consulta no permitida)."""

    def __init__(self, codigo: str, mensaje: str, status: int = 400, detalle: str | None = None):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.status = status
        self.detalle = detalle

# SQLSTATE de PostgreSQL -> (status HTTP, código, mensaje para el usuario).
# https://www.postgresql.org/docs/current/errcodes-appendix.html
POR_SQLSTATE = {
    "28P01": (401, "credenciales_invalidas", "Usuario o contraseña incorrectos."),
    "28000": (403, "acceso_denegado", "El servidor PostgreSQL no permite el acceso a este usuario desde aquí."),
    "3D000": (404, "base_no_existe", "La base de datos indicada no existe en el servidor."),
    "42501": (403, "sin_permisos", "El usuario no tiene permisos para leer este objeto. Revisa los GRANT del usuario de solo lectura."),
    "25006": (403, "solo_lectura", "La conexión es de solo lectura: no se permiten consultas que modifiquen datos."),
    "57014": (504, "tiempo_agotado", "La consulta tardó demasiado y fue cancelada."),
    "53300": (503, "demasiadas_conexiones", "El servidor PostgreSQL no acepta más conexiones en este momento."),
    "42601": (400, "error_sintaxis", "La consulta tiene un error de sintaxis."),
    "42P01": (400, "tabla_no_existe", "La consulta usa una tabla que no existe."),
    "42703": (400, "columna_no_existe", "La consulta usa una columna que no existe."),
    "42883": (400, "funcion_no_existe", "La consulta usa una función u operador que no existe para esos tipos."),
    "42804": (400, "tipo_incorrecto", "La consulta mezcla tipos de datos incompatibles."),
}

# Clases de SQLSTATE (los dos primeros caracteres) para lo que no está arriba.
POR_CLASE = {
    "08": (502, "servidor_inalcanzable", "Se perdió la conexión con el servidor PostgreSQL."),
    "22": (400, "datos_invalidos", "La consulta usa un valor con formato inválido."),
    "42": (400, "consulta_invalida", "PostgreSQL rechazó la consulta."),
}

# Los errores al CONECTAR llegan sin SQLSTATE y en el idioma y codificación del
# servidor (por eso a veces traen caracteres "�"). Se reconocen por fragmentos
# del texto, en inglés y en español, que no incluyen letras con tilde.
POR_TEXTO = [
    (("authentication failed", "autentificaci", "autenticaci", "password"),
     (401, "credenciales_invalidas", "Usuario o contraseña incorrectos.")),
    (("does not exist", "no existe"),
     (404, "base_no_existe", "La base de datos o el usuario indicado no existe en el servidor.")),
    (("pg_hba",),
     (403, "acceso_denegado", "El servidor PostgreSQL no permite conexiones desde esta dirección (pg_hba.conf).")),
    (("timeout", "timed out"),
     (504, "servidor_no_responde", "El servidor PostgreSQL no respondió a tiempo. Revisa el host y el puerto.")),
    (("refused", "rechaz", "resolve host", "could not translate host", "nodename nor servname", "could not connect", "connection failed"),
     (502, "servidor_inalcanzable", "No se pudo llegar al servidor PostgreSQL. Revisa el host, el puerto y que el servidor esté encendido.")),
]

ERROR_BD = (400, "error_base_datos", "PostgreSQL no pudo completar la operación.")

def limpiar_detalle(texto: str) -> str | None:
    """Deja solo la parte útil del mensaje técnico de psycopg.

    Si el texto llegó con caracteres mal decodificados ("�"), se descarta: el
    mensaje traducido ya explica el problema y el detalle solo confundiría.
    """
    texto = (texto or "").strip()
    if not texto or "�" in texto:
        return None
    # psycopg repite el mismo error por cada dirección que intentó (IPv4/IPv6).
    texto = texto.split("\nMultiple connection attempts failed")[0]
    # Quita el prefijo 'connection failed: connection to server at "x", port n failed: '.
    if "failed: " in texto and texto.startswith("connection"):
        texto = texto.rsplit("failed: ", 1)[-1]
    return texto.replace("FATAL:  ", "").strip() or None

def traducir_psycopg(exc: psycopg.Error) -> tuple[int, str, str]:
    estado = getattr(exc, "sqlstate", None)
    if estado in POR_SQLSTATE:
        return POR_SQLSTATE[estado]
    if estado and estado[:2] in POR_CLASE:
        return POR_CLASE[estado[:2]]
    if not estado:
        texto = str(exc).lower()
        for fragmentos, resultado in POR_TEXTO:
            if any(f in texto for f in fragmentos):
                return resultado
    return ERROR_BD

def respuesta(status: int, codigo: str, mensaje: str, detalle: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"codigo": codigo, "mensaje": mensaje, "detalle": detalle})

def _campo(loc) -> str:
    # ("body", "conexion", "dbname") -> "conexion.dbname"
    return ".".join(str(p) for p in loc if p != "body")

def _explicar(e: dict) -> str:
    """Traduce al español los errores de validación más comunes de Pydantic."""
    ctx = e.get("ctx") or {}
    textos = {
        "missing": "es obligatorio",
        "string_too_short": "no puede estar vacío",
        "string_too_long": f"admite como máximo {ctx.get('max_length')} caracteres",
        "greater_than_equal": f"debe ser mayor o igual a {ctx.get('ge')}",
        "less_than_equal": f"debe ser menor o igual a {ctx.get('le')}",
        "int_parsing": "debe ser un número entero",
        "int_type": "debe ser un número entero",
    }
    if e.get("type") in textos:
        return textos[e["type"]]
    return str(e.get("msg", "")).removeprefix("Value error, ")

def registrar_manejadores(app: FastAPI) -> None:

    @app.exception_handler(ErrorNegocio)
    async def _negocio(_: Request, exc: ErrorNegocio):
        return respuesta(exc.status, exc.codigo, exc.mensaje, exc.detalle)

    @app.exception_handler(psycopg.Error)
    async def _postgres(_: Request, exc: psycopg.Error):
        status, codigo, mensaje = traducir_psycopg(exc)
        return respuesta(status, codigo, mensaje, limpiar_detalle(str(exc)))

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError):
        errores = exc.errors()
        faltan = [_campo(e["loc"]) for e in errores if e.get("type") == "missing"]
        if faltan:
            mensaje = "Faltan datos obligatorios: " + ", ".join(faltan) + "."
        elif len(errores) == 1:
            mensaje = f"El dato «{_campo(errores[0]['loc'])}» {_explicar(errores[0])}."
        else:
            mensaje = "Algunos datos enviados no tienen un formato válido."
        detalle = "\n".join(f"{_campo(e['loc'])}: {_explicar(e)}" for e in errores)
        return respuesta(422, "datos_invalidos", mensaje, detalle)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        mensajes = {404: "La ruta solicitada no existe.", 405: "Método no permitido para esta ruta."}
        return respuesta(exc.status_code, "error_http",
                         mensajes.get(exc.status_code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception):
        log.exception("Error no controlado", exc_info=exc)
        return respuesta(500, "error_interno",
                         "Ocurrió un error inesperado en el servidor. Intenta de nuevo.")
