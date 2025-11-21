FROM python:3.11

# Instalar FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copiar archivos del bot
WORKDIR /app
COPY . /app

# Instalar dependencias
RUN pip install -r requirements.txt

# Ejecutar el bot
CMD ["python", "main.py"]
