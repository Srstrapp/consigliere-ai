"""
Consiglieri Skill Manager
Carga las skills y las ejecuta según la intención detectada
"""

import re
from typing import Optional, Dict, Any, List
from datetime import date
import logging

from .enums import ActionState, IntentionType
from ..services.database import UserRepository

logger = logging.getLogger(__name__)

# Persistencia de estado en memoria (Global por proceso)
_USER_STATES: Dict[str, Dict[str, Any]] = {}

# ==================== PATRONES DE INTENCIÓN ====================

INTENTION_PATTERNS = {
    # FINANZAS - GASTO
    "gasto": [
        r"gast[ée]\s+(\d+)", 
        r"compr[ée]\s+(\d+)", 
        r"pagu[ée]\s+(\d+)",  
        r"gasto\s+(\d+)",     
        r"(\d+)\s+en\s+(\w+)", 
    ],
    # FINANZAS - INGRESO
    "ingreso": [
        r"mi\s+flujo\s+(?:es|de|es\s+de)\s+(\d+)",      
        r"mi\s+salario\s+(?:es|de|es\s+de|va\s+a\s+ser)\s+(\d+)",  
        r"actualiza.*salario\s+(\d+)",          
        r"mi\s+ingreso\s+(?:es|de|es\s+de)\s+(\d+)",   
        r"gan[ée]\s+(\d+)",    
        r"recib[ié]\s+(\d+)", 
    ],
    # FINANZAS - META
    "meta": [
        r"meta\s+(\w+)\s+(\d+)",     
        r"crear\s+meta\s+(\w+)\s+(\d+)", 
        r"quier[oe]\s+ahorrar\s+(\d+)",  
        r"objetivo\s+(\d+)",            
        r"/metas",
    ],
    # FINANZAS - DEUDA
    "deuda": [
        r"debo\s+(\d+)",         
        r"deuda\s+de\s+(\d+)",   
        r"prestado\s+(\d+)",     
    ],
    "presupuesto": [
        r"cu[áa]nto\s+tengo",     
        r"presupuesto",           
        r"cu[áa]nto\s+me\s+queda", 
        r"/presupuesto",
    ],
    
    # PSICOLOGÍA / BIENESTAR
    "estres": [
        r"estr[ée]s",      
        r"ansioso",        
        r"agobiado",      
        r"ansiedad",       
        r"triste",
        r"deprimido",
        r"mal",
        r"estoy\s+mal",
    ],
    "energia": [
        r"energ[íi]a",     
        r"cansado",        
        r"motivaci[óo]n",  
    ],
    "checkin": [
        r"check[ -]?in",   
        r"c[óo]mo\s+estoy", 
        r"/bienestar",
    ],
    
    # LEGAL
    "legal": [
        r"legal",          
        r"ley",            
        r"derecho",        
        r"contrato",       
        r"despido",
        r"despidieron",
        r"renuncia",
        r"demanda",
    ],
    
    # GENERAL / COMANDOS
    "ayuda": [
        r"/ayuda",
        r"/help",
        r"ayuda",
        r"qué\s+podés\s+hacer",
    ],
    "reporte": [
        r"/reporte",
        r"resumen",
        r"gastos\s+del\s+mes",
    ]
}


# ==================== SKILL MANAGER ====================

