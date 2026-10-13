import logging

from analizador.explain import get_plan
from analizador.orden_join import recomendar_orden_join
from analizador.plan_parser import parse_plan
from analizador.recomendador import recomendar_indices as recomendar
from backend.services.reglas import validar_consulta

log = logging.getLogger("backend.services.analisis")

def analizar_consulta(query: str, config: dict | None = None) -> dict:

    # EXPLAIN ANALYZE ejecuta la consulta de verdad: solo se acepta una de lectura.
    query = validar_consulta(query)
    plan = get_plan(query, analyze=True, config=config)
    analisis = parse_plan(plan)
    return {
        "consulta": query,
        "analisis": analisis,
        "recomendaciones": {
            "orden_join": "pendiente (modelo ML)",
            "indices": "pendiente (HypoPG)",
            "diagnostico": "pendiente (módulo de diagnóstico)",
        },
        "recomendacion_ml": _recomendacion_ml(query, config),
    }

def _recomendacion_ml(query: str, config: dict | None) -> dict:
    # Es un complemento: si falla, el análisis del plan se entrega igual.
    try:
        return recomendar_orden_join(query, config)
    except Exception:
        log.exception("Falló la recomendación de orden de JOIN con el modelo de ML")
        return {"disponible": True, "aplica": False,
                "motivo": "No se pudo evaluar el modelo de ML para esta consulta."}

def recomendar_indices(query: str, config: dict | None = None) -> dict:

    return recomendar(validar_consulta(query), config)
