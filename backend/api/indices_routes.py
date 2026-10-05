from fastapi import APIRouter

from backend.models.schemas import ConexionBody
from backend.services.catalogo import listar_todos_indices

router = APIRouter()

@router.post("/indices")
def indices(body: ConexionBody):
    return {"indices": listar_todos_indices(body.conexion.model_dump())}
