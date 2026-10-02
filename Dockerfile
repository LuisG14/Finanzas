FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias primero (aprovecha cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY app.py .
COPY modules/ ./modules/

# La carpeta data/ se monta como volumen externo (ver docker-compose.yml)
# para que los CSVs no se pierdan al reconstruir la imagen
RUN mkdir -p /app/data

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
