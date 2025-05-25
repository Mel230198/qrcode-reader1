# Usa imagem oficial do Python como base
FROM python:3.10-slim

# Instala dependências do sistema para compilação e bibliotecas necessárias
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Cria diretório da aplicação
WORKDIR /app

# Copia os arquivos da aplicação para o container
COPY . .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta usada pela aplicação Flask
EXPOSE 5000

# Comando para iniciar o Flask
CMD ["python", "app.py"]


