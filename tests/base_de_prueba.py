# Datos compartidos por las pruebas de integración y E2E: la base de prueba
# configurada en el .env (usuario de solo lectura).
import psycopg

from backend import config

CONEXION = {"host": config.DB_HOST, "port": config.DB_PORT, "dbname": config.DB_NAME,
            "user": config.DB_USER, "password": config.DB_PASSWORD}

def hay_base():
    """True si se puede conectar a la base de prueba. Si no (por ejemplo en
    GitHub Actions, que no tiene PostgreSQL), esas pruebas se omiten."""
    try:
        psycopg.connect(**CONEXION, connect_timeout=3).close()
        return True
    except psycopg.Error:
        return False
