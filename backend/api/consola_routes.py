from fastapi import APIRouter

from analizador.consola import ejecutar_consulta
from backend.models.schemas import ConsultaSQL

router = APIRouter()

@router.post("/consulta")
def consulta(payload: ConsultaSQL):

    return ejecutar_consulta(payload.sql, payload.limit, payload.conexion.model_dump())
