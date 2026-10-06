from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

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

class FrontendSPA(StaticFiles):
    """Sirve el frontend. Las rutas de pantalla (/tablas, /diagrama, ...) no son
    archivos: devuelven index.html y el router del navegador decide qué mostrar.
    Así se puede refrescar o abrir directamente cualquier ruta sin un 404."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # Se usa la ruta de la URL: "path" viene con el separador del sistema operativo.
            url = scope["path"]
            # Un archivo que no existe (tiene extensión) o una ruta de la API sí son 404.
            if exc.status_code != 404 or url.startswith("/api/") or "." in url.rsplit("/", 1)[-1]:
                raise
            return await super().get_response("index.html", scope)

# Sirve el frontend (HTML/CSS/JS estático) desde el mismo proceso y puerto que
# la API, para poder desplegar todo detrás de un único puerto expuesto.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", FrontendSPA(directory=FRONTEND_DIR, html=True), name="frontend")
