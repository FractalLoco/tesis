from fastapi import APIRouter

from backend.models.schemas import ConexionBody, PreviewIn
from backend.services.catalogo import listar_tablas, preview_tabla

router = APIRouter()

@router.post("/tablas")
def tablas(body: ConexionBody):

    return {"tablas": listar_tablas(body.conexion.model_dump())}

@router.post("/tabla")
def tabla(payload: PreviewIn):

    return preview_tabla(
        payload.esquema, payload.tabla, payload.limit, payload.conexion.model_dump()
    )
