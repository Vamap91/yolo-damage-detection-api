from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image
import os
import json
from datetime import datetime
import requests
import io
import base64
from typing import Optional, List, Dict, Any
import logging
import threading
import time

# Configurar logging para Google Cloud
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar app FastAPI
app = FastAPI(
    title="YOLO Vehicle Damage Detection API",
    description="API para detecção de danos em veículos usando YOLOv8",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configurado para produção
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

# Variáveis globais
model = None
model_ready = False
model_error = None
startup_time = datetime.now()

def download_and_load_model():
    """Baixa e carrega o modelo YOLO."""
    global model, model_ready, model_error
    
    try:
        logger.info("🔄 Iniciando download do modelo YOLO...")
        
        # Download do modelo
        model_path = "/tmp/car_damage_best.pt"  # Usar /tmp no Cloud Run
        if not os.path.exists(model_path):
            model_url = "https://github.com/Vamap91/YOLOProject/releases/download/v2.0.0/car_damage_best.pt"
            
            logger.info(f"📥 Baixando modelo de: {model_url}")
            response = requests.get(model_url, stream=True, timeout=600)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progresso a cada 10MB
                        if downloaded % (10 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                            logger.info(f"📥 Download: {progress:.1f}% ({downloaded / 1024 / 1024:.1f}MB)")
            
            logger.info(f"✅ Modelo baixado! Tamanho: {downloaded / 1024 / 1024:.1f}MB")
        else:
            logger.info("✅ Modelo já existe no cache")
        
        # Carregamento do modelo
        logger.info("🤖 Carregando modelo YOLO...")
        from ultralytics import YOLO
        model = YOLO(model_path)
        model_ready = True
        
        # Fazer uma predição de teste para "aquecer" o modelo
        logger.info("🔥 Aquecendo modelo...")
        test_image = np.zeros((640, 640, 3), dtype=np.uint8)
        _ = model(test_image, verbose=False)
        
        logger.info("✅ Modelo carregado e aquecido com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar modelo: {e}")
        model_error = str(e)
        model_ready = False

def start_model_loading():
    """Inicia carregamento do modelo em background."""
    time.sleep(2)  # Pequeno delay para app inicializar
    download_and_load_model()

# Iniciar carregamento em background
threading.Thread(target=start_model_loading, daemon=True).start()

@app.get("/")
def root():
    """Endpoint raiz com informações da API."""
    uptime = datetime.now() - startup_time
    return {
        "message": "🚗 YOLO Vehicle Damage Detection API",
        "version": "2.0.0",
        "status": "running",
        "model_ready": model_ready,
        "uptime_seconds": int(uptime.total_seconds()),
        "endpoints": {
            "health": "/health",
            "ready": "/ready", 
            "detect": "/detect",
            "model_info": "/model/info",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    """Health check para Google Cloud Run."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "yolo-damage-detection"
    }

@app.get("/ready")
def ready():
    """Endpoint para verificar se modelo está pronto."""
    return {
        "model_ready": model_ready,
        "model_error": model_error,
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": int((datetime.now() - startup_time).total_seconds())
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
    """Detecta danos em uma imagem de veículo."""
    
    # Validar arquivo
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser uma imagem")
    
    # Verificar se modelo está pronto
    if not model_ready:
        if model_error:
            raise HTTPException(status_code=500, detail=f"Erro no modelo: {model_error}")
        else:
            raise HTTPException(
                status_code=503, 
                detail="Modelo ainda carregando. Aguarde alguns minutos e tente novamente."
            )
    
    try:
        start_time = time.time()
        
        # Processar imagem
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Redimensionar se muito grande
        max_size = 1024
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            logger.info(f"🖼️ Imagem redimensionada para: {image.size}")
        
        # Detectar com YOLO
        img_array = np.array(image)
        results = model(img_array, verbose=False)
        
        # Processar detecções
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
        
        logger.info(f"🔍 Detectados {len(detections)} danos")
        
        # Analisar danos
        damage_analysis = []
        for i, detection in enumerate(detections):
            class_name = detection['class']
            severity = DAMAGE_CONFIG['severity_map'].get(class_name, 'Indefinido')
            location = DAMAGE_CONFIG['location_map'].get(class_name, 'N/A')
            
            damage_analysis.append({
                'damage_id': f"DMG_{i+1:03d}",
                'class': class_name,
                'class_display': DAMAGE_CONFIG['class_names'].get(class_name, class_name.replace('_', ' ').title()),
                'confidence': detection['confidence'],
                'severity': severity,
                'location': location,
                'bbox': detection['bbox']
            })
        
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
        
        # Preparar resposta
        processing_time = time.time() - start_time
        
        response = {
            "inspection_info": {
                "timestamp": datetime.now().isoformat(),
                "inspector": "Sistema IA YOLO API",
                "version": "2.0.0",
                "original_filename": file.filename,
                "processing_time_seconds": round(processing_time, 2),
                "image_size": f"{image.size[0]}x{image.size[1]}"
            },
            "vehicle_info": {
                "plate": vehicle_plate or "Não informado",
                "model": vehicle_model or "Não informado", 
                "year": str(vehicle_year) if vehicle_year else "Não informado",
                "color": vehicle_color or "Não informado"
            },
            "damage_analysis": {
                "total_damages": len(damage_analysis),
                "severity_count": severity_count,
                "damage_types": sorted(damage_types),
                "repair_urgency": urgency,
            },
            "damages": damage_analysis
        }
        
        # Incluir imagem anotada se solicitado
        if include_annotated_image and len(detections) > 0:
            annotated_img = results[0].plot()
            annotated_pil = Image.fromarray(annotated_img)
            buffer = io.BytesIO()
            annotated_pil.save(buffer, format='JPEG', quality=85)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            response["annotated_image"] = f"data:image/jpeg;base64,{img_str}"
        
        logger.info(f"✅ Processamento concluído em {processing_time:.2f}s")
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"❌ Erro na detecção: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar imagem: {str(e)}")

@app.get("/model/info")
def model_info():
    """Informações sobre o modelo."""
    if not model_ready:
        return {
            "status": "not_ready",
            "error": model_error,
            "message": "Modelo ainda não carregado"
        }
    
    return {
        "model_type": "YOLOv8",
        "model_file": "car_damage_best.pt",
        "classes": list(DAMAGE_CONFIG['class_names'].values()),
        "total_classes": len(DAMAGE_CONFIG['class_names']),
        "status": "ready",
        "model_ready": model_ready
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))  # Cloud Run usa 8080 por padrão
    logger.info(f"🚀 Iniciando servidor na porta {port}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
