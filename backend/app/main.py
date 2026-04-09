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
    
    # TELEGRAM - si existe RAILWAY_STATIC_URL, usar webhook; si no, polling (local)
    if settings.telegram_bot_token:
        try:
            railway_url = os.getenv('RAILWAY_STATIC_URL')
            logger.info(f"🔍 RAILWAY_STATIC_URL: {railway_url}")
            
            from telegram import Bot
            from telegram.error import TelegramError
            
            if railway_url:
                # Railway: usar webhook - NO iniciar polling nunca
                webhook_url = f"https://{railway_url}/webhook/telegram"
                bot = Bot(token=settings.telegram_bot_token)
                
                # Eliminar cualquier webhook anterior
                try:
                    await bot.delete_webhook()
                    logger.info("🗑️ Webhook anterior eliminado")
                except:
                    pass
                
                await bot.set_webhook(url=webhook_url)
                logger.info(f"✅ Telegram webhook configurado: {webhook_url}")
                logger.info("⚠️ No se inicia polling en Railway (solo webhook)")
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

# Routers
from .routers import auth as auth_router
app.include_router(auth_router.router)


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
    """Webhook para recibir mensajes de Telegram - Usa Skill Manager"""
    try:
        from telegram import Update, Bot
        
        # Crear objeto Update desde el payload del webhook
        update_obj = Update.de_json(update, Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None)
        
        if not update_obj.message:
            return {"status": "ignored"}
        
        mensaje = update_obj.message.text or ""
        user_id_telegram = update_obj.message.from_user.id
        
        # Obtener o crear usuario en Supabase
        from app.services.database import UserRepository
        db_user = UserRepository.get_by_telegram(user_id_telegram)
        es_nuevo = db_user is None
        
        if not db_user:
            nombre = update_obj.message.from_user.first_name or "Usuario"
            db_user = UserRepository.create(user_id_telegram, nombre)
        
        # Detectar comandos especiales
        if mensaje.strip().lower() in ["/start", "start", "/menu", "/ayuda", "/help"]:
            # Generar mensaje de bienvenida según si es nuevo o no
            if es_nuevo or not db_user.get("auth_user_id"):
                respuesta = """¡Hola! Soy Consiglieri, tu asistente personal para poner en orden tus finanzas y bienestar. 👋

Para arrancar con todo y que pueda llevar tus registros, necesito que te registres en el dashboard:
https://consigliere.up.railway.app/dashboard

Una vez registrado, podés escribirme cosas como:
- 'Gasté 500 en comida' 🍔
- 'Quiero ahorrar 2000 para un viaje' ✈️
- 'Me siento un poco estresado' 🧘‍♂️

¡Te espero allá para empezar!"""
            else:
                presupuesto = db_user.get("presupuesto_mensual", 1000)
                respuesta = f"¡Qué bueno verte de nuevo! 👋\n\nTu presupuesto actual es de ${presupuesto} al mes. ¿En qué te puedo ayudar hoy? Podés registrar un gasto, una meta o contarme cómo vas de energía."
            
            # Enviar respuesta
            from telegram import Bot
            bot = Bot(token=settings.telegram_bot_token)
            await bot.send_message(chat_id=update_obj.message.chat_id, text=respuesta)
            return {"status": "ok"}
        
        # Si es usuario nuevo y no tiene auth, recordarle el registro
        tiene_auth = db_user.get("auth_user_id") is not None if db_user else False
        if (es_nuevo or not tiene_auth) and len(mensaje) > 5:
            respuesta = "¡Veo que todavía no te registraste! 😅 Para que pueda guardar tus gastos y ayudarte con tus metas, pasate por acá:\n\nhttps://consigliere.up.railway.app/dashboard\n\n¡Es un toque y ya quedamos conectados!"
            
            from telegram import Bot
            bot = Bot(token=settings.telegram_bot_token)
            await bot.send_message(chat_id=update_obj.message.chat_id, text=respuesta)
            return {"status": "ok"}
        
        # Usar Skill Manager para procesar el mensaje
        from app.skills import get_skill_manager
        from app.services.execution_engine import get_execution_engine
        
        engine = get_execution_engine()
        manager = get_skill_manager(engine)
        
        # Ejecutar skill (AHORA ES ASYNC)
        result = await manager.execute(mensaje, db_user["id"])
        
        # Determinar respuesta
        if result.get("message") == "CONTINUAR_CON_IA":
            # Pasar a IA para respuesta general
            from app.services.deepseek import AIServiceFactory
            from app.services.database import ConversationRepository
            
            ia_service = AIServiceFactory.get_service()
            contexto = ConversationRepository.get_last(db_user["id"])
            
            try:
                respuesta = await ia_service.chat(mensaje, contexto, modo="system")
            except Exception as e:
                logger.error(f"Error en chat IA: {e}")
                respuesta = "Disculpa, tuve un problema. Intentá de nuevo."
            
            # Guardar conversación
            contexto.append({"role": "user", "content": mensaje})
            contexto.append({"role": "assistant", "content": respuesta})
            ConversationRepository.save(db_user["id"], contexto[-10:])
        else:
            # Usar respuesta de la skill
            respuesta = result.get("message", "Listo")
        
        # Enviar respuesta por Telegram
        from telegram import Bot
        bot = Bot(token=settings.telegram_bot_token)
        await bot.send_message(chat_id=update_obj.message.chat_id, text=respuesta)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error en webhook de Telegram: {e}")
        return {"status": "error", "detail": str(e)}


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(payload: dict):
    """Webhook para WhatsApp (Evolution API) - Usa Skill Manager"""
    try:
        message = WhatsAppMessageParser.parse_message(payload)
        
        # Ignorar mensajes enviados por el bot
        if message.get("from_me"):
            return {"status": "ignored"}
        
        # Solo procesar mensajes de texto por ahora
        if message["type"] != "text":
            logger.info(f"📱 WhatsApp: mensaje tipo {message['type']} ignorado")
            return {"status": "ignored"}
        
        # Obtener o crear usuario
        from app.services.database import UserRepository
        db_user = UserRepository.get_by_whatsapp(message["phone"])
        if not db_user:
            db_user = UserRepository.create_by_phone(
                message["phone"], 
                message.get("push_name", "Usuario WhatsApp")
            )
        
        # Usar Skill Manager para procesar el mensaje
        from app.skills import get_skill_manager
        from app.services.execution_engine import get_execution_engine
        
        engine = get_execution_engine()
        manager = get_skill_manager(engine)
        
        # Ejecutar skill (AHORA ES ASYNC)
        result = await manager.execute(message["content"], db_user["id"])
        
        # Determinar respuesta
        if result.get("message") == "CONTINUAR_CON_IA":
            # Pasar a IA para respuesta general
            from app.services.deepseek import AIServiceFactory
            from app.services.database import ConversationRepository
            
            ia_service = AIServiceFactory.get_service()
            contexto = ConversationRepository.get_last(db_user["id"])
            
            try:
                respuesta = await ia_service.chat(message["content"], contexto, modo="system")
            except Exception as e:
                logger.error(f"Error en chat IA WhatsApp: {e}")
                respuesta = "Disculpa, tuve un problema. Intentá de nuevo."
            
            # Guardar conversación
            contexto.append({"role": "user", "content": message["content"]})
            contexto.append({"role": "assistant", "content": respuesta})
            ConversationRepository.save(db_user["id"], contexto[-10:])
        else:
            # Usar respuesta de la skill
            respuesta = result.get("message", "✅ Listo")
        
        # Enviar respuesta por WhatsApp
        from app.services.whatsapp import WhatsAppServiceFactory
        wa_service = WhatsAppServiceFactory.get_service()
        await wa_service.send_text(message["phone"], respuesta)
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error en webhook WhatsApp: {e}")
        return {"status": "error", "detail": str(e)}


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)