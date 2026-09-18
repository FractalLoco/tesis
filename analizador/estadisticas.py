import time

from analizador.connector import get_readonly_connection

def obtener_estadisticas(config: dict | None = None) -> dict:
    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:

            inicio = time.perf_counter()
            cur.execute("SELECT 1;")
            cur.fetchone()
            tiempo_respuesta_ms = round((time.perf_counter() - inicio) * 1000, 2)

            cur.execute(
                """SELECT numbackends, blks_read, blks_hit,
                          tup_returned, tup_fetched, xact_commit
                   FROM pg_stat_database WHERE datname = current_database();"""
            )
            fila = cur.fetchone() or (0, 0, 0, 0, 0, 0)

    numbackends, blks_read, blks_hit, tup_ret, tup_fetch, commits = fila
    total = (blks_hit or 0) + (blks_read or 0)
    cache = round(100 * (blks_hit or 0) / total, 1) if total else 0.0
    return {
        "tiempo_respuesta_ms": tiempo_respuesta_ms,
        "conexiones": numbackends or 0,
        "cache_hit_ratio": cache,
        "blks_read": blks_read or 0,
        "blks_hit": blks_hit or 0,
        "tup_returned": tup_ret or 0,
        "tup_fetched": tup_fetch or 0,
        "commits": commits or 0,
    }
