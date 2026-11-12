from fastapi import APIRouter

from backend.models.schemas import PrediccionIn, Version3In
from backend.services.analisis import recomendar_version2, recomendar_version3

router = APIRouter()

@router.post("/version2")
def version2(payload: PrediccionIn):

    return recomendar_version2(payload.query, payload.conexion.model_dump())

@router.post("/version3")
def version3(payload: Version3In):

    return recomendar_version3(payload.query, payload.conexion.model_dump(), payload.reconstruir)