class ConsiglieriSkillManager:
    """
    Maneja la carga y ejecución de skills.
    Implementa el flujo de persistencia de estado en memoria para evitar errores de BD.
    """
    
    def __init__(self, execution_engine):
        self.engine = execution_engine
        self._current_user_id: Optional[str] = None
        
        logger.info("ConsiglieriSkillManager inicializado con ruteo mejorado")
    
    def _save_state(self, user_id: str, action: str, data: Dict[str, Any] = None):
        _USER_STATES[user_id] = {"action": action, "data": data or {}}

    def _clear_state(self, user_id: str):
        if user_id in _USER_STATES:
            del _USER_STATES[user_id]

    def detect_intention(self, message: str) -> IntentionType:
        message_lower = message.lower().strip()
        
        for intention_name, patterns in INTENTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    try:
                        # Mapear nombres de patrones a Enums
                        if intention_name in ["estres", "energia", "checkin"]:
                            return IntentionType.CHECKIN
                        if intention_name == "ayuda":
                            return IntentionType.GENERAL
                        return IntentionType.INTENTION_MAPPING.get(intention_name, IntentionType(intention_name))
                    except:
                        # Fallback manual para evitar errores de Enum
                        mapping = {
                            "gasto": IntentionType.GASTO,
                            "ingreso": IntentionType.INGRESO,
                            "meta": IntentionType.META,
                            "deuda": IntentionType.DEUDA,
                            "presupuesto": IntentionType.PRESUPUESTO,
                            "legal": IntentionType.LEGAL,
                            "reporte": IntentionType.GENERAL
                        }
                        return mapping.get(intention_name, IntentionType.GENERAL)
        
        return IntentionType.GENERAL
    
    def _should_pass_to_ia(self, message: str, intention: IntentionType) -> bool:
        """Determina si el mensaje debe pasar a IA."""
        msg_lower = message.lower().strip()
        
        # SIEMPRE pasar a IA si es tema legal o emocional profundo
        if intention in [IntentionType.LEGAL, IntentionType.ESTRES, IntentionType.EMOCIONAL]:
            return True
            
        if intention != IntentionType.GENERAL:
            return False
            
        if len(message) < 15: # Bajamos el límite para que sea más reactivo
            return False
        
        saludos = ["hola", "buenas", "buenos dias", "buenas noches", "hello", "hi", "que tal", "como estas"]
        if any(msg_lower == s for s in saludos):
            return False
        
        return True # Por defecto, si es largo y general, que responda la IA
    
    async def execute(self, message: str, user_id: str) -> Dict[str, Any]:
        logger.info(f"=== PROCESANDO MENSAJE === User: {user_id[:8]}... | Mensaje: {message[:50]}...")
        self._current_user_id = user_id
        
        state = _USER_STATES.get(user_id, {"action": None, "data": {}})
        pending_action = state.get("action")
        pending_data = state.get("data") or {}
        
        if pending_action and pending_action != ActionState.NONE.value:
            return await self._execute_pending(message, pending_action, pending_data)
        
        intention = self.detect_intention(message)
        logger.info(f"Intención detectada: {intention}")
        
        # 4. Verificación de IA con MODO dinámico
        if self._should_pass_to_ia(message, intention):
            modo = "system"
            if intention == IntentionType.LEGAL: modo = "legal"
            elif intention in [IntentionType.ESTRES, IntentionType.EMOCIONAL, IntentionType.CHECKIN]: modo = "metanoia"
            
            return {
                "success": True,
                "message": "CONTINUAR_CON_IA",
                "action": "IA_CHAT",
                "modo": modo
            }
        
        # 5. Ejecutar según intención (Handlers Directos)
        if intention == IntentionType.GASTO:
            return await self._handle_gasto(message)
        elif intention == IntentionType.META:
            return await self._handle_meta(message)
        elif intention == IntentionType.INGRESO:
            return await self._handle_ingreso(message)
        elif intention == IntentionType.PRESUPUESTO:
            return await self._handle_presupuesto(message)
        elif intention == IntentionType.CHECKIN:
            return await self._handle_checkin(message)
        else:
            return await self._handle_general(message)
    
    # ==================== HANDLERS ====================
    
    async def _handle_gasto(self, message: str) -> Dict[str, Any]:
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            self._save_state(self._current_user_id, ActionState.WAIT_MONTO.value)
            return {"success": True, "message": "¿Cuánto gastaste, hermano? Así lo anoto de una vez. 😊"}
        
        monto = float(monto_match.group(1))
        categoria = self._infer_categoria(message)
        self._save_state(self._current_user_id, ActionState.WAIT_CATEGORIA.value, {"monto": monto, "categoria": categoria})
        return {"success": True, "message": f"Dale, anotado los ${monto}. ¿En qué categoría lo pongo? (Ej: Alimentos, Transporte, Otro)"}
    
    async def _handle_meta(self, message: str) -> Dict[str, Any]:
        if "/metas" in message.lower():
            result = self.engine.goal_get_all(self._current_user_id)
            return {"success": True, "message": result["message"]}

        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            self._save_state(self._current_user_id, ActionState.WAIT_MONTO.value, {"type": "meta"})
            return {"success": True, "message": "¿Cuál es el monto de esa meta que querés alcanzar? 🎯"}
        
        monto = float(monto_match.group(1))
        nombre_match = re.search(r"para\s+(?:un|una|el|la)?\s*(\w+)", message)
        nombre = nombre_match.group(1) if nombre_match else "Meta"
        self._save_state(self._current_user_id, ActionState.WAIT_META_DETAILS.value, {"nombre": nombre, "monto": monto})
        return {"success": True, "message": f"Buenísimo, una meta para {nombre} de ${monto:,.2f}. ¿En cuántos meses pensás lograrlo?"}
    
    async def _handle_presupuesto(self, message: str) -> Dict[str, Any]:
        result = self.engine.budget_get(self._current_user_id)
        return {"success": True, "message": f"Tu presupuesto actual es de {result['message']}. ¿Querés que lo ajustemos o está bien así? 💰"}
    
    async def _handle_checkin(self, message: str) -> Dict[str, Any]:
        self._save_state(self._current_user_id, ActionState.WAIT_ENERGIA.value)
        return {"success": True, "message": "¿Cómo va ese ánimo hoy? Contame del 1 al 100 cómo estás de energía para arrancar. 🧘‍♂️"}
    
    async def _handle_general(self, message: str) -> Dict[str, Any]:
        if "/reporte" in message.lower():
            from ..services.database import ExpenseRepository
            summary = ExpenseRepository.get_summary(self._current_user_id)
            msg = f"Este mes llevás gastado un total de ${summary['total']:,.2f}. 📊\n\n"
            if summary['categorías']:
                msg += "Desglose:\n"
                for cat, monto in summary['categorías'].items():
                    msg += f"• {cat}: ${monto:,.2f}\n"
            return {"success": True, "message": msg}

        if "/ayuda" in message.lower() or "ayuda" in message.lower():
            return {
                "success": True,
                "message": "¡Acá estoy! Podés usar estos comandos:\n\n"
                           "💰 /presupuesto - Ver cuánto tenés\n"
                           "🎯 /metas - Ver tus objetivos\n"
                           "📊 /reporte - Ver tus gastos del mes\n"
                           "🧘‍♂️ /bienestar - Hacer un check-in\n\n"
                           "O simplemente escribime: 'gasté 500 en pizza' o 'estoy preocupado por un contrato'."
            }

        return {
            "success": True,
            "message": "No te seguí del todo, hermano. ¿Querés registrar un gasto, ver tus metas o charlar un poco? Escribime /ayuda si tenés dudas. 😊"
        }
    
    # ==================== SEGUNDOS PASOS ====================
    
    async def _execute_pending(self, message: str, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if action == ActionState.WAIT_MONTO.value:
            monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
            if monto_match:
                monto = float(monto_match.group(1))
                if data.get("type") == "meta":
                    self._save_state(self._current_user_id, ActionState.WAIT_META_DETAILS.value, {"monto": monto})
                    return {"success": True, "message": f"Dale, ${monto}. ¿Para qué es esta meta y en cuánto tiempo la querés cumplir?"}
                result = self.engine.expense_create(user_id=self._current_user_id, monto=monto, categoria="Otro", descripcion=message)
                self._clear_state(self._current_user_id)
                return {"success": result["success"], "message": "¡Listo! Ya quedó registrado. ¿Algo más?"}
        
        elif action == ActionState.WAIT_CATEGORIA.value:
            categoria = message.strip().title()
            monto = data.get('monto', 0)
            result = self.engine.expense_create(user_id=self._current_user_id, monto=monto, categoria=categoria, descripcion=message)
            self._clear_state(self._current_user_id)
            return {"success": result["success"], "message": f"Perfecto, guardé los ${monto} en {categoria}. ¡Bien ahí! 👏"}
        
        elif action == ActionState.WAIT_ENERGIA.value:
            energia_match = re.search(r"(\d+)", message)
            if energia_match:
                energia = int(energia_match.group(1))
                self.engine.emotional_checkin_create(user_id=self._current_user_id, nivel_energia=energia, notas=message)
                self._clear_state(self._current_user_id)
                return {"success": True, "message": f"Anotado tu {energia} de energía. ¡A darle con todo a lo que queda del día! 🚀"}
        
        self._clear_state(self._current_user_id)
        return {"success": False, "message": "Me perdí, ¿podés repetirme lo último? 😊"}
    
    def _infer_categoria(self, message: str) -> str:
        message_lower = message.lower()
        categorias = {
            "Alimentos": ["comida", "super", "pizza", "hamburguesa", "almuerzo", "cena"],
            "Transporte": ["taxi", "uber", "bus", "gasolina", "nafta"],
            "Servicios": ["luz", "agua", "internet", "netflix"],
            "Entretenimiento": ["cine", "bar", "fiesta", "juego"],
        }
        for cat, keywords in categorias.items():
            if any(k in message_lower for k in keywords): return cat
        return "Otro"

    def _detect_legal_topic(self, message: str) -> List[str]:
        # Implementación simple para detectar temas legales
        return ["legal"] if "ley" in message.lower() or "contrato" in message.lower() else []


# ==================== FACTORY ====================

class SkillManagerFactory:
    _instance: Optional[ConsiglieriSkillManager] = None
    @classmethod
    def get_manager(cls, execution_engine) -> ConsiglieriSkillManager:
        if cls._instance is None: cls._instance = ConsiglieriSkillManager(execution_engine)
        return cls._instance

def get_skill_manager(execution_engine) -> ConsiglieriSkillManager:
    return SkillManagerFactory.get_manager(execution_engine)
