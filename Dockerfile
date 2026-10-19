FROM python:3.12-slim

# Evita archivos .pyc y salida con búfer (logs inmediatos en docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalamos primero las dependencias para aprovechar la caché de capas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código de la aplicación
COPY . .

EXPOSE 5000

# Servidor WSGI de producción (Gunicorn) en lugar del servidor de desarrollo
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
