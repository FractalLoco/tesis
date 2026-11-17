#!/bin/bash
# Se ejecuta una sola vez, cuando la base se crea por primera vez (volumen vacío)
set -e

# Base de prueba: la misma de sql/base_de_prueba.sql (7 tablas tipo TPC-H)
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -c "CREATE DATABASE optimizacion"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d optimizacion -f /sql/base_de_prueba.sql

# Usuario de solo lectura que usa la app (igual que sql/usuario_solo_lectura.sql)
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d optimizacion -v clave="$CLAVE_SOLO_LECTURA" <<'SQL'
CREATE ROLE analizador_ro LOGIN PASSWORD :'clave';
GRANT CONNECT ON DATABASE optimizacion TO analizador_ro;
GRANT USAGE ON SCHEMA public TO analizador_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analizador_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analizador_ro;
GRANT pg_read_all_stats TO analizador_ro;
SQL
