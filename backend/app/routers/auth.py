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
        # Usamos service instance para bypass RLS y asegurar limpieza de duplicados
        from ..services.database import SupabaseClient
        supabase = SupabaseClient.get_service_instance()
        
        # Verificar el usuario (esto sí lo hacemos con el token del usuario para seguridad)
        auth_client = SupabaseClient.get_instance()
        user_response = auth_client.auth.get_user(auth_header.split(" ")[1] if " " in auth_header else auth_header)
        
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Sesión inválida")
        
        auth_user_id = user_response.user.id
        
        # Vincular el auth_user_id con el usuario de Telegram
        # MERGE Atómico:
        db_user_telegram = UserRepository.get_by_telegram(int(telegram_id))
        
        if db_user_telegram:
            # Transferir el auth_user_id a la cuenta de telegram existente
            supabase.table("users").update({
                "auth_user_id": auth_user_id,
                "email": user_response.user.email
            }).eq("id", db_user_telegram["id"]).execute()
            
            # Limpiar: Borrar cualquier fila duplicada que pudiera haber creado un trigger residual
            # (con el service_role esto no falla por RLS)
            supabase.table("users").delete().eq("auth_user_id", auth_user_id).neq("id", db_user_telegram["id"]).execute()
        else:
            # Si no existe en telegram, simplemente nos aseguramos de que el registro web tenga los datos
            supabase.table("users").update({
                "nombre": user_response.user.user_metadata.get("full_name", "Usuario")
            }).eq("auth_user_id", auth_user_id).execute()

        return {"success": True, "message": "Cuentas vinculadas"}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
