# ==========================================
# Etapa 1: Build (Construcción)
# ==========================================
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 as builder

# Configuraciones de Python para evitar archivos .pyc y no bufferizar el output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias para compilar librerías (ej. WeasyPrint, psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear y activar un entorno virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .

# Instalar dependencias (usando el entorno virtual)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# Etapa 2: Producción (Imagen final más ligera)
# ==========================================
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"
ENV TZ="America/Caracas"

# Instalar SOLO las librerías en tiempo de ejecución (sin compiladores)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg62-turbo \
    libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*

# Crear un usuario no-root por seguridad
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copiar el entorno virtual desde el builder
COPY --from=builder /opt/venv /opt/venv

# Copiar el código fuente del proyecto
COPY . /app/

# Crear carpeta de subidas y dar permisos al usuario no-root
RUN mkdir -p /app/static/uploads && chown -R appuser:appgroup /app

# Cambiar al usuario seguro
USER appuser

# Exponer el puerto
EXPOSE 5000

# Usar Gunicorn en producción en vez del servidor de desarrollo de Flask
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--threads", "2", "--timeout", "120", "app:app"]
