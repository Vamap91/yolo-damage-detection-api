# YOLO Vehicle Damage Detection API

API REST para detecção de danos em veículos usando YOLOv8.

## 🚀 Funcionalidades

- **Detecção automática de danos** em imagens de veículos
- **6 tipos de danos detectados**: Vidro quebrado, Lâmpada quebrada, Pneu vazio, Amassado, Risco, Rachadura
- **Classificação de severidade**: Leve, Moderado, Severo
- **Identificação de localização**: Carroceria, Pintura, Para-brisa/Vidros, etc.
- **Imagem anotada** com danos destacados
- **API RESTful** com documentação automática

## 📋 Pré-requisitos

- Python 3.11+
- Docker (opcional)
- 4GB+ de RAM (para carregar o modelo YOLO)

## 🛠️ Instalação

### Opção 1: Instalação Local

```bash
# Clonar/copiar os arquivos da API
cd yolo-api

# Instalar dependências
pip install -r requirements.txt

# Executar a API
python main.py
```

### Opção 2: Docker

```bash
# Construir e executar com Docker Compose
docker-compose up --build

# Ou construir manualmente
docker build -t yolo-api .
docker run -p 8000:8000 yolo-api
```

## 📖 Uso da API

### Endpoints Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Informações básicas da API |
| `/health` | GET | Status de saúde da API |
| `/detect` | POST | Detectar danos em imagem |
| `/model/info` | GET | Informações do modelo |
| `/docs` | GET | Documentação interativa (Swagger) |

### Exemplo de Uso

#### 1. Verificar Status da API

```bash
curl http://localhost:8000/health
```

#### 2. Detectar Danos em Imagem

```bash
curl -X POST "http://localhost:8000/detect" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@caminho/para/imagem.jpg" \
  -F "include_annotated_image=true" \
  -F "vehicle_plate=ABC-1234" \
  -F "vehicle_model=Toyota Corolla"
```

#### 3. Usando Python

```python
import requests

# Detectar danos
with open('imagem_veiculo.jpg', 'rb') as f:
    files = {'file': f}
    data = {
        'include_annotated_image': True,
        'vehicle_plate': 'ABC-1234',
        'vehicle_model': 'Toyota Corolla'
    }
    
    response = requests.post('http://localhost:8000/detect', files=files, data=data)
    result = response.json()
    
    print(f"Danos encontrados: {result['damage_analysis']['total_damages']}")
    print(f"Urgência: {result['damage_analysis']['repair_urgency']}")
```

## 📊 Formato de Resposta

```json
{
  "inspection_info": {
    "timestamp": "2024-09-17T12:00:00",
    "inspector": "Sistema IA YOLO API",
    "version": "2.0.0",
    "model": "YOLOv8 (car_damage_best.pt)",
    "original_filename": "carro.jpg"
  },
  "vehicle_info": {
    "plate": "ABC-1234",
    "model": "Toyota Corolla",
    "year": "2020",
    "color": "Branco"
  },
  "damage_analysis": {
    "total_damages": 2,
    "severity_count": {
      "Leve": 1,
      "Moderado": 1,
      "Severo": 0
    },
    "damage_types": ["Amassado", "Risco"],
    "repair_urgency": "Média"
  },
  "damages": [
    {
      "damage_id": "DMG_001",
      "class": "dent",
      "class_display": "Amassado",
      "confidence": 0.85,
      "severity": "Moderado",
      "location": "Carroceria",
      "bbox": [100, 150, 200, 250]
    }
  ],
  "annotated_image": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
}
```

## 🧪 Testes

Execute o script de teste incluído:

```bash
python test_api.py
```

Este script irá:
- Verificar o status da API
- Obter informações do modelo
- Criar uma imagem de teste
- Executar detecção de danos
- Salvar a imagem anotada

## 🔧 Configuração

### Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `HOST` | Host da API | `0.0.0.0` |
| `PORT` | Porta da API | `8000` |
| `MODEL_URL` | URL do modelo YOLO | GitHub Release |

### Personalização

Para usar um modelo personalizado, modifique a URL em `main.py`:

```python
model_url = "https://seu-repositorio.com/modelo.pt"
```

## 📈 Performance

- **Primeira execução**: ~30-60 segundos (download do modelo)
- **Execuções subsequentes**: ~1-3 segundos por imagem
- **Tamanho do modelo**: ~50MB
- **Memória necessária**: ~2-4GB

## 🐛 Troubleshooting

### Erro de Memória
```bash
# Aumentar limite de memória do Docker
docker run -m 4g -p 8000:8000 yolo-api
```

### Modelo não carrega
- Verificar conexão com internet
- Verificar espaço em disco
- Verificar logs: `docker logs container_id`

### Erro de dependências
```bash
# Reinstalar dependências
pip install --upgrade -r requirements.txt
```

## 📝 Logs

A API gera logs detalhados incluindo:
- Status de download do modelo
- Tempo de processamento
- Erros e exceções
- Estatísticas de uso

## 🔒 Segurança

- Validação de tipos de arquivo
- Limite de tamanho de upload
- Sanitização de entrada
- CORS configurado

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📞 Suporte

Para suporte e dúvidas:
- Abra uma issue no GitHub
- Consulte a documentação em `/docs`
- Verifique os logs da aplicação
