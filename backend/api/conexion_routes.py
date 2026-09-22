from fastapi import APIRouter, HTTPException

from backend.models.schemas import Conexion
from backend.services.orchestrator import probar_conexion

router = APIRouter()

@router.post("/conectar")
def conectar(cfg: Conexion):

    try:
        return probar_conexion(cfg.model_dump())
    except Exception as e:                
        raise HTTPException(status_code=400, detail=f"No se pudo conectar: {e}")
