from fastapi import APIRouter, HTTPException

from backend.models.schemas import AnalizarIn
from backend.services.orchestrator import analizar_consulta

router = APIRouter()

@router.post("/analizar")
def analizar(payload: AnalizarIn):

    try:
        return analizar_consulta(payload.query, payload.conexion.model_dump())
    except Exception as e:                
        raise HTTPException(status_code=400, detail=f"Error al analizar: {e}")
