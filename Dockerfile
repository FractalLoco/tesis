# Python liviano
FROM python:3.13-slim

# lo pide LightGBM para cargar los modelos
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# primero las librerías, así Docker las reusa si no cambian
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# el código
COPY analizador ./analizador
COPY backend ./backend
COPY frontend ./frontend
COPY ml ./ml

# logs al tiro y la app en el 8000
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
