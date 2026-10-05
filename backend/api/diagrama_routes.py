from fastapi import APIRouter

from backend.models.schemas import ConexionBody
from backend.services.catalogo import obtener_diagrama

router = APIRouter()

@router.post("/diagrama")
def diagrama(body: ConexionBody):
    return obtener_diagrama(body.conexion.model_dump())
