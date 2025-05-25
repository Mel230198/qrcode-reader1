FROM python:3.10-slim

# Instala dependências do sistema
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
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia requirements primeiro (melhor para cache do Docker)
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante da aplicação
COPY . .

# Expõe a porta do Flask
EXPOSE 5000

# Comando padrão
CMD ["python", "app.py"]



