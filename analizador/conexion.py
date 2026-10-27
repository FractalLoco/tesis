import psycopg

from backend.config import (
    DB_CONNECT_TIMEOUT,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    PRECARGAR_CONEXION,
)

DESTINO = ("host", "port", "dbname", "user")

def get_db_config(overrides: dict | None = None) -> dict:
    defecto = {
        "host": DB_HOST,
        "port": DB_PORT,
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
    }
    if not overrides:
        return defecto
    cfg = {**defecto, **{k: v for k, v in overrides.items() if v not in (None, "")}}
    # Con la contraseña en blanco solo se usa la del .env si PRECARGAR_CONEXION está
    # activo y la conexión es a la misma base del .env: nunca se envía a otro servidor.
    if not overrides.get("password"):
        misma_base = all(str(cfg[k]) == str(defecto[k]) for k in DESTINO)
        if not (PRECARGAR_CONEXION and misma_base):
            cfg["password"] = ""
    return cfg

def get_readonly_connection(config: dict | None = None) -> psycopg.Connection:
    conn = psycopg.connect(**get_db_config(config), connect_timeout=DB_CONNECT_TIMEOUT)
    with conn.cursor() as cur:
        cur.execute("SET default_transaction_read_only = on;")
    return conn
