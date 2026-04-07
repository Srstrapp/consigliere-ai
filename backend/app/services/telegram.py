"""
Handlers del Bot - Command Pattern
Cada handler es una clase independiente siguiendo SRP
Usa TOML para prompts optimizados
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from .database import UserRepository, ExpenseRepository, GoalRepository, ConversationRepository
from .deepseek import AIServiceFactory, IAResponseError, GastoData
from .automation import BudgetAlert, ReminderScheduler, WellnessCheck, WeeklyReport, GoalTracker
from .whatsapp import WhatsAppService
from ..config import get_settings


settings = get_settings()


# ==================== BASE HANDLER ====================

class BaseHandler(ABC):
    """Clase base para handlers - SRP"""
    
    @abstractmethod
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ejecutar el handler"""
        pass
    
    async def reply(self, update: Update, text: str, parse_mode: str = "Markdown") -> None:
        """Helper para responder"""
        await update.message.reply_text(text, parse_mode=parse_mode)
    
    def get_db_user(self, telegram_id: int) -> Optional[dict]:
        """Helper para obtener usuario de DB"""
        return UserRepository.get_by_telegram(telegram_id)


# ==================== COMMAND HANDLERS ====================

class StartCommandHandler(BaseHandler):
    """Handler para /start - Bienvenida"""
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.reply(update, """🎯 *Consigliere AI*

Tu asistente omnicanal para:

💰 *Finanzas* - Registrá gastos, analizá tu dinero
🧠 *Metanoia* - Apoyo emocional y motivación  
⚖️ *Ley* - Consultas legales en lenguaje sencillo

¡Escribeme cualquier cosa y te ayudo! 🚀""")


class HelpCommandHandler(BaseHandler):
    """Handler para /help y /ayuda"""
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.reply(update, """📋 *Comandos disponibles:*

/start - Iniciar el bot
/gastos - Ver mis gastos recientes
/metas - Ver mis metas financieras
/bienestar - Check-in de bienestar (Metanoia)
/reporte - Ver reporte semanal
/presupuesto - Ver estado del presupuesto
/ayuda - Mostrar esta ayuda

También podés escribir normalmente y te ayudo!""")


class GastosCommandHandler(BaseHandler):
    """Handler para /gastos - Ver gastos"""
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        db_user = self.get_db_user(user.id)
        
        if not db_user:
            await self.reply(update, "No estás registrado aún. Escribí algo para empezar!")
            return
        
        gastos = ExpenseRepository.get_by_user(db_user["id"], limit=5)
        
        if not gastos:
            await self.reply(update, "No tenés gastos registrados aún.")
            return
        
        mensaje = "💰 *Tus últimos gastos:*\n\n"
        for g in gastos:
            mensaje += f"• {g['categoría']}: ${g['monto']:.2f} - {g.get('descripción', 'sin descripción')}\n"
        
        await self.reply(update, mensaje)


class MetasCommandHandler(BaseHandler):
    """Handler para /metas - Ver metas"""
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        db_user = self.get_db_user(user.id)
        
        if not db_user:
            await self.reply(update, "No estás registrado aún.")
            return
        
        metas = GoalRepository.get_by_user(db_user["id"])
        
        if not metas:
            await self.reply(update, "No tenés metas creadas. Escribí 'quiero ahorrar para un carro' y te ayudo!")
            return
        
        mensaje = "🎯 *Tus metas:*\n\n"
        for m in metas:
            progreso = (m["current_amount"] / m["meta_amount"]) * 100 if m["meta_amount"] > 0 else 0
            mensaje += f"• {m['nombre']}: ${m['current_amount']:.2f} / ${m['meta_amount']:.2f} ({progreso:.0f}%)\n"
        
        await self.reply(update, mensaje)


