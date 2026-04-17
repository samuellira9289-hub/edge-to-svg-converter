FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

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

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN mkdir -p static/uploads

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "4", "app:app"]
