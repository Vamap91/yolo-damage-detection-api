import os
import sys

# CONFIGURAÇÃO CRÍTICA: Deve ser feita ANTES de qualquer import
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '0'
os.environ['OPENCV_IO_ENABLE_JASPER'] = '0'  
os.environ['QT_X11_NO_MITSHM'] = '1'
os.environ['OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS'] = '0'
os.environ['MPLBACKEND'] = 'Agg'  # Matplotlib sem GUI

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Criar app FastAPI
app = FastAPI(
    title="YOLO Vehicle Damage Detection API",
    description="API para detecção de danos em veículos usando YOLOv8",
    version="2.1.0"
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

def test_opencv():
    """Testa se OpenCV está funcionando."""
    try:
        import cv2
        logger.info(f"✅ OpenCV versão: {cv2.__version__}")
        
        # Teste básico
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite('/tmp/test_opencv.jpg', test_img)
        os.remove('/tmp/test_opencv.jpg')
        logger.info("✅ OpenCV funcionando corretamente")
        return True
    except Exception as e:
        logger.error(f"❌ Erro OpenCV: {e}")
        return False

def download_and_load_model():
    """Baixa e carrega o modelo em thread separada."""
    global model, model_ready, model_error
    
    try:
        logger.info("🔄 Testando OpenCV...")
        if not test_opencv():
            model_error = "OpenCV não está funcionando corretamente"
            return
        
        logger.info("🔄 Iniciando download do modelo...")
        
        # Download
        model_path = "car_damage_best.pt"
        if not os.path.exists(model_path):
            model_url = "https://github.com/Vamap91/YOLOProject/releases/download/v2.0.0/car_damage_best.pt"
            
            logger.info(f"📥 Baixando de: {model_url}")
            response = requests.get(model_url, stream=True, timeout=600)  # 10 min timeout
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            if downloaded % (1024*1024) == 0:  # Log a cada MB
                                logger.info(f"📥 Download: {percent:.1f}%")
            
            logger.info("✅ Modelo baixado com sucesso!")
        
        # Carregamento do YOLO
        logger.info("🤖 Carregando modelo YOLO...")
        
        try:
            from ultralytics import YOLO
            
            # Configurar YOLO para modo silencioso
            import ultralytics
            ultralytics.settings.update({'verbose': False})
            
            # Carregar modelo
            model = YOLO(model_path)
            
            # Teste rápido
            test_img = np.zeros((640, 640, 3), dtype=np.uint8)
            test_results = model(test_img, verbose=False)
            logger.info(f"✅ Teste do modelo OK - Classes: {len(model.names)}")
            
            model_ready = True
            logger.info("🎉 Modelo YOLO carregado e testado com sucesso!")
            
        except Exception as yolo_error:
            logger.error(f"❌ Erro ao carregar YOLO: {yolo_error}")
            model_error = f"Erro YOLO: {str(yolo_error)}"
        
    except Exception as e:
        logger.error(f"❌ Erro geral: {e}")
        model_error = str(e)

# Iniciar carregamento em background
def start_model_loading():
    logger.info("⏳ Aguardando 5 segundos antes de carregar modelo...")
    time.sleep(5)
    download_and_load_model()

threading.Thread(target=start_model_loading, daemon=True).start()

@app.get("/")
def root():
    """Endpoint raiz."""
    return {
        "message": "🚗 YOLO Vehicle Damage Detection API",
        "version": "2.1.0", 
        "status": "running",
        "model_ready": model_ready,
        "opencv_working": test_opencv() if not model_ready else True
    }

@app.get("/health")
def health():
    """Health check que SEMPRE funciona."""
    return {
        "status": "ok",
        "model_ready": model_ready,
        "model_error": model_error,
        "timestamp": datetime.now().isoformat(),
        "system": "healthy"
    }

@app.get("/ready") 
def ready():
    """Verifica se modelo está pronto."""
    return {
        "model_ready": model_ready,
        "model_error": model_error,
        "opencv_status": "working" if test_opencv() else "error",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/debug")
def debug_info():
    """Informações de debug."""
    try:
        import cv2
        opencv_version = cv2.__version__
    except:
        opencv_version = "not_available"
    
    return {
        "python_version": sys.version,
        "opencv_version": opencv_version,
        "environment_vars": {
            "OPENCV_IO_ENABLE_OPENEXR": os.environ.get("OPENCV_IO_ENABLE_OPENEXR"),
            "QT_X11_NO_MITSHM": os.environ.get("QT_X11_NO_MITSHM"),
            "DISPLAY": os.environ.get("DISPLAY")
        },
        "model_status": {
            "ready": model_ready,
            "error": model_error,
            "model_file_exists": os.path.exists("car_damage_best.pt")
        }
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
    
    logger.info(f"🔍 Iniciando detecção para arquivo: {file.filename}")
    
    # Verificar tipo de arquivo
    if not file.content_type or not file.content_type.startswith('image/'):
        logger.error(f"❌ Tipo de arquivo inválido: {file.content_type}")
        raise HTTPException(status_code=400, detail="Arquivo deve ser uma imagem")
    
    # Verificar se modelo está pronto
    if not model_ready:
        if model_error:
            logger.error(f"❌ Modelo não está pronto: {model_error}")
            raise HTTPException(
                status_code=500, 
                detail=f"Erro no modelo: {model_error}"
            )
        else:
            logger.warning("⏳ Modelo ainda carregando")
            raise HTTPException(
                status_code=503, 
                detail="Modelo ainda carregando. Aguarde alguns minutos e tente novamente."
            )
    
    try:
        # Processar imagem
        logger.info("📥 Lendo arquivo de imagem...")
        contents = await file.read()
        logger.info(f"📊 Tamanho do arquivo: {len(contents)} bytes")
        
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        logger.info(f"🖼️ Dimensões da imagem: {image.size}")
        
        # Redimensionar se muito grande
        max_size = 1280
        if max(image.size) > max_size:
            original_size = image.size
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            logger.info(f"📏 Redimensionado de {original_size} para {image.size}")
        
        # Converter para numpy
        img_array = np.array(image)
        logger.info(f"🔢 Array shape: {img_array.shape}")
        
        # Executar detecção YOLO
        logger.info("🤖 Executando detecção YOLO...")
        results = model(img_array, verbose=False)
        logger.info("✅ Detecção YOLO concluída")
        
        # Processar resultados
        detections = []
        if len(results[0].boxes) > 0:
            logger.info(f"🎯 Encontradas {len(results[0].boxes)} detecções")
            for i, box in enumerate(results[0].boxes):
                class_id = int(box.cls)
                class_name = model.names[class_id]
                confidence = float(box.conf)
                bbox = box.xyxy[0].cpu().numpy().tolist()
                
                detection = {
                    'class': class_name,
                    'confidence': confidence,
                    'bbox': bbox
                }
                detections.append(detection)
                logger.info(f"  {i+1}. {class_name}: {confidence:.3f}")
        else:
            logger.info("ℹ️ Nenhum dano detectado")
        
        # Processar análise de danos
        damage_analysis = []
        for i, detection in enumerate(detections):
            class_name = detection['class']
            severity = DAMAGE_CONFIG['severity_map'].get(class_name, 'Indefinido')
            location = DAMAGE_CONFIG['location_map'].get(class_name, 'N/A')
            display_name = DAMAGE_CONFIG['class_names'].get(class_name, class_name.replace('_', ' ').title())
            
            damage_analysis.append({
                'damage_id': f"DMG_{i+1:03d}",
                'class': class_name,
                'class_display': display_name,
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
            display_name = damage['class_display']
            if display_name not in damage_types:
                damage_types.append(display_name)
        
        # Determinar urgência
        urgency = 'Baixa'
        if severity_count['Severo'] > 0:
            urgency = 'Alta'
        elif severity_count['Moderado'] > 0:
            urgency = 'Média'
        
        logger.info(f"📊 Análise: {len(damage_analysis)} danos, urgência {urgency}")
        
        # Preparar resposta
        response = {
            "inspection_info": {
                "timestamp": datetime.now().isoformat(),
                "inspector": "Sistema IA YOLO API",
                "version": "2.1.0",
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
            try:
                logger.info("🎨 Gerando imagem anotada...")
                annotated_img = results[0].plot()
                annotated_pil = Image.fromarray(annotated_img)
                
                buffer = io.BytesIO()
                annotated_pil.save(buffer, format='JPEG', quality=85)
                img_str = base64.b64encode(buffer.getvalue()).decode()
                response["annotated_image"] = f"data:image/jpeg;base64,{img_str}"
                logger.info("✅ Imagem anotada gerada")
                
            except Exception as plot_error:
                logger.warning(f"⚠️ Erro ao criar imagem anotada: {plot_error}")
                # Continuar sem imagem anotada
        
        logger.info("🎉 Detecção concluída com sucesso!")
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"❌ Erro durante detecção: {e}", exc_info=True)
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
        "model_names": model.names if model else None
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Iniciando servidor na porta {port}")
    logger.info(f"🐍 Python: {sys.version}")
    logger.info(f"🔧 OpenCV funcionando: {test_opencv()}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
