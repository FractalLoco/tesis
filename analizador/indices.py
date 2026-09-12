from analizador.connector import get_readonly_connection

CONSULTA = """
    SELECT n.nspname                                   AS esquema,
           t.relname                                   AS tabla,
           i.relname                                   AS indice,
           am.amname                                   AS metodo,
           idx.indisprimary                            AS es_primary,
           idx.indisunique                             AS es_unique,
           idx.indisvalid                              AS valido,
           idx.indpred IS NOT NULL                     AS parcial,
           idx.indexprs IS NOT NULL                    AS expresion,
           pg_get_expr(idx.indpred, idx.indrelid)      AS predicado,
           ARRAY(SELECT pg_get_indexdef(idx.indexrelid, k, true)
                 FROM generate_series(1, idx.indnkeyatts::int) k)                        AS columnas,
           ARRAY(SELECT pg_get_indexdef(idx.indexrelid, k, true)
                 FROM generate_series(idx.indnkeyatts::int + 1, idx.indnatts::int) k)    AS incluye,
           ARRAY(SELECT a.attname
                 FROM pg_attribute a
                 WHERE a.attrelid = idx.indrelid AND a.attnum > 0 AND NOT a.attisdropped
                   AND (a.attnum = ANY (idx.indkey::int2[])
                        OR a.attnum IN (SELECT d.refobjsubid FROM pg_depend d
                                        WHERE d.classid = 'pg_class'::regclass
                                          AND d.objid = idx.indexrelid
                                          AND d.refobjid = idx.indrelid
                                          AND d.refobjsubid > 0))
                 ORDER BY a.attnum)                    AS cols_tabla,
           pg_get_indexdef(idx.indexrelid)             AS definicion,
           pg_relation_size(idx.indexrelid)            AS bytes,
           COALESCE(s.idx_scan, 0)                     AS usos,
           COALESCE(s.idx_tup_read, 0)                 AS lecturas
    FROM pg_index idx
    JOIN pg_class i      ON i.oid = idx.indexrelid
    JOIN pg_class t      ON t.oid = idx.indrelid
    JOIN pg_namespace n  ON n.oid = t.relnamespace
    JOIN pg_am am        ON am.oid = i.relam
    LEFT JOIN pg_stat_all_indexes s ON s.indexrelid = idx.indexrelid
    WHERE t.relkind IN ('r', 'p', 'm')
      AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
    ORDER BY n.nspname, t.relname, idx.indisprimary DESC, i.relname;
"""

CAMPOS = ["esquema", "tabla", "indice", "metodo", "es_primary", "es_unique", "valido",
          "parcial", "expresion", "predicado", "columnas", "incluye", "cols_tabla", "definicion",
          "bytes", "usos", "lecturas"]

def listar_todos_indices(config: dict | None = None) -> list[dict]:
    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(CONSULTA)
            filas = cur.fetchall()
    return [dict(zip(CAMPOS, f)) for f in filas]
