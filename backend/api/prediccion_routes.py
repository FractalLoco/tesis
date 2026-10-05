from fastapi import APIRouter

from backend.models.schemas import PrediccionIn
from backend.services.analisis import recomendar_indices

router = APIRouter()

@router.post("/prediccion-indices")
def prediccion_indices(payload: PrediccionIn):

    return recomendar_indices(payload.query, payload.conexion.model_dump())
