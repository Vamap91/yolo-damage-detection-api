FROM python:3.11-slim

# CORREÇÃO: Nomes dos pacotes atualizados para Debian Trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

COPY main.py .

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE $PORT

CMD ["python", "main.py"]
