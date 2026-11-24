import os
from pathlib import Path

from dotenv import load_dotenv

# Lee el .env de la raíz; las variables que ya existan en el entorno mandan.
RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

def _si(nombre: str, defecto: str) -> bool:
    return os.getenv(nombre, defecto).strip().lower() in ("1", "true", "si", "sí")

# Base por defecto (usuario de SOLO LECTURA).
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "optimizacion")
DB_USER = os.getenv("DB_USER", "analizador_ro")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# La pantalla de conexión llega llena con la base de arriba. Solo para uso local.
PRECARGAR_CONEXION = _si("PRECARGAR_CONEXION", "false")

# Límites de tiempo: al conectar (s) y por consulta, bloqueo y transacción inactiva (ms).
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))
DB_LOCK_TIMEOUT_MS = int(os.getenv("DB_LOCK_TIMEOUT_MS", "5000"))
DB_IDLE_TX_TIMEOUT_MS = int(os.getenv("DB_IDLE_TX_TIMEOUT_MS", "60000"))

# false = los errores no muestran el detalle de PostgreSQL (hosts, versiones).
MOSTRAR_DETALLE_TECNICO = _si("MOSTRAR_DETALLE_TECNICO", "true")

# Dónde escucha iniciar.py. 0.0.0.0 abre la app a la red (la API no tiene login).
BIND_HOST = os.getenv("BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
PUERTO = int(os.getenv("PUERTO", "8000"))

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if o.strip()
]

# PostgreSQL propio con HypoPG para la base gemela de la V3. Vacío = V3 no disponible.
GEMELA_DSN = os.getenv("GEMELA_DSN", "")
