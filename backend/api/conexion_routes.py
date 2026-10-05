from fastapi import APIRouter

from backend.models.schemas import Conexion
from backend.services.orchestrator import probar_conexion

router = APIRouter()

@router.post("/conectar")
def conectar(cfg: Conexion):

    return probar_conexion(cfg.model_dump())
