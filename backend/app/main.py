"""
Consigliere AI - FastAPI Entry Point
Arquitectura limpia: Ports & Adapters
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging
import os

from .config import get_settings
from .services.database import UserRepository, ExpenseRepository, GoalRepository
from .services.whatsapp import WhatsAppMessageParser, WhatsAppServiceFactory, WhatsAppError


settings = get_settings()
logger = logging.getLogger(__name__)


# ==================== LIFECYCLE ====================

bot_app = None
whatsapp_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle - iniciar/stop servicios externos"""
    global bot_app, whatsapp_service
    
    # TELEGRAM - detectar si es Railway o local
    if settings.telegram_bot_token:
        try:
            # Railway tiene estas variables de entorno
            is_railway = bool(os.getenv('RAILWAY_PUBLIC_DOMAIN') or os.getenv('RAILWAY_STATIC_URL'))
            
            from telegram import Bot
            from telegram.error import TelegramError
            
            if is_railway:
                # Railway: usar webhook
                bot = Bot(token=settings.telegram_bot_token)
                if os.getenv('RAILWAY_STATIC_URL'):
                    webhook_url = f"https://{os.getenv('RAILWAY_STATIC_URL')}/webhook/telegram"
                else:
                    webhook_url = f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN')}/webhook/telegram"
                
                try:
                    await bot.set_webhook(url=webhook_url)
                    logger.info(f"✅ Telegram webhook configurado: {webhook_url}")
                except TelegramError as e:
                    logger.warning(f"⚠️ Error configurando webhook: {e}")
            else:
                # Local: usar polling
                from .services.telegram import create_bot_application
                bot_app = create_bot_application()
                await bot_app.initialize()
                await bot_app.start()
                asyncio.create_task(bot_app.updater.start_polling(drop_pending_updates=True))
                logger.info("✅ Telegram Bot iniciado (polling)")
                
        except Exception as e:
            logger.warning(f"⚠️ Telegram Bot no iniciado: {e}")
    
    # Iniciar WhatsApp (Evolution API)
    if settings.whatsapp_api_url and settings.whatsapp_api_key:
        try:
            whatsapp_service = WhatsAppServiceFactory.get_service()
            logger.info("✅ WhatsApp service iniciado")
        except WhatsAppError as e:
            logger.warning(f"⚠️ WhatsApp no iniciado: {e}")
        except Exception as e:
            logger.warning(f"⚠️ WhatsApp error: {e}")
    
    yield
    
    # Shutdown
    if bot_app:
        try:
            await bot_app.stop()
            await bot_app.updater.stop()
            logger.info("🛑 Telegram Bot detenido")
        except Exception as e:
            logger.warning(f"⚠️ Error deteniendo Telegram: {e}")
    
    if whatsapp_service:
        await whatsapp_service.close()
        logger.info("🛑 WhatsApp service detenido")


# ==================== APP ====================

app = FastAPI(
    title="Consigliere AI API",
    description="Backend - Asistencia IA omnicanal: Finanzas, Mente, Ley",
    version="2.0.0",
    lifespan=lifespan
)

# CORS - permitir PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== HEALTH ENDPOINTS ====================

@app.get("/")
async def root():
    """Health check básico"""
    return {
        "status": "✅ Consigliere AI online",
        "version": "2.0.0",
        "channels": {
            "telegram": "active" if bot_app else "inactive",
            "whatsapp": "active" if whatsapp_service else "inactive"
        }
    }


@app.get("/health")
async def health():
    """Health check detallado"""
    return {
        "status": "healthy",
        "telegram": "connected" if bot_app else "disconnected",
        "whatsapp": "connected" if whatsapp_service else "disconnected",
        "deepseek": "configured" if settings.deepseek_api_key else "pending",
        "supabase": "configured" if settings.supabase_anon_key else "pending"
    }


# ==================== API ENDPOINTS ====================

@app.get("/api/usuario/{telegram_id}")
async def get_usuario(telegram_id: int):
    """Obtener usuario por Telegram ID"""
    user = UserRepository.get_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@app.get("/api/{telegram_id}/gastos")
async def get_gastos(telegram_id: int, limit: int = 10):
    """Obtener gastos del usuario"""
    user = UserRepository.get_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    gastos = ExpenseRepository.get_by_user(user["id"], limit)
    return {"gastos": gastos}


@app.get("/api/{telegram_id}/gastos/resumen")
async def get_resumen_gastos(telegram_id: int):
    """Resumen de gastos por categoría"""
    user = UserRepository.get_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return ExpenseRepository.get_summary(user["id"])


