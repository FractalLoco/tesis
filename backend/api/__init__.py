from fastapi import APIRouter

from backend.api.analisis_routes import router as analisis_router
from backend.api.catalogo_routes import router as catalogo_router
from backend.api.conexion_routes import router as conexion_router
from backend.api.consola_routes import router as consola_router
from backend.api.diagrama_routes import router as diagrama_router
from backend.api.estadisticas_routes import router as estadisticas_router
from backend.api.indices_routes import router as indices_router
from backend.api.prediccion_routes import router as prediccion_router

# Agrupa todas las rutas de la API bajo /api, para que no se confundan con las
# rutas de pantalla del frontend (/tablas, /diagrama, etc.).
api_router = APIRouter(prefix="/api")

api_router.include_router(conexion_router, tags=["conexion"])
api_router.include_router(catalogo_router, tags=["catalogo"])
api_router.include_router(consola_router, tags=["consola"])
api_router.include_router(analisis_router, tags=["analisis"])
api_router.include_router(estadisticas_router, tags=["estadisticas"])
api_router.include_router(indices_router, tags=["indices"])
api_router.include_router(diagrama_router, tags=["diagrama"])
api_router.include_router(prediccion_router, tags=["prediccion"])
