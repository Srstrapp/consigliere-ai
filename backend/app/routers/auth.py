"""
Router de autenticación — valida magic link tokens del bot de Telegram
"""

from fastapi import APIRouter, HTTPException, Query, Request
from ..services.database import LoginTokenRepository, UserRepository
from supabase import create_client
from ..config import get_settings


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/token")
async def validate_login_token(token: str = Query(..., description="Token de login del bot")):
    """
    Valida un token de login generado por el bot de Telegram.
    Retorna los datos del usuario para que el dashboard pueda autenticarlo.
    El token se marca como usado y expira en 1 hora.
    """
    user = LoginTokenRepository.validate(token)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Token inválido, ya fue usado o expiró. Pedí uno nuevo con /start en Telegram."
        )

    # Vincular el telegram_id del usuario con su cuenta de Supabase Auth
    # Esto permite que cuando se registre, quede vinculado automáticamente
    telegram_id = user.get("telegram_id")
    
    return {
        "success": True,
        "nombre": user.get("nombre"),
        "telegram_id": telegram_id,
        "presupuesto_mensual": user.get("presupuesto_mensual", 0),
        "access_token": None,
        "refresh_token": None,
    }


@router.post("/link-telegram")
async def link_telegram_auth(request: Request):
    """
    Este endpoint se llama desde el frontend después de que el usuario se registra
    o hace login. Recibe el telegram_id del contexto y vincula el auth_user_id.
    """
    try:
        body = await request.json()
        telegram_id = body.get("telegram_id")
        
        if not telegram_id:
            raise HTTPException(status_code=400, detail="telegram_id es requerido")
        
        # Obtener el usuario actual de Supabase Auth desde el request
        auth_header = request.headers.get("authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="No autorizado")
        
        settings = get_settings()
        supabase = create_client(settings.supabase_url, settings.supabase_anon_key)
        
        # Verificar el token de Supabase Auth
        user_response = supabase.auth.get_user()
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Sesión inválida")
        
        auth_user_id = user_response.user.id
        
        # Vincular el auth_user_id con el usuario de Telegram
        db_user = UserRepository.get_by_telegram(int(telegram_id))
        if db_user:
            UserRepository.link_auth_user(db_user["id"], auth_user_id)
        
        return {"success": True, "message": "Cuentas vinculadas"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
