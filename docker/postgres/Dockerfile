# Postgres oficial
FROM postgres:17

# HypoPG para los índices hipotéticos
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17-hypopg \
    && rm -rf /var/lib/apt/lists/*

# se ejecuta la primera vez y carga la base de prueba
COPY docker/postgres/iniciar_base.sh /docker-entrypoint-initdb.d/
COPY sql/base_de_prueba.sql /sql/base_de_prueba.sql
