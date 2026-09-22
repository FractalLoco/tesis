import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def get_db_config(overrides: dict | None = None) -> dict:
    cfg = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "optimizacion"),
        "user": os.getenv("DB_USER", "analizador_ro"),
        "password": os.getenv("DB_PASSWORD", ""),
    }
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v not in (None, "")})
    return cfg

def get_readonly_connection(config: dict | None = None) -> psycopg.Connection:
    conn = psycopg.connect(**get_db_config(config))
    with conn.cursor() as cur:
        cur.execute("SET default_transaction_read_only = on;")
    return conn
