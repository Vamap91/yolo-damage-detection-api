# 🚀 Guia de Deploy para Produção

Este guia mostra como colocar sua API YOLO em produção com HTTPS e domínio personalizado.

## 🎯 Opções de Deploy

### 1. 🖥️ Servidor VPS/Dedicado (Recomendado)

**Requisitos:**
- Ubuntu 20.04+ ou CentOS 8+
- 4GB+ RAM
- 2+ CPU cores
- 20GB+ storage
- Domínio configurado

**Deploy Automático:**
```bash
# 1. Fazer upload dos arquivos para o servidor
scp -r yolo-api/ root@seu-servidor:/tmp/

# 2. Conectar ao servidor
ssh root@seu-servidor

# 3. Executar deploy automático
cd /tmp/yolo-api
chmod +x deploy.sh
./deploy.sh api.seudominio.com admin@seudominio.com
```

**Deploy Manual:**
```bash
# 1. Instalar dependências
apt update && apt install -y docker.io docker-compose nginx certbot

# 2. Configurar arquivos
sed -i 's/api.seudominio.com/SEU_DOMINIO/g' nginx.conf
sed -i 's/seu-email@exemplo.com/SEU_EMAIL/g' docker-compose.prod.yml

# 3. Obter certificado SSL
certbot --nginx -d SEU_DOMINIO

# 4. Iniciar containers
docker-compose -f docker-compose.prod.yml up -d
```

### 2. ☁️ Plataformas Cloud (PaaS)

#### Railway.app
```bash
# 1. Instalar Railway CLI
npm install -g @railway/cli

# 2. Login e deploy
railway login
railway init
railway up
```

#### Render.com
```bash
# 1. Conectar repositório GitHub ao Render
# 2. Usar arquivo render.yaml incluído
# 3. Deploy automático via Git
```

#### Google Cloud Run
```bash
# 1. Construir imagem
docker build -f Dockerfile.prod -t gcr.io/SEU_PROJETO/yolo-api .

# 2. Push para registry
docker push gcr.io/SEU_PROJETO/yolo-api

# 3. Deploy
gcloud run deploy yolo-api \
  --image gcr.io/SEU_PROJETO/yolo-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2
```

#### AWS ECS/Fargate
```bash
# 1. Criar task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 2. Criar serviço
aws ecs create-service \
  --cluster yolo-cluster \
  --service-name yolo-api \
  --task-definition yolo-api:1 \
  --desired-count 1
```

### 3. 🐳 Docker Swarm/Kubernetes

#### Docker Swarm
```bash
# 1. Inicializar swarm
docker swarm init

# 2. Deploy stack
docker stack deploy -c docker-compose.prod.yml yolo-api
```

#### Kubernetes
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: yolo-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: yolo-api
  template:
    metadata:
      labels:
        app: yolo-api
    spec:
      containers:
      - name: yolo-api
        image: yolo-api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
```

## 🔧 Configuração de Domínio

### 1. DNS Configuration
```
Tipo: A
Nome: api
Valor: IP_DO_SERVIDOR
TTL: 300
```

### 2. Subdomínio
```
api.seudominio.com → IP_DO_SERVIDOR
```

### 3. Verificar DNS
```bash
nslookup api.seudominio.com
dig api.seudominio.com
```

## 🔒 SSL/HTTPS

### Let's Encrypt (Gratuito)
```bash
# Automático via Certbot
certbot --nginx -d api.seudominio.com

# Manual
certbot certonly --webroot -w /var/www/html -d api.seudominio.com
```

### Cloudflare (Recomendado)
1. Adicionar domínio ao Cloudflare
2. Configurar DNS proxy
3. SSL automático + CDN + DDoS protection

## 📊 Monitoramento

### 1. Health Checks
```bash
# Verificar status
curl https://api.seudominio.com/health

# Monitoramento contínuo
watch -n 30 'curl -s https://api.seudominio.com/health | jq'
```

### 2. Logs
```bash
# Docker logs
docker-compose -f docker-compose.prod.yml logs -f yolo-api

# Nginx logs
tail -f /var/log/nginx/api_access.log
tail -f /var/log/nginx/api_error.log
```

### 3. Métricas
```bash
# Uso de recursos
docker stats

# Espaço em disco
df -h

# Memória
free -h
```

## 🔧 Manutenção

### Backup
```bash
# Backup dos logs
tar -czf backup-$(date +%Y%m%d).tar.gz /opt/yolo-api/logs

# Backup da configuração
cp -r /opt/yolo-api /backup/yolo-api-$(date +%Y%m%d)
```

### Atualizações
```bash
# Atualizar código
cd /opt/yolo-api
git pull origin main

# Rebuild e restart
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### Scaling
```bash
# Aumentar réplicas
docker-compose -f docker-compose.prod.yml up -d --scale yolo-api=3

# Load balancer (Nginx)
upstream yolo_api {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}
```

## 🚨 Troubleshooting

### Problemas Comuns

#### 1. Erro de Memória
```bash
# Aumentar swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

#### 2. Certificado SSL
```bash
# Renovar certificado
certbot renew --dry-run

# Forçar renovação
certbot renew --force-renewal
```

#### 3. Container não inicia
```bash
# Verificar logs
docker-compose -f docker-compose.prod.yml logs yolo-api

# Verificar recursos
docker system df
docker system prune
```

#### 4. API lenta
```bash
# Verificar CPU/Memória
htop

# Otimizar workers
# Editar docker-compose.prod.yml
environment:
  - WORKERS=4  # CPU cores * 2
```

## 📈 Performance

### Otimizações
- **Workers**: CPU cores × 2
- **Memory**: 4GB+ recomendado
- **Cache**: Redis para cache de modelos
- **CDN**: Cloudflare para assets estáticos
- **Database**: PostgreSQL para logs/analytics

### Benchmarks
```bash
# Teste de carga
ab -n 100 -c 10 https://api.seudominio.com/health

# Teste com imagem
curl -X POST -F "file=@test.jpg" https://api.seudominio.com/detect
```

## 💰 Custos Estimados

| Opção | Custo/mês | Recursos |
|-------|-----------|----------|
| VPS Digital Ocean | $20-40 | 4GB RAM, 2 CPU |
| AWS EC2 t3.medium | $30-50 | 4GB RAM, 2 CPU |
| Google Cloud Run | $10-30 | Pay per use |
| Railway.app | $5-20 | Managed hosting |
| Render.com | $7-25 | Managed hosting |

## 🔐 Segurança

### Checklist
- ✅ HTTPS obrigatório
- ✅ Firewall configurado
- ✅ Rate limiting
- ✅ Input validation
- ✅ Logs de auditoria
- ✅ Backup automático
- ✅ Monitoramento 24/7

### Hardening
```bash
# Fail2ban
apt install fail2ban

# UFW Firewall
ufw enable
ufw allow 22,80,443/tcp

# Automatic updates
apt install unattended-upgrades
```

## 📞 Suporte

Para problemas específicos:
1. Verificar logs: `docker-compose logs`
2. Testar health check: `curl /health`
3. Verificar recursos: `htop`, `df -h`
4. Consultar documentação: `/docs`

---

**🎉 Sua API estará disponível em: `https://api.seudominio.com`**
