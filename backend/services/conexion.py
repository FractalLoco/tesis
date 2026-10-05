from analizador.connector import get_readonly_connection

# Tablas de usuario sobre las que el usuario conectado PODRÍA escribir según sus
# permisos. La conexión es de solo lectura igual, pero si este número no es 0 el
# usuario no es el recomendado (ver sql/usuario_solo_lectura.sql) y se avisa.
TABLAS_CON_ESCRITURA = """
    SELECT count(*)
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind IN ('r', 'p')
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%%'
      AND (has_table_privilege(c.oid, 'INSERT')
           OR has_table_privilege(c.oid, 'UPDATE')
           OR has_table_privilege(c.oid, 'DELETE'));
"""

def probar_conexion(config: dict) -> dict:

    with get_readonly_connection(config) as conn, conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_schema NOT IN ('pg_catalog','information_schema');"
        )
        n_tablas = cur.fetchone()[0]
        cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user;")
        fila = cur.fetchone()
        es_superusuario = bool(fila and fila[0])
        cur.execute(TABLAS_CON_ESCRITURA)
        tablas_escribibles = cur.fetchone()[0]

    advertencias = []
    if es_superusuario:
        advertencias.append(
            "Te conectaste con un superusuario. El análisis igual es de solo lectura, "
            "pero se recomienda un usuario dedicado sin permisos de escritura."
        )
    elif tablas_escribibles:
        advertencias.append(
            f"El usuario tiene permisos de escritura sobre {tablas_escribibles} "
            f"{'tabla' if tablas_escribibles == 1 else 'tablas'}. El análisis igual es de "
            "solo lectura, pero se recomienda un usuario dedicado (sql/usuario_solo_lectura.sql)."
        )

    return {
        "ok": True,
        "version": version,
        "n_tablas": n_tablas,
        "usuario_solo_lectura": not es_superusuario and not tablas_escribibles,
        "advertencias": advertencias,
    }
