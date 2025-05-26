FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Atualiza e instala dependências essenciais, evita pacotes recomendados desnecessários
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libzbar0 \
    tesseract-ocr \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia somente requirements.txt primeiro para usar cache do Docker
COPY requirements.txt .

# Usa --no-cache-dir para pip evitar cache local e deixar imagem menor
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código para o container (após instalar libs)
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]

