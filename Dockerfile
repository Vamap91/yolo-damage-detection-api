FROM python:3.11-slim

# Instalar dependências do sistema (CORRIGIDO para OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libatlas-base-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libdc1394-22-dev \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copiar e instalar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copiar código
COPY main.py .

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# IMPORTANTE: Desabilitar display para OpenCV headless
ENV DISPLAY=:99
ENV QT_X11_NO_MITSHM=1

EXPOSE $PORT

# Comando simples que funciona
CMD ["python", "main.py"]
