FROM python:3.11.12-slim

WORKDIR /app

# Dependências do sistema necessárias para libs Python (psycopg2, etc.) + Tesseract OCR
ARG CACHE_BUST=2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-por \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python antes de copiar o código
# (aproveita cache do Docker se requirements.txt não mudou)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Porta padrão do Railway via variável de ambiente
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
