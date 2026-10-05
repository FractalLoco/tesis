from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from backend.config import DB_HOST, DB_PORT

# Límites de lo que la API acepta. Se validan aquí, al recibir la petición, en
# vez de corregirse en silencio más adelante.
MAX_FILAS_TABLA = 200
MAX_FILAS_CONSOLA = 1000
MAX_LARGO_SQL = 20_000

class Entrada(BaseModel):
    # Quita espacios al inicio y al final de todos los textos recibidos.
    model_config = ConfigDict(str_strip_whitespace=True)

class Conexion(Entrada):

    host: str = Field(DB_HOST, min_length=1, max_length=255)
    port: str = DB_PORT
    dbname: str = Field(min_length=1, max_length=63)
    user: str = Field(min_length=1, max_length=63)
    # La contraseña se recibe tal cual: un espacio al inicio o al final es válido.
    password: Annotated[str, StringConstraints(strip_whitespace=False, max_length=1024)] = ""

    @field_validator("port")
    @classmethod
    def puerto_valido(cls, v: str) -> str:
        if not v.isdigit() or not 1 <= int(v) <= 65535:
            raise ValueError("debe ser un número entre 1 y 65535")
        return v

class ConexionBody(Entrada):
    conexion: Conexion

class PreviewIn(Entrada):
    conexion: Conexion
    esquema: str = Field(min_length=1, max_length=63)
    tabla: str = Field(min_length=1, max_length=63)
    limit: int = Field(50, ge=1, le=MAX_FILAS_TABLA)

class ConsultaSQL(Entrada):
    conexion: Conexion
    sql: str = Field(max_length=MAX_LARGO_SQL)
    limit: int = Field(200, ge=1, le=MAX_FILAS_CONSOLA)

class AnalizarIn(Entrada):
    conexion: Conexion
    query: str = Field(max_length=MAX_LARGO_SQL)

class PrediccionIn(Entrada):
    conexion: Conexion
    query: str = Field(max_length=MAX_LARGO_SQL)
