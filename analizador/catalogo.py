from psycopg import sql

from analizador.connector import get_readonly_connection

def listar_tablas(config: dict | None = None) -> list[dict]:
    q = """
        SELECT n.nspname AS esquema,
               c.relname AS tabla,
               c.reltuples::bigint AS filas_est,
               (SELECT count(*) FROM pg_index i WHERE i.indrelid = c.oid) AS n_indices
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY n.nspname, c.relname;
    """
    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            filas = cur.fetchall()
    return [{"esquema": e, "tabla": t, "filas_est": int(f), "n_indices": int(ix)}
            for (e, t, f, ix) in filas]

def listar_indices(esquema: str, tabla: str, config: dict | None = None) -> list[dict]:
    q = """
        SELECT i.relname AS indice,
               idx.indisprimary AS es_primary,
               idx.indisunique  AS es_unique,
               pg_get_indexdef(idx.indexrelid) AS definicion
        FROM pg_index idx
        JOIN pg_class i  ON i.oid  = idx.indexrelid
        JOIN pg_class t  ON t.oid  = idx.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = %s AND t.relname = %s
        ORDER BY idx.indisprimary DESC, i.relname;
    """
    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(q, (esquema, tabla))
            filas = cur.fetchall()
    return [
        {"indice": n, "es_primary": bool(p), "es_unique": bool(u), "definicion": d}
        for (n, p, u, d) in filas
    ]

def preview_tabla(esquema: str, tabla: str, limit: int = 50,
                  config: dict | None = None) -> dict:
    limit = max(1, min(int(limit), 200))
    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT column_name, data_type
                   FROM information_schema.columns
                   WHERE table_schema = %s AND table_name = %s
                   ORDER BY ordinal_position;""",
                (esquema, tabla),
            )
            columnas = [{"nombre": n, "tipo": t} for (n, t) in cur.fetchall()]

            consulta = sql.SQL("SELECT * FROM {}.{} LIMIT {}").format(
                sql.Identifier(esquema), sql.Identifier(tabla), sql.Literal(limit)
            )
            cur.execute(consulta)
            filas = [[_to_str(v) for v in fila] for fila in cur.fetchall()]

    indices = listar_indices(esquema, tabla, config)
    return {"columnas": columnas, "filas": filas, "n_filas": len(filas), "indices": indices}

def _to_str(v) -> str:
    return "" if v is None else str(v)
