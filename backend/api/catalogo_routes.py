from fastapi import APIRouter

from analizador.catalogo import listar_tablas, preview_tabla
from backend.models.schemas import ConexionBody, PreviewIn

router = APIRouter()

@router.post("/tablas")
def tablas(body: ConexionBody):

    return {"tablas": listar_tablas(body.conexion.model_dump())}

@router.post("/tabla")
def tabla(payload: PreviewIn):

    return preview_tabla(
        payload.esquema, payload.tabla, payload.limit, payload.conexion.model_dump()
    )
