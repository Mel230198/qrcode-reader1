# Imagem base com Python 3.10
FROM python:3.10-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1-mesa-glx \
    libzbar0 \
    poppler-utils \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia o conteúdo da aplicação
COPY . .

# Instala dependências Python
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expõe a porta usada pelo Gunicorn
EXPOSE 10000

# Comando padrão para iniciar o servidor
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]

