from fastapi import APIRouter

from backend.models.schemas import Conexion
from backend.services.conexion import conexion_por_defecto, probar_conexion

router = APIRouter()

@router.post("/conectar")
def conectar(cfg: Conexion):

    return probar_conexion(cfg.model_dump())

@router.get("/conexion-por-defecto")
def por_defecto():

    return conexion_por_defecto()
