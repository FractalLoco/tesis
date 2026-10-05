from analizador.explain import get_plan
from analizador.plan_parser import parse_plan
from analizador.recomendador import recomendar_indices as recomendar
from backend.services.reglas import validar_consulta

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
    }

def recomendar_indices(query: str, config: dict | None = None) -> dict:

    return recomendar(validar_consulta(query), config)
