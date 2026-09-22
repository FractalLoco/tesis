from analizador.connector import get_readonly_connection

SISTEMA = "('pg_catalog', 'information_schema', 'pg_toast')"

COLUMNAS = f"""
    SELECT n.nspname, c.relname, c.reltuples::bigint,
           a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull
    FROM pg_attribute a
    JOIN pg_class c     ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind IN ('r', 'p')
      AND a.attnum > 0 AND NOT a.attisdropped
      AND n.nspname NOT IN {SISTEMA}
    ORDER BY n.nspname, c.relname, a.attnum;
"""

RESTRICCIONES = f"""
    SELECT con.conname, con.contype,
           n.nspname, c.relname,
           ARRAY(SELECT a.attname
                 FROM unnest(con.conkey) WITH ORDINALITY k(num, ord)
                 JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.num
                 ORDER BY k.ord),
           fn.nspname, fc.relname,
           ARRAY(SELECT a.attname
                 FROM unnest(con.confkey) WITH ORDINALITY k(num, ord)
                 JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = k.num
                 ORDER BY k.ord)
    FROM pg_constraint con
    JOIN pg_class c      ON c.oid = con.conrelid
    JOIN pg_namespace n  ON n.oid = c.relnamespace
    LEFT JOIN pg_class fc     ON fc.oid = con.confrelid
    LEFT JOIN pg_namespace fn ON fn.oid = fc.relnamespace
    WHERE con.contype IN ('p', 'f')
      AND n.nspname NOT IN {SISTEMA}
    ORDER BY con.conname;
"""

def obtener_diagrama(config: dict | None = None) -> dict:
    with get_readonly_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute(COLUMNAS)
            columnas = cur.fetchall()
            cur.execute(RESTRICCIONES)
            restricciones = cur.fetchall()

    tablas: dict[tuple, dict] = {}
    for esquema, tabla, filas, nombre, tipo, not_null in columnas:
        t = tablas.setdefault((esquema, tabla), {
            "esquema": esquema, "tabla": tabla, "filas_est": int(filas), "columnas": []})
        t["columnas"].append({"nombre": nombre, "tipo": tipo, "not_null": bool(not_null),
                              "pk": False, "fk": False})

    relaciones = []
    for nombre, tipo, esquema, tabla, cols, f_esquema, f_tabla, f_cols in restricciones:
        origen = tablas.get((esquema, tabla))
        if origen is None:
            continue
        marca = "pk" if tipo == "p" else "fk"
        for c in origen["columnas"]:
            if c["nombre"] in cols:
                c[marca] = True
        if tipo == "f" and (f_esquema, f_tabla) in tablas:
            relaciones.append({
                "nombre": nombre,
                "desde": {"esquema": esquema, "tabla": tabla, "columnas": cols},
                "hacia": {"esquema": f_esquema, "tabla": f_tabla, "columnas": f_cols},
            })

    return {"tablas": list(tablas.values()), "relaciones": relaciones}
