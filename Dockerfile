FROM python:3.10-slim

# Instala dependências do sistema, incluindo o Tesseract com suporte ao português
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libzbar0 \
    tesseract-ocr \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia e instala as dependências Python
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código para o container
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
