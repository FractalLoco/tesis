from fastapi import APIRouter, HTTPException

from backend.models.schemas import PrediccionIn
from analizador.recomendador import recomendar_indices

router = APIRouter()

@router.post("/prediccion-indices")
def prediccion_indices(payload: PrediccionIn):

    try:
        return recomendar_indices(payload.query, payload.conexion.model_dump())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo generar la recomendación: {e}")
