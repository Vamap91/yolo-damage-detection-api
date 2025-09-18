FROM python:3.11-slim

# Nova Atualização VINICIUS PASCHOA
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copiar código da aplicação
COPY main.py .

# Criar diretório para modelos
RUN mkdir -p /app/models

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Expor porta
EXPOSE $PORT

# Comando para iniciar a aplicação
CMD uvicorn main:app --host $HOST --port $PORT --timeout-keep-alive 300
