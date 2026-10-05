from fastapi import APIRouter

from analizador.indices import listar_todos_indices
from backend.models.schemas import ConexionBody

router = APIRouter()

@router.post("/indices")
def indices(body: ConexionBody):
    return {"indices": listar_todos_indices(body.conexion.model_dump())}