class MetanoiaCommandHandler(BaseHandler):
    """Handler para /bienestar - Check-in emocional"""
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        db_user = self.get_db_user(user.id)
        
        if not db_user:
            await self.reply(update, "No estás registrado. Escribí algo para empezar!")
            return
        
        mensaje = WellnessCheck.get_checkin_message()
        await self.reply(update, mensaje)


class ReporteCommandHandler(BaseHandler):
    """Handler para /reporte - Reporte semanal"""
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        db_user = self.get_db_user(user.id)
        
        if not db_user:
            await self.reply(update, "No estás registrado. Escribí algo para empezar!")
            return
        
        reporte = await WeeklyReport.generate_report(db_user["id"])
        await self.reply(update, reporte)


class PresupuestoCommandHandler(BaseHandler):
    """Handler para /presupuesto - Ver alertas de presupuesto"""
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        db_user = self.get_db_user(user.id)
        
        if not db_user:
            await self.reply(update, "No estás registrado. Escribí algo para empezar!")
            return
        
        # Obtener presupuesto del usuario desde la DB
        presupuesto = db_user.get("presupuesto_mensual")
        
        # Si no tiene presupuesto configurado, pedir que lo configure
        if presupuesto is None or presupuesto <= 0:
            await self.reply(update, 
                "💰 *Configura tu Presupuesto*\n\n"
                "No tienes un presupuesto mensual configurado.\n\n"
                "Para configurarlo, escribí algo como:\n"
                "'Quiero poner mi presupuesto en 2000' o 'mi presupuesto es 1500'\n\n"
                "Una vez configurado, podras usar /presupuesto para ver tu estado.")
            return
        
        alerta = await BudgetAlert.check_spending(db_user["id"], presupuesto)
        
        if alerta:
            await self.reply(update, alerta)
        else:
            # Calcular cuanto le queda
            gastos = ExpenseRepository.get_by_user(db_user["id"], limit=100)
            ahora = datetime.now()
            gastos_mes = [
                g for g in gastos 
                if g.get("fecha") and 
                datetime.strptime(str(g["fecha"]), "%Y-%m-%d").month == ahora.month and
                datetime.strptime(str(g["fecha"]), "%Y-%m-%d").year == ahora.year
            ]
            total_gastado = sum(g.get("monto", 0) for g in gastos_mes)
            restante = presupuesto - total_gastado
            
            await self.reply(update, 
                f"✅ *Presupuesto OK*\n\n"
                f"Llevas ${total_gastado:.2f} de ${presupuesto:.2f} este mes.\n"
                f"Te quedan ${restante:.2f} para el resto del mes.\n\n"
                f"Para ajustar tu presupuesto, escribí algo como:\n"
                f"'Quiero poner mi presupuesto en 2000' o 'cambia presupuesto a 1500'")


from datetime import datetime


# ==================== PLATFORM ABSTRACTION ====================

class PlatformMessage:
    """Abstracción de mensaje para cualquier plataforma (Telegram/WhatsApp)"""
    
    def __init__(self, platform: str, user_id: str, user_name: str, text: str):
        self.platform = platform
        self.user_id = user_id
        self.user_name = user_name
        self.text = text
    
    @property
    def effective_user(self):
        """Compatible con interfaz de Telegram Update"""
        class User:
            def __init__(self, uid, name):
                self.id = uid
                self.first_name = name
        return User(self.user_id, self.user_name)
    
    @property
    def message(self):
        """Compatible con interfaz de Telegram Update"""
        class Msg:
            def __init__(self, txt, platform, user_id, user_name, text):
                self.text = txt
                self._platform = platform
                self._user_id = user_id
                self._user_name = user_name
                self._text = text
            
            async def reply_text(self, text: str, parse_mode: str = "Markdown"):
                """Enviar respuesta al usuario"""
                if self._platform == "telegram":
                    # Telegram se maneja desde el handler original
                    pass
                elif self._platform == "whatsapp":
                    # Enviar por WhatsApp
                    try:
                        from .whatsapp import WhatsAppServiceFactory
                        wa_service = WhatsAppServiceFactory.get_service()
                        await wa_service.send_text(self._user_id, text)
                    except Exception as e:
                        print(f"Error enviando a WhatsApp: {e}")
        
        return Msg(self.text, self.platform, self.user_id, self.user_name, self.text)


