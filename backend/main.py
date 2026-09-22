from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.conexion_routes import router as conexion_router
from backend.api.catalogo_routes import router as catalogo_router
from backend.api.consola_routes import router as consola_router
from backend.api.analisis_routes import router as analisis_router
from backend.api.estadisticas_routes import router as estadisticas_router
from backend.api.indices_routes import router as indices_router
from backend.api.diagrama_routes import router as diagrama_router
from backend.api.prediccion_routes import router as prediccion_router

app = FastAPI(title="Optimizador SQL con ML — Backend de análisis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conexion_router, tags=["conexion"])
app.include_router(catalogo_router, tags=["catalogo"])
app.include_router(consola_router, tags=["consola"])
app.include_router(analisis_router, tags=["analisis"])
app.include_router(estadisticas_router, tags=["estadisticas"])
app.include_router(indices_router, tags=["indices"])
app.include_router(diagrama_router, tags=["diagrama"])
app.include_router(prediccion_router, tags=["prediccion"])

@app.get("/health")
def health():

    return {"status": "ok"}

# Sirve el frontend (HTML/CSS/JS estático) desde el mismo proceso y puerto que
# la API, para poder desplegar todo detrás de un único puerto expuesto.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
