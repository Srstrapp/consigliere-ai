"""
Router de autenticación — valida magic link tokens del bot de Telegram
"""

from fastapi import APIRouter, HTTPException, Query
from ..services.database import LoginTokenRepository


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

    return {
        "success": True,
        "nombre": user.get("nombre"),
        "telegram_id": user.get("telegram_id"),
        "presupuesto_mensual": user.get("presupuesto_mensual", 0),
        # access_token y refresh_token se omiten acá porque el auth es via Supabase Auth
        # en el futuro: si el user tiene auth_user_id, generar un magic link de Supabase
        "access_token": None,
        "refresh_token": None,
    }
