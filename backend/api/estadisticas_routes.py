from fastapi import APIRouter

from backend.models.schemas import ConexionBody
from backend.services.catalogo import obtener_estadisticas

router = APIRouter()

@router.post("/estadisticas")
def estadisticas(body: ConexionBody):
    return obtener_estadisticas(body.conexion.model_dump())
