
# Use uma imagem base Python otimizada para aplicações web
FROM python:3.9-slim-buster

# Definir variáveis de ambiente para evitar prompts interativos durante a instalação
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar dependências do sistema necessárias para OpenCV e outras bibliotecas
# Inclui build-essential para compilação, libgl1-mesa-glx para renderização OpenGL (necessário para algumas operações do OpenCV)
# libgtk2.0-dev e libgtk-3-dev para interfaces gráficas (mesmo que não usadas diretamente, são dependências comuns do OpenCV)
# libjpeg-dev, libpng-dev, libtiff-dev, libavcodec-dev, libavformat-dev, libswscale-dev para suporte a formatos de imagem/vídeo
# freetype* e fontconfig para renderização de fontes (útil para Pillow)
# libatlas-base-dev e liblapack-dev para otimização de NumPy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    unzip \
    yasm \
    pkg-config \
    libswscale-dev \
    libtbb2 \
    libtbb-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libpostproc-dev \
    libswscale-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libxrender1 \
    libgl1-mesa-glx \
    libgtk2.0-dev \
    libgtk-3-dev \
    libatlas-base-dev \
    liblapack-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copiar o arquivo requirements.txt para o diretório de trabalho
COPY requirements.txt .

# Instalar as dependências Python
# Usar --no-cache-dir para reduzir o tamanho da imagem Docker
# Instalar gunicorn aqui também, pois será o servidor de produção
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copiar o restante do código da aplicação para o diretório de trabalho
COPY . .

# Criar o diretório 'static/uploads' se ele não existir, conforme app.py
RUN mkdir -p static/uploads

# Expor a porta que o Gunicorn irá escutar
EXPOSE 8000

# Comando para iniciar a aplicação com Gunicorn
# Usar 4 workers para melhor desempenho em ambientes de produção
# Vincular ao 0.0.0.0 para que seja acessível de fora do contêiner
# O módulo da aplicação é 'app:app' (nome do arquivo:instância Flask)
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "4", "app:app"]
