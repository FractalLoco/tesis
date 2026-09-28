from pydantic import BaseModel

from backend.config import DB_HOST, DB_PORT

class Conexion(BaseModel):

    host: str = DB_HOST
    port: str = DB_PORT
    dbname: str
    user: str
    password: str = ""

class ConexionBody(BaseModel):
    conexion: Conexion

class PreviewIn(BaseModel):
    conexion: Conexion
    esquema: str
    tabla: str
    limit: int = 50

class ConsultaSQL(BaseModel):
    conexion: Conexion
    sql: str
    limit: int = 200

class AnalizarIn(BaseModel):
    conexion: Conexion
    query: str

class PrediccionIn(BaseModel):
    conexion: Conexion
    query: str
