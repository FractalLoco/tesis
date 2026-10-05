from fastapi import APIRouter

from analizador.diagrama import obtener_diagrama
from backend.models.schemas import ConexionBody

router = APIRouter()

@router.post("/diagrama")
def diagrama(body: ConexionBody):
    return obtener_diagrama(body.conexion.model_dump())
