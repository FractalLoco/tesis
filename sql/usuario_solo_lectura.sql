-- Usuario de SOLO LECTURA para el analizador (validado).
-- Reemplaza mi_base y la contraseña por los tuyos, y ejecútalo como superusuario.

CREATE ROLE analizador_ro LOGIN PASSWORD 'CAMBIA_ESTA_CLAVE';

GRANT CONNECT ON DATABASE mi_base TO analizador_ro;
GRANT USAGE ON SCHEMA public TO analizador_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analizador_ro;

-- Para que también pueda leer tablas creadas a futuro:
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analizador_ro;

-- Para el apartado de Estadísticas (pg_stat_database, etc.):
GRANT pg_read_all_stats TO analizador_ro;
