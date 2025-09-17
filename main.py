from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image
import os
import json
from datetime import datetime
from ultralytics import YOLO
import requests
import io
import base64
from typing import Optional, List, Dict, Any
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YOLO Vehicle Damage Detection API",
    description="API para detecção de danos em veículos usando YOLOv8",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração dos danos
DAMAGE_CONFIG = {
    'severity_map': {
        'shattered_glass': 'Severo',
        'broken_lamp': 'Severo',
        'flat_tire': 'Severo',
        'dent': 'Moderado',
        'scratch': 'Leve',
        'crack': 'Leve'
    },
    'location_map': {
        'shattered_glass': 'Para-brisa/Vidros',
        'flat_tire': 'Rodas',
        'broken_lamp': 'Faróis/Lanternas',
        'dent': 'Carroceria',
        'scratch': 'Pintura',
        'crack': 'Para-choque/Plásticos'
    },
    'class_names': {
        'shattered_glass': 'Vidro Quebrado',
        'broken_lamp': 'Lâmpada Quebrada',
        'flat_tire': 'Pneu Vazio',
        'dent': 'Amassado',
        'scratch': 'Risco',
        'crack': 'Rachadura'
    }
}

# Variável global para o modelo
model = None

def download_model():
    """Baixa o modelo do GitHub se não existir localmente."""
    model_path = "car_damage_best.pt"
    
    if not os.path.exists(model_path):
        logger.info("Baixando modelo do GitHub...")
        model_url = "https://github.com/Vamap91/YOLOProject/releases/download/v2.0.0/car_damage_best.pt"
        
        try:
            response = requests.get(model_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and downloaded % (1024 * 1024 * 5) == 0:  # Log a cada 5MB
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Download: {progress:.1f}% ({downloaded / 1024 / 1024:.1f}MB)")
            
            logger.info(f"Modelo baixado com sucesso! Tamanho: {downloaded / 1024 / 1024:.1f}MB")
            
        except Exception as e:
            logger.error(f"Erro ao baixar o modelo: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao baixar o modelo: {e}")
    
    return model_path

def load_model():
    """Carrega o modelo YOLO."""
    global model
    
    if model is None:
        try:
            model_path = download_model()
            logger.info("Carregando modelo YOLO...")
            model = YOLO(model_path)
            logger.info("Modelo carregado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao carregar o modelo: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao carregar o modelo: {e}")
    
    return model

def process_image(image: Image.Image) -> tuple:
    """Processa a imagem com o modelo YOLO."""
    try:
        model = load_model()
        img_array = np.array(image)
        
        # Executar predição
        results = model(img_array, verbose=False)
        
        detections = []
        if len(results[0].boxes) > 0:
            for box in results[0].boxes:
                class_id = int(box.cls)
                class_name = model.names[class_id]
                detection = {
                    'class': class_name,
                    'confidence': float(box.conf),
                    'bbox': box.xyxy[0].cpu().numpy().tolist()
                }
                detections.append(detection)
        
        # Gerar imagem anotada
        annotated_img = results[0].plot()
        annotated_pil = Image.fromarray(annotated_img)
        
        return detections, annotated_pil
        
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar imagem: {e}")

def create_damage_analysis(detections: List[Dict]) -> List[Dict]:
    """Analisa as detecções de danos."""
    damage_report = []
    for i, detection in enumerate(detections):
        class_name = detection['class']
        severity = DAMAGE_CONFIG['severity_map'].get(class_name, 'Indefinido')
        location = DAMAGE_CONFIG['location_map'].get(class_name, 'N/A')
        
        damage_report.append({
            'damage_id': f"DMG_{i+1:03d}",
            'class': class_name,
            'class_display': DAMAGE_CONFIG['class_names'].get(class_name, class_name.replace('_', ' ').title()),
            'confidence': detection['confidence'],
            'severity': severity,
            'location': location,
            'bbox': detection['bbox']
        })
    return damage_report

def image_to_base64(image: Image.Image) -> str:
    """Converte imagem PIL para base64."""
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=85)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

@app.on_event("startup")
async def startup_event():
    """Carrega o modelo na inicialização da API."""
    logger.info("🚀 Iniciando YOLO Damage Detection API...")
    try:
        load_model()
        logger.info("✅ API iniciada com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")

@app.get("/")
async def root():
    """Endpoint raiz da API."""
    return {
        "message": "🚗 YOLO Vehicle Damage Detection API",
        "version": "2.0.0",
        "status": "running",
        "model_loaded": model is not None,
        "endpoints": {
            "detect": "/detect",
            "health": "/health",
            "model_info": "/model/info",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Endpoint de verificação de saúde da API."""
    try:
        model_loaded = model is not None
        return {
            "status": "healthy" if model_loaded else "loading",
            "model_loaded": model_loaded,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/detect")
async def detect_damage(
    file: UploadFile = File(...),
    include_annotated_image: bool = True,
    vehicle_plate: Optional[str] = None,
    vehicle_model: Optional[str] = None,
    vehicle_year: Optional[int] = None,
    vehicle_color: Optional[str] = None
):
    """
    Detecta danos em uma imagem de veículo.
    """
    
    # Validar tipo de arquivo
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser uma imagem")
    
    try:
        # Ler e processar a imagem
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Redimensionar se muito grande (otimização)
        max_size = 1024
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Detectar danos
        detections, annotated_img = process_image(image)
        
        # Analisar danos
        damage_analysis = create_damage_analysis(detections)
        
        # Calcular estatísticas
        severity_count = {'Leve': 0, 'Moderado': 0, 'Severo': 0}
        damage_types = []
        
        for damage in damage_analysis:
            severity = damage.get('severity', 'Indefinido')
            if severity in severity_count:
                severity_count[severity] += 1
            if damage['class_display'] not in damage_types:
                damage_types.append(damage['class_display'])
        
        # Determinar urgência
        urgency = 'Baixa'
        if severity_count['Severo'] > 0:
            urgency = 'Alta'
        elif severity_count['Moderado'] > 0:
            urgency = 'Média'
        
        # Preparar informações do veículo
        vehicle_info = {
            "plate": vehicle_plate or "Não informado",
            "model": vehicle_model or "Não informado",
            "year": str(vehicle_year) if vehicle_year else "Não informado",
            "color": vehicle_color or "Não informado"
        }
        
        # Preparar resposta
        response = {
            "inspection_info": {
                "timestamp": datetime.now().isoformat(),
                "inspector": "Sistema IA YOLO API",
                "version": "2.0.0",
                "model": "YOLOv8 (car_damage_best.pt)",
                "original_filename": file.filename
            },
            "vehicle_info": vehicle_info,
            "damage_analysis": {
                "total_damages": len(damage_analysis),
                "severity_count": severity_count,
                "damage_types": sorted(damage_types),
                "repair_urgency": urgency,
            },
            "damages": damage_analysis
        }
        
        # Incluir imagem anotada se solicitado
        if include_annotated_image and annotated_img:
            response["annotated_image"] = image_to_base64(annotated_img)
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Erro na detecção: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar imagem: {str(e)}")

@app.get("/model/info")
async def model_info():
    """Retorna informações sobre o modelo carregado."""
    try:
        model = load_model()
        return {
            "model_type": "YOLOv8",
            "model_file": "car_damage_best.pt",
            "classes": list(DAMAGE_CONFIG['class_names'].values()),
            "total_classes": len(DAMAGE_CONFIG['class_names']),
            "severity_levels": list(set(DAMAGE_CONFIG['severity_map'].values())),
            "locations": list(set(DAMAGE_CONFIG['location_map'].values())),
            "model_loaded": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter informações do modelo: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
