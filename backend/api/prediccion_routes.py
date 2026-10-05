from fastapi import APIRouter

from analizador.recomendador import recomendar_indices
from backend.models.schemas import PrediccionIn

router = APIRouter()

@router.post("/prediccion-indices")
def prediccion_indices(payload: PrediccionIn):

    return recomendar_indices(payload.query, payload.conexion.model_dump())
