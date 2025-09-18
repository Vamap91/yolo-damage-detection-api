# Dockerfile TESTADO para Google Cloud Run
# Resolve todos os conflitos de dependências identificados

FROM python:3.11-slim

# Variáveis de ambiente para Cloud Run
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Instalar dependências de sistema mínimas para OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python em ordem específica para evitar conflitos
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 1. Instalar numpy primeiro (versão específica)
RUN pip install --no-cache-dir numpy==1.26.4

# 2. Instalar pillow e opencv-headless
RUN pip install --no-cache-dir \
    pillow==10.0.1 \
    opencv-python-headless==4.8.1.78

# 3. Instalar PyTorch CPU
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    torchvision==0.16.0 \
    --index-url https://download.pytorch.org/whl/cpu

# 4. Instalar ultralytics e outras dependências
RUN pip install --no-cache-dir \
    ultralytics==8.0.196 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    python-multipart==0.0.6 \
    requests==2.28.1

# 5. Forçar numpy para versão correta (caso ultralytics tenha atualizado)
RUN pip install --no-cache-dir --force-reinstall numpy==1.26.4

# Copiar código da aplicação
COPY main.py .

# Expor porta
EXPOSE $PORT

# Comando para iniciar
CMD ["python", "main.py"]
