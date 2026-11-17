# Imagen de la base de datos: PostgreSQL 17 con HypoPG

# Base: la imagen oficial de PostgreSQL 17
FROM postgres:17

# HypoPG: índices hipotéticos para la base gemela de la V3
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17-hypopg \
    && rm -rf /var/lib/apt/lists/*

# Lo que corre la primera vez: crea la base de prueba y el usuario de solo lectura
COPY docker/postgres/iniciar_base.sh /docker-entrypoint-initdb.d/
COPY sql/base_de_prueba.sql /sql/base_de_prueba.sql
