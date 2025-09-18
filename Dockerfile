# SOLUÇÃO DEFINITIVA - Dockerfile para Cloud Run
FROM python:3.11-slim

# Instalar TODAS as dependências necessárias para OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libgtk-3-0 \
    # Video/Image processing
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    # Math libraries
    libatlas-base-dev \
    liblapack-dev \
    libblas-dev \
    # Image formats
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    # Additional OpenCV deps
    libdc1394-22-dev \
    libopencv-dev \
    # System tools
    wget \
    curl \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copiar requirements primeiro
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copiar código
COPY main.py .

# Criar usuário não-root (opcional, mas recomendado)
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Variáveis de ambiente para OpenCV headless
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV OPENCV_IO_ENABLE_OPENEXR=0
ENV OPENCV_IO_ENABLE_JASPER=0
ENV QT_X11_NO_MITSHM=1
ENV OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0
ENV DISPLAY=:99

# Mudar para usuário não-root
USER app

EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Comando para iniciar
CMD ["python", "main.py"]
