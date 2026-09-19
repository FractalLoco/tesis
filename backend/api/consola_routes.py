from fastapi import APIRouter, HTTPException

from backend.models.schemas import ConsultaSQL
from analizador.consola import ejecutar_consulta

router = APIRouter()

@router.post("/consulta")
def consulta(payload: ConsultaSQL):

    try:
        return ejecutar_consulta(payload.sql, payload.limit, payload.conexion.model_dump())
    except Exception as e:                
        raise HTTPException(status_code=400, detail=f"Error en la consulta: {e}")
