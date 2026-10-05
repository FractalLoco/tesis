from fastapi import APIRouter

from analizador.estadisticas import obtener_estadisticas
from backend.models.schemas import ConexionBody

router = APIRouter()

@router.post("/estadisticas")
def estadisticas(body: ConexionBody):
    return obtener_estadisticas(body.conexion.model_dump())
