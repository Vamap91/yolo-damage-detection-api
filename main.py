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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar app FastAPI
app = FastAPI(
    title="YOLO Vehicle Damage Detection API",
    description="API para detecção de danos em veículos usando YOLOv8",
    version="2.0.0"
)

# CORS
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

def download_and_load_model():
    """Baixa e carrega o modelo em thread separada."""
    global model, model_ready, model_error
    
    try:
        logger.info("🔄 Iniciando download do modelo...")
        
        # Download
        model_path = "car_damage_best.pt"
        if not os.path.exists(model_path):
            model_url = "https://github.com/Vamap91/YOLOProject/releases/download/v2.0.0/car_damage_best.pt"
            
            response = requests.get(model_url, stream=True, timeout=300)
            response.raise_for_status()
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info("✅ Modelo baixado!")
        
        # Carregamento
        logger.info("🤖 Carregando modelo YOLO...")
        from ultralytics import YOLO
        model = YOLO(model_path)
        model_ready = True
        logger.info("✅ Modelo carregado e pronto!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar modelo: {e}")
        model_error = str(e)

# Iniciar carregamento em background (após 3 segundos)
def start_model_loading():
    time.sleep(3)  # Aguarda app inicializar
    download_and_load_model()

threading.Thread(target=start_model_loading, daemon=True).start()

@app.get("/")
def root():
    """Endpoint raiz."""
    return {
        "message": "🚗 YOLO Vehicle Damage Detection API",
        "version": "2.0.0", 
        "status": "running",
        "model_ready": model_ready
    }

@app.get("/health")
def health():
    """Health check que SEMPRE funciona."""
    return {"status": "ok"}

@app.get("/ready")
def ready():
    """Verifica se modelo está pronto."""
    return {
        "model_ready": model_ready,
        "model_error": model_error,
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
    
    # Verificar se arquivo é imagem
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
        # Processar imagem
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Redimensionar se necessário
        max_size = 1024
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
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
        "status": "ready"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Iniciando servidor na porta {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
