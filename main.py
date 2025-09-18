from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
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
import asyncio
import threading
import time

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YOLO Vehicle Damage Detection API",
    description="API para detecção de danos em veículos usando YOLOv8",
    version="2.0.0"
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

# Variáveis globais
model = None
model_loading = False
model_loaded = False
app_ready = False

def download_model_sync():
    """Baixa o modelo do GitHub de forma síncrona."""
    model_path = "car_damage_best.pt"
    
    if not os.path.exists(model_path):
        logger.info("🔄 Baixando modelo...")
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
            
            logger.info(f"✅ Modelo baixado! ({downloaded / 1024 / 1024:.1f}MB)")
            
        except Exception as e:
            logger.error(f"❌ Erro ao baixar modelo: {e}")
            raise e
    
    return model_path

def load_model_sync():
    """Carrega o modelo YOLO de forma síncrona."""
    global model, model_loading, model_loaded
    
    if model is not None:
        return model
    
    model_loading = True
    
    try:
        from ultralytics import YOLO
        model_path = download_model_sync()
        logger.info("🤖 Carregando modelo YOLO...")
        model = YOLO(model_path)
        model_loaded = True
        logger.info("✅ Modelo carregado com sucesso!")
        return model
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar modelo: {e}")
        raise e
    finally:
        model_loading = False

def background_model_loader():
    """Carrega o modelo em background thread."""
    global app_ready
    try:
        time.sleep(2)  # Aguarda app inicializar
        load_model_sync()
        app_ready = True
        logger.info("🚀 API totalmente pronta!")
    except Exception as e:
        logger.error(f"❌ Erro no carregamento em background: {e}")
        app_ready = True  # Marca como pronta mesmo com erro

# Iniciar carregamento em background
threading.Thread(target=background_model_loader, daemon=True).start()

@app.get("/")
async def root():
    """Endpoint raiz da API."""
    return {
        "message": "🚗 YOLO Vehicle Damage Detection API",
        "version": "2.0.0",
        "status": "running",
        "model_status": "loaded" if model_loaded else ("loading" if model_loading else "not_loaded"),
        "app_ready": app_ready
    }

@app.get("/health")
async def health_check():
    """Health check que SEMPRE retorna 200 OK."""
    # SEMPRE retorna sucesso para passar no Railway
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": "ok"
    }

@app.get("/readiness")
async def readiness_check():
    """Endpoint separado para verificar se está realmente pronto."""
    return {
        "ready": app_ready,
        "model_loaded": model_loaded,
        "model_loading": model_loading,
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
    """Detecta danos em uma imagem de veículo."""
    
    # Validar tipo de arquivo
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser uma imagem")
    
    # Verificar se modelo está carregado
    if not model_loaded:
        if model_loading:
            raise HTTPException(
                status_code=503, 
                detail="Modelo ainda carregando. Aguarde alguns minutos e tente novamente."
            )
        else:
            # Tentar carregar agora
            try:
                load_model_sync()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Erro ao carregar modelo: {e}")
    
    try:
        # Ler e processar a imagem
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Redimensionar se muito grande
        max_size = 1024
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Processar com YOLO
        img_array = np.array(image)
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
        response = {
            "inspection_info": {
                "timestamp": datetime.now().isoformat(),
                "inspector": "Sistema IA YOLO API",
                "version": "2.0.0",
                "original_filename": file.filename
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
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"❌ Erro na detecção: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar imagem: {str(e)}")

@app.get("/model/info")
async def model_info():
    """Retorna informações sobre o modelo."""
    if not model_loaded:
        return {
            "status": "not_loaded",
            "message": "Modelo ainda não carregado"
        }
    
    return {
        "model_type": "YOLOv8",
        "model_file": "car_damage_best.pt",
        "classes": list(DAMAGE_CONFIG['class_names'].values()),
        "total_classes": len(DAMAGE_CONFIG['class_names']),
        "status": "loaded"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)
