FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências necessárias, incluindo Java para ZXing
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
    default-jre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório de trabalho
WORKDIR /app

# Copia requirements e instala dependências Python
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante da aplicação
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
