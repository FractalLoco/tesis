import psycopg

from backend.config import (
    DB_CONNECT_TIMEOUT,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
)

def get_db_config(overrides: dict | None = None) -> dict:
    cfg = {
        "host": DB_HOST,
        "port": DB_PORT,
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
    }
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v not in (None, "")})
    return cfg

def get_readonly_connection(config: dict | None = None) -> psycopg.Connection:
    conn = psycopg.connect(**get_db_config(config), connect_timeout=DB_CONNECT_TIMEOUT)
    with conn.cursor() as cur:
        cur.execute("SET default_transaction_read_only = on;")
    return conn
