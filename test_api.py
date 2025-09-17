#!/usr/bin/env python3
"""
Script de teste para a API de detecção de danos veiculares.
"""

import requests
import json
import base64
from PIL import Image
import io

# Configuração da API
API_BASE_URL = "http://localhost:8000"

def test_health():
    """Testa o endpoint de health check."""
    print("🔍 Testando health check...")
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_model_info():
    """Testa o endpoint de informações do modelo."""
    print("🔍 Testando informações do modelo...")
    response = requests.get(f"{API_BASE_URL}/model/info")
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_detection(image_path: str):
    """Testa o endpoint de detecção de danos."""
    print(f"🔍 Testando detecção com imagem: {image_path}")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (image_path, f, 'image/jpeg')}
            data = {
                'include_annotated_image': True,
                'vehicle_plate': 'ABC-1234',
                'vehicle_model': 'Toyota Corolla',
                'vehicle_year': 2020,
                'vehicle_color': 'Branco'
            }
            
            response = requests.post(f"{API_BASE_URL}/detect", files=files, data=data)
            
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Mostrar informações básicas
            print(f"Total de danos: {result['damage_analysis']['total_damages']}")
            print(f"Urgência: {result['damage_analysis']['repair_urgency']}")
            print(f"Tipos de dano: {result['damage_analysis']['damage_types']}")
            
            # Mostrar detalhes dos danos
            if result['damages']:
                print("\nDetalhes dos danos:")
                for damage in result['damages']:
                    print(f"  - {damage['class_display']}: {damage['severity']} "
                          f"(Confiança: {damage['confidence']:.2%}) - {damage['location']}")
            
            # Salvar imagem anotada se disponível
            if 'annotated_image' in result:
                print("\n💾 Salvando imagem anotada...")
                img_data = result['annotated_image'].split(',')[1]  # Remove o prefixo data:image/jpeg;base64,
                img_bytes = base64.b64decode(img_data)
                
                with open('resultado_anotado.jpg', 'wb') as f:
                    f.write(img_bytes)
                print("✅ Imagem salva como 'resultado_anotado.jpg'")
        else:
            print(f"Erro: {response.text}")
            
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {image_path}")
    except Exception as e:
        print(f"❌ Erro: {e}")
    
    print("-" * 50)

def create_test_image():
    """Cria uma imagem de teste simples."""
    print("🎨 Criando imagem de teste...")
    
    # Criar uma imagem simples para teste
    img = Image.new('RGB', (640, 480), color='lightblue')
    img.save('test_image.jpg')
    
    print("✅ Imagem de teste criada: test_image.jpg")
    return 'test_image.jpg'

def main():
    """Função principal de teste."""
    print("🚀 Iniciando testes da API YOLO...")
    print("=" * 50)
    
    # Testar endpoints básicos
    test_health()
    test_model_info()
    
    # Criar imagem de teste se necessário
    test_image = create_test_image()
    
    # Testar detecção
    test_detection(test_image)
    
    print("✅ Testes concluídos!")

if __name__ == "__main__":
    main()
