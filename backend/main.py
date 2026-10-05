from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import api_router
from backend.config import CORS_ORIGINS
from backend.errores import registrar_manejadores

app = FastAPI(title="Optimizador SQL con ML — Backend de análisis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(api_router)
registrar_manejadores(app)

@app.get("/health")
def health():

    return {"status": "ok"}

# Sirve el frontend (HTML/CSS/JS estático) desde el mismo proceso y puerto que
# la API, para poder desplegar todo detrás de un único puerto expuesto.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
