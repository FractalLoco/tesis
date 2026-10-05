from fastapi import APIRouter

from backend.models.schemas import AnalizarIn
from backend.services.analisis import analizar_consulta

router = APIRouter()

@router.post("/analizar")
def analizar(payload: AnalizarIn):

    return analizar_consulta(payload.query, payload.conexion.model_dump())
