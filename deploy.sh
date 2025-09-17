#!/bin/bash

# Script de Deploy para Produção - YOLO API
# Uso: ./deploy.sh [dominio] [email]

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
if [ $# -lt 2 ]; then
    error "Uso: $0 <dominio> <email>\nExemplo: $0 api.seudominio.com admin@seudominio.com"
fi

DOMAIN=$1
EMAIL=$2

log "🚀 Iniciando deploy da YOLO API para produção"
log "Domínio: $DOMAIN"
log "Email: $EMAIL"

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    error "Este script deve ser executado como root (sudo)"
fi

# Atualizar sistema
log "📦 Atualizando sistema..."
apt update && apt upgrade -y

# Instalar dependências
log "🔧 Instalando dependências..."
apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx curl

# Iniciar Docker
log "🐳 Iniciando Docker..."
systemctl start docker
systemctl enable docker

# Criar diretórios necessários
log "📁 Criando estrutura de diretórios..."
mkdir -p /opt/yolo-api
mkdir -p /opt/yolo-api/ssl
mkdir -p /opt/yolo-api/logs
mkdir -p /opt/yolo-api/models

# Copiar arquivos para produção
log "📋 Copiando arquivos..."
cp -r . /opt/yolo-api/
cd /opt/yolo-api

# Configurar domínio nos arquivos
log "⚙️ Configurando domínio..."
sed -i "s/api.seudominio.com/$DOMAIN/g" nginx.conf
sed -i "s/api.seudominio.com/$DOMAIN/g" docker-compose.prod.yml
sed -i "s/seu-email@exemplo.com/$EMAIL/g" docker-compose.prod.yml

# Parar Nginx se estiver rodando
log "🛑 Parando Nginx local..."
systemctl stop nginx 2>/dev/null || true

# Obter certificado SSL
log "🔒 Obtendo certificado SSL..."
docker-compose -f docker-compose.prod.yml run --rm certbot || warn "Falha ao obter certificado SSL automaticamente"

# Verificar se o certificado foi criado
if [ ! -f "./ssl/live/$DOMAIN/fullchain.pem" ]; then
    warn "Certificado SSL não encontrado. Configurando certificado temporário..."
    
    # Criar certificado auto-assinado temporário
    mkdir -p ./ssl/live/$DOMAIN
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ./ssl/live/$DOMAIN/privkey.pem \
        -out ./ssl/live/$DOMAIN/fullchain.pem \
        -subj "/C=BR/ST=State/L=City/O=Organization/CN=$DOMAIN"
    
    warn "Certificado temporário criado. Configure o DNS e execute: certbot --nginx -d $DOMAIN"
fi

# Construir e iniciar containers
log "🏗️ Construindo e iniciando containers..."
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Aguardar API inicializar
log "⏳ Aguardando API inicializar..."
sleep 30

# Verificar se a API está funcionando
log "🔍 Verificando status da API..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log "✅ API está funcionando localmente"
else
    error "❌ API não está respondendo"
fi

# Configurar firewall
log "🔥 Configurando firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Configurar renovação automática do SSL
log "🔄 Configurando renovação automática do SSL..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet && docker-compose -f /opt/yolo-api/docker-compose.prod.yml restart nginx") | crontab -

# Criar script de monitoramento
log "📊 Criando script de monitoramento..."
cat > /opt/yolo-api/monitor.sh << 'EOF'
#!/bin/bash
# Script de monitoramento da API

API_URL="https://api.seudominio.com/health"
LOG_FILE="/opt/yolo-api/logs/monitor.log"

check_api() {
    if curl -f -s "$API_URL" > /dev/null; then
        echo "$(date): API OK" >> "$LOG_FILE"
        return 0
    else
        echo "$(date): API DOWN - Reiniciando..." >> "$LOG_FILE"
        cd /opt/yolo-api
        docker-compose -f docker-compose.prod.yml restart yolo-api
        return 1
    fi
}

check_api
EOF

chmod +x /opt/yolo-api/monitor.sh
sed -i "s/api.seudominio.com/$DOMAIN/g" /opt/yolo-api/monitor.sh

# Configurar monitoramento automático
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/yolo-api/monitor.sh") | crontab -

# Mostrar informações finais
log "🎉 Deploy concluído com sucesso!"
echo
echo -e "${BLUE}📋 Informações do Deploy:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "🌐 URL da API: https://$DOMAIN"
echo -e "📚 Documentação: https://$DOMAIN/docs"
echo -e "❤️ Health Check: https://$DOMAIN/health"
echo -e "📁 Diretório: /opt/yolo-api"
echo -e "📊 Logs: /opt/yolo-api/logs"
echo
echo -e "${YELLOW}⚠️ Próximos passos:${NC}"
echo "1. Configure o DNS do domínio para apontar para este servidor"
echo "2. Aguarde a propagação do DNS (pode levar até 24h)"
echo "3. Execute: certbot --nginx -d $DOMAIN (se o SSL automático falhou)"
echo "4. Teste a API: curl https://$DOMAIN/health"
echo
echo -e "${GREEN}✅ Comandos úteis:${NC}"
echo "• Ver logs: docker-compose -f /opt/yolo-api/docker-compose.prod.yml logs -f"
echo "• Reiniciar: docker-compose -f /opt/yolo-api/docker-compose.prod.yml restart"
echo "• Parar: docker-compose -f /opt/yolo-api/docker-compose.prod.yml down"
echo "• Status: docker-compose -f /opt/yolo-api/docker-compose.prod.yml ps"
