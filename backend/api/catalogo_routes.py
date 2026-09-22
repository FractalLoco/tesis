from fastapi import APIRouter, HTTPException

from backend.models.schemas import ConexionBody, PreviewIn
from analizador.catalogo import listar_tablas, preview_tabla

router = APIRouter()

@router.post("/tablas")
def tablas(body: ConexionBody):

    try:
        return {"tablas": listar_tablas(body.conexion.model_dump())}
    except Exception as e:                
        raise HTTPException(status_code=400, detail=f"No se pudieron listar las tablas: {e}")

@router.post("/tabla")
def tabla(payload: PreviewIn):

    try:
        return preview_tabla(
            payload.esquema, payload.tabla, payload.limit, payload.conexion.model_dump()
        )
    except Exception as e:                
        raise HTTPException(status_code=400, detail=f"No se pudo obtener la tabla: {e}")
