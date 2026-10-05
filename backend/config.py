import os
from pathlib import Path

from dotenv import load_dotenv

# Lee el .env de la raíz del repo (ver .env.example). Las variables que ya
# existan en el entorno tienen prioridad sobre las del archivo.
RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# Credenciales por defecto de la base objetivo (usuario de SOLO LECTURA).
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "optimizacion")
DB_USER = os.getenv("DB_USER", "analizador_ro")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Segundos máximos de espera al abrir la conexión con PostgreSQL. Sin esto, un
# host que no responde deja la petición colgada indefinidamente.
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))

# Orígenes permitidos por CORS, separados por coma.
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if o.strip()
]

# Puerto en que iniciar.py levanta el servidor.
PUERTO = int(os.getenv("PUERTO", "8000"))
