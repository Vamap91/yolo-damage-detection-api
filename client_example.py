#!/usr/bin/env python3
"""
Exemplo de cliente para consumir a API de detecção de danos veiculares.
Este é um exemplo simples que pode ser usado como base para integração.
"""

import requests
import json
import base64
from typing import Optional, Dict, Any

class YOLODamageDetectionClient:
    """Cliente para a API de detecção de danos veiculares."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Inicializa o cliente.
        
        Args:
            base_url: URL base da API
        """
        self.base_url = base_url.rstrip('/')
        
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica o status de saúde da API.
        
        Returns:
            Dicionário com o status da API
        """
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Obtém informações sobre o modelo carregado.
        
        Returns:
            Dicionário com informações do modelo
        """
        response = requests.get(f"{self.base_url}/model/info")
        response.raise_for_status()
        return response.json()
    
    def detect_damage(
        self,
        image_path: str,
        include_annotated_image: bool = True,
        vehicle_plate: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        vehicle_year: Optional[int] = None,
        vehicle_color: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detecta danos em uma imagem de veículo.
        
        Args:
            image_path: Caminho para o arquivo de imagem
            include_annotated_image: Se deve incluir a imagem anotada
            vehicle_plate: Placa do veículo (opcional)
            vehicle_model: Modelo do veículo (opcional)
            vehicle_year: Ano do veículo (opcional)
            vehicle_color: Cor do veículo (opcional)
            
        Returns:
            Dicionário com os resultados da detecção
        """
        with open(image_path, 'rb') as f:
            files = {'file': (image_path, f, 'image/jpeg')}
            data = {
                'include_annotated_image': include_annotated_image,
                'vehicle_plate': vehicle_plate,
                'vehicle_model': vehicle_model,
                'vehicle_year': vehicle_year,
                'vehicle_color': vehicle_color
            }
            
            # Remover valores None
            data = {k: v for k, v in data.items() if v is not None}
            
            response = requests.post(f"{self.base_url}/detect", files=files, data=data)
            response.raise_for_status()
            return response.json()
    
    def save_annotated_image(self, result: Dict[str, Any], output_path: str = "annotated_result.jpg"):
        """
        Salva a imagem anotada do resultado.
        
        Args:
            result: Resultado da detecção contendo a imagem anotada
            output_path: Caminho onde salvar a imagem
        """
        if 'annotated_image' not in result:
            raise ValueError("Resultado não contém imagem anotada")
        
        # Extrair dados da imagem base64
        img_data = result['annotated_image']
        if img_data.startswith('data:image'):
            img_data = img_data.split(',')[1]
        
        # Decodificar e salvar
        img_bytes = base64.b64decode(img_data)
        with open(output_path, 'wb') as f:
            f.write(img_bytes)
        
        print(f"Imagem anotada salva em: {output_path}")

def main():
    """Exemplo de uso do cliente."""
    
    # Inicializar cliente
    client = YOLODamageDetectionClient("http://localhost:8000")
    
    try:
        # Verificar status da API
        print("🔍 Verificando status da API...")
        health = client.health_check()
        print(f"Status: {health['status']}")
        print(f"Modelo carregado: {health['model_loaded']}")
        
        # Obter informações do modelo
        print("\n📊 Informações do modelo...")
        model_info = client.get_model_info()
        print(f"Tipo: {model_info['model_type']}")
        print(f"Classes detectadas: {len(model_info['classes'])}")
        print(f"Classes: {', '.join(model_info['classes'])}")
        
        # Exemplo de detecção (substitua pelo caminho da sua imagem)
        image_path = "exemplo_veiculo.jpg"
        
        print(f"\n🔍 Detectando danos em: {image_path}")
        result = client.detect_damage(
            image_path=image_path,
            include_annotated_image=True,
            vehicle_plate="ABC-1234",
            vehicle_model="Toyota Corolla",
            vehicle_year=2020,
            vehicle_color="Branco"
        )
        
        # Exibir resultados
        damage_analysis = result['damage_analysis']
        print(f"\n📋 Resultados:")
        print(f"Total de danos: {damage_analysis['total_damages']}")
        print(f"Urgência de reparo: {damage_analysis['repair_urgency']}")
        print(f"Tipos de dano: {', '.join(damage_analysis['damage_types'])}")
        
        # Detalhes dos danos
        if result['damages']:
            print(f"\n🔧 Detalhes dos danos:")
            for damage in result['damages']:
                print(f"  • {damage['class_display']}: {damage['severity']}")
                print(f"    Confiança: {damage['confidence']:.2%}")
                print(f"    Localização: {damage['location']}")
                print(f"    Coordenadas: {damage['bbox']}")
                print()
        
        # Salvar imagem anotada
        if 'annotated_image' in result:
            client.save_annotated_image(result, "resultado_deteccao.jpg")
        
        print("✅ Detecção concluída com sucesso!")
        
    except FileNotFoundError:
        print(f"❌ Arquivo de imagem não encontrado: {image_path}")
        print("💡 Crie uma imagem de teste ou use uma imagem existente")
        
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar à API")
        print("💡 Certifique-se de que a API está rodando em http://localhost:8000")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erro HTTP: {e}")
        print(f"Resposta: {e.response.text}")
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    main()
