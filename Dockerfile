# Imagen de la aplicación (FastAPI sirve la API y la página en el puerto 8000)

# Base: Python 3.13 en versión liviana
FROM python:3.13-slim

# LightGBM necesita libgomp para poder cargar los modelos de ml/
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Primero las dependencias: si no cambia requirements.txt, Docker reusa esta capa
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Después el código y los modelos entrenados
COPY analizador ./analizador
COPY backend ./backend
COPY frontend ./frontend
COPY ml ./ml

# Arranque: el mismo comando que se usa en local, escuchando en todas las interfaces
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
