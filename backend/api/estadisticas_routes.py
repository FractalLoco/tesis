from fastapi import APIRouter, HTTPException

from backend.models.schemas import ConexionBody
from analizador.estadisticas import obtener_estadisticas

router = APIRouter()

@router.post("/estadisticas")
def estadisticas(body: ConexionBody):
    try:
        return obtener_estadisticas(body.conexion.model_dump())
    except Exception as e:                
        raise HTTPException(status_code=400, detail=f"No se pudieron obtener estadísticas: {e}")
