import psycopg

from backend.config import (
    DB_CONNECT_TIMEOUT,
    DB_HOST,
    DB_IDLE_TX_TIMEOUT_MS,
    DB_LOCK_TIMEOUT_MS,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_STATEMENT_TIMEOUT_MS,
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
    # La clave del .env solo se usa con la precarga activa y hacia la misma base:
    # nunca se envía a otro servidor.
    if not overrides.get("password"):
        misma_base = all(str(cfg[k]) == str(defecto[k]) for k in DESTINO)
        if not (PRECARGAR_CONEXION and misma_base):
            cfg["password"] = ""
    return cfg

# Se fijan al abrir la sesión, así un ROLLBACK no los puede deshacer.
OPCIONES = " ".join(f"-c {k}={v}" for k, v in {
    "default_transaction_read_only": "on",
    "statement_timeout": max(0, DB_STATEMENT_TIMEOUT_MS),
    "lock_timeout": max(0, DB_LOCK_TIMEOUT_MS),
    "idle_in_transaction_session_timeout": max(0, DB_IDLE_TX_TIMEOUT_MS),
    "application_name": "optimizador_sql",
}.items())

def get_readonly_connection(config: dict | None = None) -> psycopg.Connection:
    return psycopg.connect(**get_db_config(config), connect_timeout=DB_CONNECT_TIMEOUT,
                           options=OPCIONES)
