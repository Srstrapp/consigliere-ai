"""
Servicio de WhatsApp - Evolution API
Soporta texto, voz, imágenes, video, documentos
"""

import httpx
from typing import Optional, Dict, Any, List
from enum import Enum
import base64
import json


class WhatsAppError(Exception):
    """Error en servicio de WhatsApp"""
    pass


class WhatsAppMessageType(Enum):
    """Tipos de mensaje soportados"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    VCARD = "vcard"


class WhatsAppService:
    """
    Servicio de WhatsApp usando Evolution API
    Reference: https://github.com/ atendai/evolution-api
    """
    
    def __init__(self, base_url: str, api_key: str):
        """
        Inicializar servicio de WhatsApp
        
        Args:
            base_url: URL de la Evolution API (ej: http://localhost:8080)
            api_key: API key de la Evolution API
        """
        if not base_url or not api_key:
            raise WhatsAppError("base_url y api_key son requeridos")
        
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            headers={
                "apikey": api_key,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def send_text(self, phone: str, text: str) -> Dict:
        """Enviar mensaje de texto"""
        payload = {
            "number": phone,
            "text": text
        }
        return await self._post("/message/sendText/instance", payload)
    
    async def send_image(self, phone: str, image_url: str, caption: Optional[str] = None) -> Dict:
        """Enviar imagen"""
        payload = {
            "number": phone,
            "image": {"url": image_url},
            "caption": caption
        }
        return await self._post("/message/sendImage/instance", payload)
    
    async def send_audio(self, phone: str, audio_url: str) -> Dict:
        """Enviar audio (nota de voz)"""
        payload = {
            "number": phone,
            "audio": {"url": audio_url}
        }
        return await self._post("/message/sendAudio/instance", payload)
    
    async def send_video(self, phone: str, video_url: str, caption: Optional[str] = None) -> Dict:
        """Enviar video"""
        payload = {
            "number": phone,
            "video": {"url": video_url},
            "caption": caption
        }
        return await self._post("/message/sendVideo/instance", payload)
    
    async def send_document(self, phone: str, document_url: str, filename: str) -> Dict:
        """Enviar documento"""
        payload = {
            "number": phone,
            "document": {"url": document_url, "fileName": filename}
        }
        return await self._post("/message/sendDocument/instance", payload)
    
    async def send_list(self, phone: str, title: str, text: str, buttons: List[Dict]) -> Dict:
        """Enviar mensaje con botones interactivos"""
        payload = {
            "number": phone,
            "title": title,
            "text": text,
            "buttons": buttons
        }
        return await self._post("/message/sendList/instance", payload)
    
    async def get_instance_info(self) -> Dict:
        """Obtener información de la instancia"""
        return await self._get("/instance/instance")
    
    async def get_qr_code(self) -> Optional[Dict]:
        """Obtener QR code para conectar"""
        return await self._get("/instance/connect")
    
    async def download_media(self, message_id: str) -> bytes:
        """Descargar medios de un mensaje"""
        url = f"{self._base_url}/message/download/{message_id}"
        response = await self._client.get(url)
        return response.content
    
    async def _post(self, endpoint: str, data: Dict) -> Dict:
        """Método POST interno"""
        url = f"{self._base_url}{endpoint}"
        response = await self._client.post(url, json=data)
        
        if response.status_code >= 400:
            raise WhatsAppError(f"Error {response.status_code}: {response.text}")
        
        return response.json()
    
    async def _get(self, endpoint: str) -> Dict:
        """Método GET interno"""
        url = f"{self._base_url}{endpoint}"
        response = await self._client.get(url)
        
        if response.status_code >= 400:
            raise WhatsAppError(f"Error {response.status_code}: {response.text}")
        
        return response.json()
    
    async def close(self):
        """Cerrar cliente HTTP"""
        await self._client.aclose()


# ==================== HANDLER DE MENSAJES ====================

class WhatsAppMessageParser:
    """Parser de mensajes entrantes de WhatsApp"""
    
    @staticmethod
    def parse_message(data: Dict) -> Dict:
        """Parsear mensaje entrante"""
        message_data = data.get("message", {})
        
        # Extraer número
        key = data.get("key", {})
        remote_jid = key.get("remoteJid", "")
        phone = remote_jid.split("@")[0] if remote_jid else ""
        
        # Extraer tipo de mensaje y contenido
        msg_type = ""
        content = ""
        
        if "conversation" in message_data:
            msg_type = "text"
            content = message_data["conversation"]
        elif "extendedTextMessage" in message_data:
            msg_type = "text"
            content = message_data["extendedTextMessage"].get("text", "")
        elif "imageMessage" in message_data:
            msg_type = "image"
            content = message_data["imageMessage"].get("caption", "")
        elif "audioMessage" in message_data:
            msg_type = "audio"
            content = "nota_de_voz"
        elif "videoMessage" in message_data:
            msg_type = "video"
            content = message_data["videoMessage"].get("caption", "")
        elif "documentMessage" in message_data:
            msg_type = "document"
            content = message_data["documentMessage"].get("fileName", "")
        elif "stickerMessage" in message_data:
            msg_type = "sticker"
            content = "sticker"
        
        return {
            "phone": phone,
            "type": msg_type,
            "content": content,
            "message_id": key.get("id", ""),
            "from_me": key.get("fromMe", False),
            "push_name": data.get("pushName", "")
        }


# ==================== FACTORY ====================

class WhatsAppServiceFactory:
    """Factory para servicio de WhatsApp"""
    
    _instance: Optional[WhatsAppService] = None
    
    @classmethod
    def get_service(cls) -> WhatsAppService:
        if cls._instance is None:
            from ..config import get_settings
            settings = get_settings()
            
            if not settings.whatsapp_api_url or not settings.whatsapp_api_key:
                raise WhatsAppError("WHATSAPP_API_URL y WHATSAPP_API_KEY son requeridos")
            
            cls._instance = WhatsAppService(
                base_url=settings.whatsapp_api_url,
                api_key=settings.whatsapp_api_key
            )
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        cls._instance = None


def get_whatsapp_service() -> WhatsAppService:
    """Obtener servicio de WhatsApp"""
    return WhatsAppServiceFactory.get_service()