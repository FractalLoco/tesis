from fastapi import APIRouter, HTTPException

from backend.models.schemas import ConexionBody
from analizador.indices import listar_todos_indices

router = APIRouter()

@router.post("/indices")
def indices(body: ConexionBody):
    try:
        return {"indices": listar_todos_indices(body.conexion.model_dump())}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudieron listar los índices: {e}")
