from fastapi import APIRouter

from backend.models.schemas import ConsultaSQL
from backend.services.consola import ejecutar_consulta

router = APIRouter()

@router.post("/consulta")
def consulta(payload: ConsultaSQL):

    return ejecutar_consulta(payload.sql, payload.limit, payload.conexion.model_dump())
