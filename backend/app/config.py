"""
Configuración de variables de entorno
Todas las credenciales vienen del archivo .env
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Settings de la aplicación - carga desde .env"""
    
    # Supabase - valores por defecto vacíos (se cargan del .env)
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    
    # DeepSeek
    deepseek_api_key: Optional[str] = None
    
    # Telegram Bot
    telegram_bot_token: Optional[str] = None
    
    # WhatsApp - Evolution API
    whatsapp_api_url: Optional[str] = None
    whatsapp_api_key: Optional[str] = None
    
    # App
    app_name: str = "Consigliere AI"
    debug: bool = True
    dashboard_url: str = "http://localhost:4200"
    
    # Supabase Service Role Key (para crear auth users desde el bot)
    supabase_service_role_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Ignorar campos extra
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Instancia singleton de settings"""
    return Settings()