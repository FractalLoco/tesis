#!/bin/bash
# corre una sola vez, con el volumen vacío
set -e

# la base de prueba
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -c "CREATE DATABASE optimizacion"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d optimizacion -f /sql/base_de_prueba.sql

# usuario de solo lectura para la app
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d optimizacion -v clave="$CLAVE_SOLO_LECTURA" <<'SQL'
CREATE ROLE analizador_ro LOGIN PASSWORD :'clave';
GRANT CONNECT ON DATABASE optimizacion TO analizador_ro;
GRANT USAGE ON SCHEMA public TO analizador_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analizador_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analizador_ro;
GRANT pg_read_all_stats TO analizador_ro;
SQL
