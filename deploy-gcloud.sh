#!/bin/bash

# Script de Deploy para Google Cloud Run - YOLO API
# Uso: ./deploy-gcloud.sh [PROJECT_ID] [REGION]

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Verificar argumentos
PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null)}
REGION=${2:-"us-central1"}

if [ -z "$PROJECT_ID" ]; then
    error "PROJECT_ID não especificado. Uso: $0 <PROJECT_ID> [REGION]"
fi

log "🚀 Iniciando deploy da YOLO API para Google Cloud Run"
log "Project ID: $PROJECT_ID"
log "Region: $REGION"

# Verificar se gcloud está instalado e autenticado
if ! command -v gcloud &> /dev/null; then
    error "gcloud CLI não está instalado. Instale em: https://cloud.google.com/sdk/docs/install"
fi

# Verificar autenticação
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    error "Não autenticado no gcloud. Execute: gcloud auth login"
fi

# Configurar projeto
log "⚙️ Configurando projeto..."
gcloud config set project $PROJECT_ID

# Habilitar APIs necessárias
log "🔧 Habilitando APIs necessárias..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Fazer build e deploy usando Cloud Build
log "🏗️ Iniciando build e deploy..."
gcloud builds submit --config cloudbuild.yaml --substitutions=_REGION=$REGION

# Obter URL do serviço
log "🔍 Obtendo URL do serviço..."
SERVICE_URL=$(gcloud run services describe yolo-damage-detection --region=$REGION --format="value(status.url)")

# Testar o serviço
log "🧪 Testando o serviço..."
if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
    log "✅ Serviço está funcionando!"
else
    warn "⚠️ Serviço pode não estar respondendo ainda. Aguarde alguns minutos."
fi

# Mostrar informações finais
log "🎉 Deploy concluído com sucesso!"
echo
echo -e "${BLUE}📋 Informações do Deploy:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "🌐 URL da API: $SERVICE_URL"
echo -e "📚 Documentação: $SERVICE_URL/docs"
echo -e "❤️ Health Check: $SERVICE_URL/health"
echo -e "🔧 Project ID: $PROJECT_ID"
echo -e "🌍 Region: $REGION"
echo
echo -e "${GREEN}✅ Comandos úteis:${NC}"
echo "• Ver logs: gcloud run services logs read yolo-damage-detection --region=$REGION"
echo "• Atualizar: gcloud builds submit --config cloudbuild.yaml"
echo "• Deletar: gcloud run services delete yolo-damage-detection --region=$REGION"
echo "• Status: gcloud run services describe yolo-damage-detection --region=$REGION"
