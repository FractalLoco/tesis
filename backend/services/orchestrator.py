from analizador.connector import get_readonly_connection
from analizador.explain import get_plan
from analizador.plan_parser import parse_plan

def probar_conexion(config: dict) -> dict:

    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema NOT IN ('pg_catalog','information_schema');"
            )
            n_tablas = cur.fetchone()[0]
    return {"ok": True, "version": version, "n_tablas": n_tablas}

def analizar_consulta(query: str, config: dict | None = None) -> dict:

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
