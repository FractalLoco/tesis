from statistics import median

from analizador.connector import get_readonly_connection

RONDAS_WARMUP = 3
REPETICIONES = 5

def get_plan(query: str, analyze: bool = False, config: dict | None = None):
    prefix = (
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
        if analyze
        else "EXPLAIN (FORMAT JSON) "
    )
    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(prefix + query)
            return cur.fetchone()[0]

def medir_tiempo_ejecucion(query: str) -> float:
    with get_readonly_connection() as conn:
        with conn.cursor() as cur:
            for _ in range(RONDAS_WARMUP):
                cur.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query)
                cur.fetchone()
            tiempos = []
            for _ in range(REPETICIONES):
                cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query)
                plan = cur.fetchone()[0]
                tiempos.append(plan[0]["Plan"]["Actual Total Time"])
    return median(tiempos)