# ==================== MESSAGE HANDLER ====================

# Mapping de intención a dominio para contexto aislado
INTENCION_A_DOMINIO = {
    "gasto": "finanzas",
    "meta": "finanzas",
    "presupuesto": "finanzas",
    "metanoia": "metanoia",
    "legal": "legal",
    "general": "general"
}


class MessageRouter:
    """
    Router de mensajes - Factory Pattern
    Decide qué handler usar según la intención
    Usa TOML para prompts optimizados
    """
    
    def __init__(self):
        self._ia_service = AIServiceFactory.get_service()
        self._handlers = {
            "gasto": self._handle_gasto,
            "meta": self._handle_meta,
            "metanoia": self._handle_metanoia,
            "legal": self._handle_legal,
            "presupuesto": self._handle_presupuesto,  # NEW
            "general": self._handle_general
        }
    
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Procesar mensaje entrante"""
        user = update.effective_user
        mensaje = update.message.text
        
        # Verificar si quiere cambiar presupuesto
        if self._es_cambio_presupuesto(mensaje):
            db_user = UserRepository.get_by_telegram(user.id)
            if not db_user:
                db_user = UserRepository.create(user.id, user.first_name)
            await self._handle_cambio_presupuesto(update, mensaje, db_user)
            return
        
        # 1. Asegurar usuario existe
        db_user = UserRepository.get_by_telegram(user.id)
        if not db_user:
            db_user = UserRepository.create(user.id, user.first_name)
        
        # 1.5. Si presupuesto = 0, preguntar presupuesto y guardar mensaje para procesar después
        if db_user.get("presupuesto_mensual", 0) == 0:
            # Guardar el mensaje original para procesar después
            UserRepository.set_mensaje_pendiente(db_user["id"], mensaje)
            await update.message.reply_text(
                "👋 ¡Hola! Primero necesito saber tu presupuesto mensual.\n\n"
                "¿Cuál es tu presupuesto mensual? (ej: 2000)"
            )
            return
        
        # 2. Detectar intención (usa TOML)
        try:
            intención = self._ia_service.detectar_intención(mensaje).intencion
        except IAResponseError:
            intención = "general"
        
        # 3. Obtener dominio basado en intención
        dominio = INTENCION_A_DOMINIO.get(intención, "general")
        
        # 4. Obtener contexto filtrado por dominio
        conv_result = ConversationRepository.get_by_dominio(db_user["id"], dominio)
        contexto = conv_result["messages"] if conv_result else []
        
        # 5. Ejecutar handler apropiado
        handler = self._handlers.get(intención, self._handlers["general"])
        
        # Pasar dominio y contexto como kwargs al handler
        await handler(update, mensaje, db_user, dominio=dominio, contexto=contexto)
    
    def _es_cambio_presupuesto(self, mensaje: str) -> bool:
        """Detectar si el mensaje es para cambiar presupuesto"""
        mensaje_lower = mensaje.lower()
        # Buscar palabras relacionadas con presupuesto Y un número
        palabras = ["presupuesto", "presupuesto", "presupuesto", "presupuesto", "cambiar", "ajustar", "setear", "poner"]
        numeros = any(c.isdigit() for c in mensaje)
        return any(p in mensaje_lower for p in palabras) and numeros
    
    async def _handle_gasto(self, update: Update, mensaje: str, db_user: dict, dominio: str = None, contexto: list = None) -> None:
        """Handler para registrar gasto - usa TOML"""
        try:
            datos: GastoData = self._ia_service.analizar(mensaje)
        except IAResponseError:
            await update.message.reply_text("No pude entender el gasto. Intenta de nuevo.")
            return
        
        if datos.monto > 0:
            ExpenseRepository.create(
                db_user["id"],
                datos.monto,
                datos.categoria,
                datos.desc or mensaje
            )
            respuesta = f"✅ *Gasto registrado:*\n\n💰 ${datos.monto:.2f}\n📂 {datos.categoria}"
        else:
            respuesta = "No pude entender el monto del gasto. Podés intentar con algo como 'gasté 5000 en comida'?"
        
        await update.message.reply_text(respuesta, parse_mode="Markdown")
    
    async def _handle_meta(self, update: Update, mensaje: str, db_user: dict, dominio: str = None, contexto: list = None) -> None:
        """Handler para crear meta"""
        import re
        
        monto_match = re.search(r'(\d+(?:\.\d+)?)', mensaje)
        if monto_match:
            monto = float(monto_match.group(1))
            nombre = mensaje.replace(monto_match.group(1), "").strip()[:50] or "Mi meta"
            
            GoalRepository.create(db_user["id"], nombre, monto)
            
            respuesta = f"🎯 *Meta creada!*\n\nObjetivo: {nombre}\nMonto: ${monto:.2f}"
        else:
            respuesta = "Para crear una meta, indicá el monto. Ej: 'Quiero ahorrar 50000 para un carro'"
        
        await update.message.reply_text(respuesta, parse_mode="Markdown")
    
    async def _handle_metanoia(self, update: Update, mensaje: str, db_user: dict, dominio: str = "metanoia", contexto: list = None) -> None:
        """Handler para apoyo emocional - usa TOML modo metanoia"""
        # Usar contexto pasado como parámetro
        if contexto is None:
            conv = ConversationRepository.get_by_dominio(db_user["id"], "metanoia")
            contexto = conv["messages"] if conv else []
        
        try:
            # Usa modo metanoia desde TOML
            respuesta = self._ia_service.chat(mensaje, contexto, modo="metanoia")
        except IAResponseError:
            respuesta = "Disculpa, tuve un problema. Intentá de nuevo."
        
        # Guardar conversación con dominio específico
        contexto.append({"role": "user", "content": mensaje})
        contexto.append({"role": "assistant", "content": respuesta})
        ConversationRepository.save(db_user["id"], contexto[-10:], dominio="metanoia")
        
        await update.message.reply_text(respuesta, parse_mode="Markdown")
    
    async def _handle_legal(self, update: Update, mensaje: str, db_user: dict, dominio: str = "legal", contexto: list = None) -> None:
        """Handler para consultas legales - usa TOML modo legal"""
        # Usar contexto pasado como parámetro
        if contexto is None:
            conv = ConversationRepository.get_by_dominio(db_user["id"], "legal")
            contexto = conv["messages"] if conv else []
        
        try:
            # Usa modo legal desde TOML
            respuesta = self._ia_service.chat(mensaje, contexto, modo="legal")
        except IAResponseError:
            respuesta = "Disculpa, tuve un problema con la consulta legal. Intentá de nuevo."
        
        # Guardar conversación con dominio específico
        contexto.append({"role": "user", "content": mensaje})
        contexto.append({"role": "assistant", "content": respuesta})
        ConversationRepository.save(db_user["id"], contexto[-10:], dominio="legal")
        
        await update.message.reply_text(respuesta, parse_mode="Markdown")
    
    async def _handle_cambio_presupuesto(self, update: Update, mensaje: str, db_user: dict) -> None:
        """Manejar cambio de presupuesto"""
        import re
        
        # Buscar número en el mensaje
        numeros = re.findall(r'\d+', mensaje)
        if numeros:
            nuevo_presupuesto = float(numeros[0])
            UserRepository.update_presupuesto(db_user["id"], nuevo_presupuesto)
            
            # Verificar si hay un mensaje pendiente por procesar
            mensaje_pendiente = UserRepository.get_mensaje_pendiente(db_user["id"])
            
            if mensaje_pendiente:
                # Procesar el mensaje pendiente
                await update.message.reply_text(
                    f"✅ *Presupuesto configurado: ${nuevo_presupuesto:.2f}*\n\n"
                    f"📝 Procesando tu mensaje anterior...",
                    parse_mode="Markdown"
                )
                # Reprocesar el mensaje pendiente (llamada recursiva al process)
                # Obtener intención del mensaje pendiente
                try:
                    intención_pendiente = self._ia_service.detectar_intención(mensaje_pendiente).intencion
                except:
                    intención_pendiente = "general"
                
                # Obtener contexto
                dominio = INTENCION_A_DOMINIO.get(intención_pendiente, "general")
                conv_result = ConversationRepository.get_by_dominio(db_user["id"], dominio)
                contexto = conv_result["messages"] if conv_result else []
                
                # Ejecutar handler
                handler = self._handlers.get(intención_pendiente, self._handlers["general"])
                await handler(update, mensaje_pendiente, db_user, dominio=dominio, contexto=contexto)
            else:
                await update.message.reply_text(
                    f"✅ *Presupuesto actualizado!*\n\n"
                    f"Nuevo presupuesto mensual: ${nuevo_presupuesto:.2f}\n\n"
                    f"Quieres ver el estado actual? Escribí /presupuesto",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "No encontré un número en tu mensaje. "
                "Escribí algo como 'Quiero poner mi presupuesto en 2000'"
            )
    
    async def _handle_presupuesto(self, update: Update, mensaje: str, db_user: dict) -> None:
        """Handler para cambiar presupuesto - redirige a comando"""
        await update.message.reply_text(
            "Para ver tu presupuesto usá /presupuesto\n"
            "Para cambiarlo, escribí algo como 'Quiero poner mi presupuesto en 2000'"
        )
    
    async def _handle_general(self, update: Update, mensaje: str, db_user: dict, dominio: str = "general", contexto: list = None) -> None:
        """Handler para mensajes generales - usa TOML modo system"""
        # Usar contexto pasado como parámetro
        if contexto is None:
            conv = ConversationRepository.get_by_dominio(db_user["id"], dominio)
            contexto = conv["messages"] if conv else []
        
        try:
            # Usa modo system (default) desde TOML
            respuesta = self._ia_service.chat(mensaje, contexto, modo="system")
        except IAResponseError:
            respuesta = "Disculpa, tuve un problema. Intentá de nuevo."
        
        # Guardar conversación con dominio específico
        contexto.append({"role": "user", "content": mensaje})
        contexto.append({"role": "assistant", "content": respuesta})
        ConversationRepository.save(db_user["id"], contexto[-10:], dominio=dominio)
        
        await update.message.reply_text(respuesta, parse_mode="Markdown")


# ==================== BOT APPLICATION FACTORY ====================

def create_bot_application() -> Application:
    """Factory para crear aplicación del bot"""
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Registrar handlers
    application.add_handler(CommandHandler("start", StartCommandHandler().execute))
    application.add_handler(CommandHandler("help", HelpCommandHandler().execute))
    application.add_handler(CommandHandler("ayuda", HelpCommandHandler().execute))
    application.add_handler(CommandHandler("gastos", GastosCommandHandler().execute))
    application.add_handler(CommandHandler("metas", MetasCommandHandler().execute))
    
    # Nuevos comandos de automatización
    application.add_handler(CommandHandler("bienestar", lambda u, c: MetanoiaCommandHandler().execute(u, c)))
    application.add_handler(CommandHandler("reporte", lambda u, c: ReporteCommandHandler().execute(u, c)))
    application.add_handler(CommandHandler("presupuesto", lambda u, c: PresupuestoCommandHandler().execute(u, c)))
    
    # Handler de mensajes
    message_router = MessageRouter()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router.process))
    
    return application