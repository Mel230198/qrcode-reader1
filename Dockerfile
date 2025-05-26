# Usar imagem base oficial do Python, slim para menor tamanho
FROM python:3.10-slim

# Variáveis de ambiente para não gerar prompts interativos no apt
ENV DEBIAN_FRONTEND=noninteractive

# Atualiza e instala dependências necessárias para o app e tesseract
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia requirements.txt e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código para o container
COPY . .

# Expõe a porta onde o Flask roda
EXPOSE 5000

# Comando padrão para rodar a aplicação
CMD ["python", "app.py"]