@app.get("/api/{telegram_id}/metas")
async def get_metas(telegram_id: int):
    """Obtener metas del usuario"""
    user = UserRepository.get_by_telegram(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    metas = GoalRepository.get_by_user(user["id"])
    return {"metas": metas}


# ==================== EVOLUTION BOT ENDPOINT ====================
# Este endpoint es llamado por Evolution Bot cuando el usuario envía un mensaje
# Debe responder en formato JSON con el campo "message"

@app.post("/bot/evolution")
async def evolution_bot(payload: dict):
    """
    Endpoint para Evolution Bot
    Evolution Bot envía los mensajes aquí y espera respuesta en formato JSON
    """
    try:
        # Parsear mensaje desde Evolution Bot
        # El payload tiene variables automáticas: remoteJid, pushName, instanceName, etc.
        # Y el mensaje del usuario viene en el body
        
        # Obtener datos del usuario
        remote_jid = payload.get("remoteJid", "")
        push_name = payload.get("pushName", "Usuario WhatsApp")
        
        # El mensaje puede venir en diferentes formatos según la config del bot
        mensaje_texto = payload.get("message", "") or payload.get("text", "") or payload.get("content", "")
        
        if not mensaje_texto:
            # Si viene en formato raw, puede venir como parte del body
            # Buscar en las variables de entrada
            inputs = payload.get("inputs", {})
            mensaje_texto = inputs.get("message", "") or inputs.get("text", "")
        
        # Limpiar número de teléfono del JID (sacar @s.whatsapp.net)
        phone = remote_jid.split("@")[0] if remote_jid else ""
        
        if not mensaje_texto:
            logger.warning(f"⚠️ Evolution Bot: mensaje vacío de {phone}")
            return {"message": ""}
        
        logger.info(f"📱 Evolution Bot [{phone}]: {mensaje_texto[:50]}")
        
        # Procesar con IA (mismo flujo que WhatsApp webhook)
        from app.services.deepseek import AIServiceFactory, IAResponseError
        from app.services.database import UserRepository, ConversationRepository
        
        ia_service = AIServiceFactory.get_service()
        
        # Detectar intención
        try:
            intención = ia_service.detectar_intención(mensaje_texto).intencion
        except IAResponseError:
            intención = "general"
        
        # Mapping intención a dominio
        from app.services.telegram import INTENCION_A_DOMINIO
        dominio = INTENCION_A_DOMINIO.get(intención, "general")
        
        # Obtener o crear usuario
        db_user = UserRepository.get_by_whatsapp(phone)
        if not db_user:
            db_user = UserRepository.create_by_phone(phone, push_name)
        
        # Obtener contexto filtrado por dominio
        from app.services.database import ConversationRepository as ConvRepo
        conv = ConvRepo.get_by_dominio(db_user["id"], dominio)
        contexto = conv["messages"] if conv else []
        
        # Procesar según intención
        if intención == "gasto":
            from app.services.deepseek import GastoData
            datos: GastoData = ia_service.analizar(mensaje_texto)
            if datos.monto > 0:
                from app.services.database import ExpenseRepository
                ExpenseRepository.create(db_user["id"], datos.monto, datos.categoria, datos.desc or mensaje_texto)
                respuesta = f"✅ *Gasto registrado:*\n\n💰 ${datos.monto:.2f}\n📂 {datos.categoria}"
            else:
                respuesta = "No pude entender el monto. Probá con algo como 'gasté 5000 en comida'"
        elif intención == "meta":
            import re
            monto_match = re.search(r'(\d+(?:\.\d+)?)', mensaje_texto)
            if monto_match:
                monto = float(monto_match.group(1))
                nombre = mensaje_texto.replace(monto_match.group(1), "").strip()[:50] or "Mi meta"
                from app.services.database import GoalRepository
                GoalRepository.create(db_user["id"], nombre, monto)
                respuesta = f"🎯 *Meta creada!*\n\nObjetivo: {nombre}\nMonto: ${monto:.2f}"
            else:
                respuesta = "Para crear una meta, indicá el monto. Ej: 'Quiero ahorrar 50000 para un carro'"
        elif intención == "presupuesto":
            respuesta = "Para ver tu presupuesto usá /presupuesto\nPara cambiarlo, escribí algo como 'Quiero poner mi presupuesto en 2000'"
        else:
            # Chat general con contexto filtrado por dominio
            try:
                # Seleccionar modo según dominio
                modo = "metanoia" if dominio == "metanoia" else "legal" if dominio == "legal" else "system"
                respuesta = ia_service.chat(mensaje_texto, contexto, modo=modo)
            except IAResponseError:
                respuesta = "Disculpa, tuve un problema. Intentá de nuevo."
            
            # Guardar conversación con dominio
            contexto.append({"role": "user", "content": mensaje_texto})
            contexto.append({"role": "assistant", "content": respuesta})
            ConvRepo.save(db_user["id"], contexto[-10:], dominio=dominio)
        
        # Evolution Bot espera respuesta en campo "message"
        return {"message": respuesta}
        
    except Exception as e:
        logger.error(f"Error en Evolution Bot: {e}")
        return {"message": "Disculpa, tuve un problema. Intentá de nuevo."}


# ==================== WEBHOOKS ====================

@app.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """Webhook para recibir mensajes de Telegram"""
    try:
        from telegram import Update
        from telegram.ext import ContextTypes
        
        # Crear objeto Update desde el payload del webhook
        update_obj = Update.de_json(update, Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None)
        
        if not update_obj.message:
            return {"status": "ignored"}
        
        # Importar y usar el MessageRouter
        from app.services.telegram import MessageRouter
        
        router = MessageRouter()
        
        # Crear un contextofake
        class FakeContext:
            pass
        
        # Procesar el mensaje
        await router.process(update_obj, FakeContext())
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en webhook de Telegram: {e}")
        return {"status": "error", "detail": str(e)}


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(payload: dict):
    """Webhook para WhatsApp (Evolution API)"""
    try:
        message = WhatsAppMessageParser.parse_message(payload)
        
        # Ignorar mensajes enviados por el bot
        if message.get("from_me"):
            return {"status": "ignored"}
        
        # Solo procesar mensajes de texto por ahora
        if message["type"] != "text":
            logger.info(f"📱 WhatsApp: mensaje tipo {message['type']} ignorado")
            return {"status": "ignored"}
        
        # Importar el MessageRouter y procesar
        from app.services.telegram import MessageRouter, PlatformMessage
        
        # Crear mensaje abstracto
        platform_msg = PlatformMessage(
            platform="whatsapp",
            user_id=message["phone"],
            user_name=message.get("push_name", "Usuario WhatsApp"),
            text=message["content"]
        )
        
        # Procesar con el router (pero necesitamos adaptarlo)
        # Por ahora usamos el mismo router pero con un wrapper
        router = MessageRouter()
        
        # Crear un handler que-use el WhatsApp service para responder
        from app.services.whatsapp import WhatsAppServiceFactory
        wa_service = WhatsAppServiceFactory.get_service()
        
        # Procesar intención
        try:
            from app.services.deepseek import AIServiceFactory, IAResponseError
            ia_service = AIServiceFactory.get_service()
            intención = ia_service.detectar_intención(message["content"]).intencion
        except IAResponseError:
            intención = "general"
        
        # Procesar según intención
        # Por cada tipo de intención, llamamos al handler correspondiente
        db_user = None
        if intención in ["gasto", "meta", "presupuesto"]:
            # Necesitamos usuario en DB
            from app.services.database import UserRepository
            db_user = UserRepository.get_by_whatsapp(message["phone"])
            if not db_user:
                db_user = UserRepository.create_by_phone(
                    message["phone"], 
                    message.get("push_name", "Usuario WhatsApp")
                )
        
        # Ejecutar el handler
        if intención == "gasto":
            from app.services.deepseek import GastoData
            datos: GastoData = ia_service.analizar(message["content"])
            if datos.monto > 0:
                from app.services.database import ExpenseRepository
                ExpenseRepository.create(db_user["id"], datos.monto, datos.categoria, datos.desc or message["content"])
                respuesta = f"✅ *Gasto registrado:*\n\n💰 ${datos.monto:.2f}\n📂 {datos.categoria}"
            else:
                respuesta = "No pude entender el monto. Probá con algo como 'gasté 5000 en comida'"
        elif intención == "meta":
            import re
            monto_match = re.search(r'(\d+(?:\.\d+)?)', message["content"])
            if monto_match:
                monto = float(monto_match.group(1))
                nombre = message["content"].replace(monto_match.group(1), "").strip()[:50] or "Mi meta"
                from app.services.database import GoalRepository
                GoalRepository.create(db_user["id"], nombre, monto)
                respuesta = f"🎯 *Meta creada!*\n\nObjetivo: {nombre}\nMonto: ${monto:.2f}"
            else:
                respuesta = "Para crear una meta, indicá el monto. Ej: 'Quiero ahorrar 50000 para un carro'"
        elif intención == "presupuesto":
            respuesta = "Para ver tu presupuesto usá /presupuesto\nPara cambiarlo, escribí algo como 'Quiero poner mi presupuesto en 2000'"
        else:
            # General - usar chat de IA
            from app.services.database import ConversationRepository
            contexto = ConversationRepository.get_last(db_user["id"] if db_user else 0)
            try:
                respuesta = ia_service.chat(message["content"], contexto, modo="system")
            except IAResponseError:
                respuesta = "Disculpa, tuve un problema. Intentá de nuevo."
            
            # Guardar conversación
            if db_user:
                contexto.append({"role": "user", "content": message["content"]})
                contexto.append({"role": "assistant", "content": respuesta})
                ConversationRepository.save(db_user["id"], contexto[-10:])
        
        # Enviar respuesta por WhatsApp
        await wa_service.send_text(message["phone"], respuesta)
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error en webhook WhatsApp: {e}")
        return {"status": "error", "detail": str(e)}
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error en webhook WhatsApp: {e}")
        return {"status": "error", "detail": str(e)}


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)