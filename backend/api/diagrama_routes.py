from fastapi import APIRouter, HTTPException

from backend.models.schemas import ConexionBody
from analizador.diagrama import obtener_diagrama

router = APIRouter()

@router.post("/diagrama")
def diagrama(body: ConexionBody):
    try:
        return obtener_diagrama(body.conexion.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo obtener el diagrama: {e}")
