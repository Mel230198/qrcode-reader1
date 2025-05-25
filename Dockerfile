# Usa imagem oficial do Python como base
FROM python:3.10-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \          # Para pdf2image
    libgl1 \                 # Para OpenCV
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libzbar0 \               # NECESSÁRIO para pyzbar (leitura de QR code)
    tesseract-ocr \          # (opcional) OCR, pode remover se não usar
    && rm -rf /var/lib/apt/lists/*

# Define diretório da aplicação
WORKDIR /app

# Copia todos os arquivos da aplicação para o container
COPY . .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta usada pela aplicação Flask
EXPOSE 5000

# Comando para iniciar o Flask
CMD ["python", "app.py"]




