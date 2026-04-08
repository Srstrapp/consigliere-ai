"""
Cliente de DeepSeek AI - Strategy Pattern con TOML
Carga prompts desde archivo de configuración para optimizar tokens
"""

from openai import AsyncOpenAI
from typing import Optional, List, Dict
from pydantic import BaseModel
import json
import os


# ==================== SCHEMAS ====================

class GastoData(BaseModel):
    """Schema para datos de gasto"""
    monto: float
    categoria: str = "otro"
    desc: str = ""


class IntencionData(BaseModel):
    """Schema para intención detectada"""
    intencion: str
    confianza: float = 1.0


# ==================== EXCEPCIONES ====================

class IAError(Exception):
    """Excepción base para errores de IA"""
    pass


class IAConfigurationError(IAError):
    """Error de configuración - API key faltante"""
    pass


class IAResponseError(IAError):
    """Error en la respuesta de la IA"""
    pass


# ==================== CARGAR TOML ====================

def load_toml_config() -> Dict:
    """Cargar configuración TOML de prompts"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "prompts.toml")
    
    if not os.path.exists(config_path):
        return {}
    
    # Parser TOML manual simple (evitar dependencia extra)
    config = {}
    current_section = ""
    lines = open(config_path, encoding="utf-8").readlines()
    
    for line in lines:
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith("#") or line.startswith("=="):
            continue
        
        # Section headers
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
            config[current_section] = {}
            continue
        
        # Key-value pairs
        if "=" in line and current_section:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            if current_section not in config:
                config[current_section] = {}
            
            # Parse nested keys (a.b = value -> {a: {b: value}})
            if "." in key:
                parent, child = key.split(".", 1)
                if parent not in config[current_section]:
                    config[current_section][parent] = {}
                config[current_section][parent][child] = value
            else:
                config[current_section][key] = value
    
    return config


# ==================== INTERFACES ====================

class IAChatService:
    """Interface para chat con IA"""
    
    async def chat(self, mensaje: str, contexto: Optional[List[Dict]] = None, modo: str = "system") -> str:
        """Enviar mensaje y obtener respuesta"""
        raise NotImplementedError


class IAGastoAnalyzer:
    """Interface para analizar gastos"""
    
    async def analizar(self, texto: str) -> GastoData:
        """Analizar texto y extraer datos del gasto"""
        raise NotImplementedError


class IANLPService:
    """Interface para NLP (intenciones, etc)"""
    
    async def detectar_intención(self, mensaje: str) -> IntencionData:
        """Detectar intención del mensaje"""
        raise NotImplementedError


# ==================== IMPLEMENTACIÓN ====================

class DeepSeekService(IAChatService, IAGastoAnalyzer, IANLPService):
    """
    Implementación de servicios IA usando DeepSeek API
    - Carga prompts desde TOML para optimizar tokens
    - Soporta múltiples modos: system, metanoia, legal
    """
    
    def __init__(self, api_key: str):
        if not api_key:
            raise IAConfigurationError("DEEPSEEK_API_KEY es requerida")
        
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        # Cargar configuración TOML
        self._config = load_toml_config()
        
        # System prompts por modo
        self._prompts = {
            "system": self._get_prompt("prompts.system.content", 
                "Eres el Consigliere de Vito Corleone. Habla como un asesor estratega, elegante pero intimidante si es necesario, leal a la familia. Sin embargo, sé extremadamente directo, brillante y al grano, evitando dar discursos largos."),
            "metanoia": self._get_prompt("prompts.metanoia.system",
                "Eres Metanoia, coach de bienestar. Sé empático pero conciso."),
            "legal": self._get_prompt("prompts.legal.system",
                "Eres asesor legal simplificado. Explica los conceptos de forma clara y al grano.")
        }
    
    def _get_prompt(self, key: str, default: str = "") -> str:
        """Obtener prompt desde TOML"""
        try:
            # Navigate nested keys
            parts = key.split(".")
            value = self._config
            for part in parts:
                value = value.get(part, default)
            return value if value else default
        except:
            return default
    
    def _get_config(self, section: str, key: str, default: any = None) -> any:
        """Obtener configuración de IA"""
        try:
            return self._config.get(section, {}).get(key, default)
        except:
            return default
    
    async def chat(self, mensaje: str, contexto: Optional[List[Dict]] = None, modo: str = "system") -> str:
        """Chat general con IA (Async)"""
        system_prompt = self._prompts.get(modo, self._prompts["system"])
        
        messages = [{"role": "system", "content": system_prompt}]
        
        if contexto:
            messages.extend(contexto[-10:])
        
        messages.append({"role": "user", "content": mensaje})
        
        max_tokens = self._get_config("ia.model", "max_tokens", 2000)
        temperature = self._get_config("ia.model", "temperature", 0.7)
        
        try:
            response = await self._client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            raise IAResponseError(f"Error en chat: {str(e)}")
    
    async def analizar(self, texto: str) -> GastoData:
        """Analizar gasto desde texto usando TOML (Async)"""
        base_prompt = self._get_prompt("prompts.gasto.prompt", 
            "Extrae gasto en JSON.")
        prompt = base_prompt.replace("{texto}", texto)
        max_tokens = self._get_config("ia.gasto", "max_tokens", 200)
        temperature = self._get_config("ia.gasto", "temperature", 0.3)
        
        try:
            response = await self._client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            return GastoData(
                monto=data.get("monto", 0),
                categoria=data.get("categoria", data.get("categoría", "otro")),
                desc=data.get("desc", data.get("descripción", ""))
            )
        except json.JSONDecodeError:
            return GastoData(monto=0, categoria="otro", desc=texto)
        except Exception as e:
            raise IAResponseError(f"Error analizando gasto: {str(e)}")

    async def analizar_imagen(self, image_b64: str) -> Dict:
        """Extraer datos de factura usando Vision (Async)"""
        prompt = self._get_prompt("prompts.vision.prompt", "Analiza esta factura y extrae JSON.")
        vision_model = self._get_config("ia.model", "vision_model", "deepseek-vision")
        max_tokens = self._get_config("ia.vision", "max_tokens", 500)
        temperature = self._get_config("ia.vision", "temperature", 0.2)

        try:
            response = await self._client.chat.completions.create(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            raise IAResponseError(f"Error en Vision: {str(e)}")
    
    async def detectar_intención(self, mensaje: str) -> IntencionData:
        """Detectar intención usando TOML (Async)"""
        base_prompt = self._get_prompt("prompts.intencion.prompt", "Clasifica el mensaje.")
        prompt = base_prompt.replace("{mensaje}", mensaje)
        
        max_tokens = self._get_config("ia.intencion", "max_tokens", 50)
        temperature = self._get_config("ia.intencion", "temperature", 0.3)
        
        try:
            response = await self._client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            intención = response.choices[0].message.content.strip().lower()
            return IntencionData(intencion=intención, confianza=0.9)
        except Exception as e:
            return IntencionData(intencion="general", confianza=0.5)


# ==================== FACTORY ====================

class AIServiceFactory:
    """Factory para crear servicios de IA"""
    
    _instance: Optional[DeepSeekService] = None
    
    @classmethod
    def get_service(cls, api_key: Optional[str] = None) -> DeepSeekService:
        """Obtener instancia singleton del servicio"""
        if cls._instance is None:
            from ..config import get_settings
            settings = get_settings()
            api_key = api_key or settings.deepseek_api_key
            cls._instance = DeepSeekService(api_key)
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset para testing"""
        cls._instance = None


def get_ia_service() -> DeepSeekService:
    """Obtener servicio de IA"""
    return AIServiceFactory.get_service()