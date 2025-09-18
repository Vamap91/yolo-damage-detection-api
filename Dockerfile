FROM python:3.11-slim

# ÚNICA MUDANÇA: Adicionar dependências OpenCV que estavam faltando
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Resto igual ao original
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

COPY main.py .

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE $PORT

CMD ["python", "main.py"]
