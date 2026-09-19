import time

from analizador.connector import get_readonly_connection

def ejecutar_consulta(sql: str, limit: int = 200, config: dict | None = None) -> dict:
    limit = max(1, min(int(limit), 1000))
    inicio = time.perf_counter()
    columnas: list[str] = []
    filas: list[list[str]] = []
    n_total = 0
    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:                                             
                columnas = [c.name for c in cur.description]
                for fila in cur.fetchmany(limit):
                    filas.append([_to_str(v) for v in fila])
            n_total = cur.rowcount
    tiempo_ms = round((time.perf_counter() - inicio) * 1000, 2)
    return {
        "columnas": columnas,
        "filas": filas,
        "n_filas": len(filas),
        "n_total": n_total,
        "tiempo_ms": tiempo_ms,
    }

def _to_str(v) -> str:
    return "" if v is None else str(v)
