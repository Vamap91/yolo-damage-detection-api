FROM python:3.11-slim

# Instalar dependências mínimas do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro (para cache do Docker)
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

# Comando para iniciar - SEM timeout customizado
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
