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


# ==================== PATRONES DE INTENCIÓN ====================

INTENTION_PATTERNS = {
    # FINANZAS - GASTO
    "gasto": [
        r"gast[ée]\s+(\d+)",  # gasté 500
        r"compr[ée]\s+(\d+)", # compré 200
        r"pagu[ée]\s+(\d+)",  # pagué 100
        r"gasto\s+(\d+)",     # gasto 300
        r"(\d+)\s+en\s+(\w+)", # 500 en comida
    ],
    # FINANZAS - INGRESO
    "ingreso": [
        r"mi\s+flujo\s+(?:es|de|es\s+de)\s+(\d+)",      # mi flujo es 910
        r"mi\s+salario\s+(?:es|de|es\s+de|va\s+a\s+ser)\s+(\d+)",  # mi salary es 800
        r"actualiza.*salario\s+(\d+)",          # actualiza mi salary 1200
        r"mi\s+ingreso\s+(?:es|de|es\s+de)\s+(\d+)",   # mi ingreso es 1000
        r"gan[ée]\s+(\d+)",    # gané 1000
        r"recib[ié]\s+(\d+)", # recibí 500
    ],
    # FINANZAS - META
    "meta": [
        r"meta\s+(\w+)\s+(\d+)",     # meta moto 2650
        r"crear\s+meta\s+(\w+)\s+(\d+)", # crear meta moto 2000
        r"quier[oe]\s+ahorrar\s+(\d+)",  # quiero ahorrar 5000
        r"objetivo\s+(\d+)",            # objetivo 10000
    ],
    # FINANZAS - DEUDA
    "deuda": [
        r"debo\s+(\d+)",         # debo 5000
        r"deuda\s+de\s+(\d+)",   # deuda de 3000
        r"prestado\s+(\d+)",     # prestado 1000
    ],
    "presupuesto": [
        r"cu[áa]nto\s+tengo",     # cuánto tengo
        r"presupuesto",           # presupuesto
        r"cu[áa]nto\s+me\s+queda", # cuánto me queda
    ],
    
    # PSICOLOGÍA
    "estres": [
        r"estr[ée]s",      # estrés
        r"ansioso",        # ansioso
        r"agobiado",      # agobiado
        r"ansiedad",       # ansiedad
    ],
    "emocional": [
        r"triste",         # triste
        r"mal",           # mal
        r"deprimido",     # deprimido
        r"estoy\s+mal",   # estoy mal
    ],
    "energia": [
        r"energ[íi]a",     # energía
        r"cansado",        # cansado
        r"motivaci[óo]n",  # motivación
    ],
    "checkin": [
        r"check[ -]?in",   # checkin
        r"c[óo]mo\s+estoy", # cómo estoy
    ],
    
    # LEGAL
    "legal": [
        r"legal",          # legal
        r"ley",            # ley
        r"derecho",        # derecho
        r"contrato",       # contrato
    ],
}


# ==================== SKILL MANAGER ====================

class ConsiglieriSkillManager:
    """
    Maneja la carga y ejecución de skills.
    Implementa el flujo de persistencia de estado en BD para evitar bucles.
    """
    
    def __init__(self, execution_engine):
        self.engine = execution_engine
        self._current_user_id: Optional[str] = None
        
        logger.info("ConsiglieriSkillManager inicializado")
    
    def detect_intention(self, message: str) -> IntentionType:
        """Detectar intención del mensaje usando patrones regex."""
        message_lower = message.lower().strip()
        
        # Buscar patrones de intención
        for intention_name, patterns in INTENTION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    try:
                        intention = IntentionType(intention_name)
                        return intention
                    except ValueError:
                        continue
        
        return IntentionType.GENERAL
    
    def _should_pass_to_ia(self, message: str, intention: IntentionType) -> bool:
        """Determina si el mensaje debe pasar a IA para interpretación."""
        msg_lower = message.lower().strip()
        if intention != IntentionType.GENERAL:
            return False
        if len(message) < 30:
            return False
        
        saludos = ["hola", "buenas", "buenos dias", "buenas noches", "hello", "hi", "que tal", "como estas", "buen dia"]
        if any(msg_lower.startswith(s) for s in saludos):
            return False
        
        palabras_analisis = [
            "qué crees", "crees que", "me recomiendas", "opinión", "analiza", 
            "situación", "consejo", "piensas", "debería", "flujo", 
            "presupuesto", "deuda", "inversión", "ahorrar", "plan"
        ]
        
        if any(p in msg_lower for p in palabras_analisis) and len(message) > 50:
            return True
        
        return False
    
    async def execute(self, message: str, user_id: str) -> Dict[str, Any]:
        """
        Ejecutar la skill apropiada.
        AHORA CARGA EL ESTADO DESDE LA BD.
        """
        logger.info(f"=== PROCESANDO MENSAJE === User: {user_id[:8]}... | Mensaje: {message[:50]}...")
        self._current_user_id = user_id
        
        # 1. Cargar estado desde la base de datos
        state = UserRepository.get_pending_state(user_id)
        pending_action = state.get("action")
        pending_data = state.get("data") or {}
        
        # 2. Si hay acción pendiente, ejecutar _execute_pending
        if pending_action and pending_action != ActionState.NONE.value:
            logger.info(f"Ejecutando acción pendiente: {pending_action}")
            return await self._execute_pending(message, pending_action, pending_data)
        
        # 3. Detectar intención
        intention = self.detect_intention(message)
        
        # 4. Si es GENERAL, verificar si debe pasar a IA
        if intention == IntentionType.GENERAL:
            if self._should_pass_to_ia(message, intention):
                return {
                    "success": True,
                    "message": "CONTINUAR_CON_IA",
                    "action": "IA_CHAT"
                }
            else:
                return await self._handle_general(message)
        
        # 5. Ejecutar según intención
        if intention == IntentionType.GASTO:
            return await self._handle_gasto(message)
        elif intention == IntentionType.META:
            return await self._handle_meta(message)
        elif intention == IntentionType.INGRESO:
            return await self._handle_ingreso(message)
        elif intention == IntentionType.DEUDA:
            return await self._handle_deuda(message)
        elif intention == IntentionType.PRESUPUESTO:
            return await self._handle_presupuesto(message)
        elif intention in [IntentionType.ESTRES, IntentionType.EMOCIONAL, IntentionType.ENERGIA]:
            return await self._handle_psicologia(message, intention)
        elif intention == IntentionType.CHECKIN:
            return await self._handle_checkin(message)
        elif intention == IntentionType.LEGAL:
            return await self._handle_legal(message)
        else:
            return await self._handle_general(message)
    
    # ==================== HANDLERS ====================
    
    async def _handle_gasto(self, message: str) -> Dict[str, Any]:
        """Manejar gasto - extraer monto y PREGUNTAR categoría"""
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            UserRepository.set_pending_state(self._current_user_id, ActionState.WAIT_MONTO.value)
            return {
                "success": True,
                "message": "¿Cuánto gastaste, hermano? Así lo anoto de una vez."
            }
        
        monto = float(monto_match.group(1))
        categoria = self._infer_categoria(message)
        
        # Guardar en BD para el próximo paso
        UserRepository.set_pending_state(
            self._current_user_id, 
            ActionState.WAIT_CATEGORIA.value, 
            {"monto": monto, "categoria": categoria}
        )
        
        return {
            "success": True,
            "message": f"Dale, anotado los ${monto}. ¿En qué categoría lo pongo? (Ej: Alimentos, Transporte, Entretenimiento...)"
        }
    
    async def _handle_meta(self, message: str) -> Dict[str, Any]:
        """Manejar meta de ahorro - pregunta plazo e ingreso"""
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            UserRepository.set_pending_state(self._current_user_id, ActionState.WAIT_MONTO.value, {"type": "meta"})
            return {
                "success": True,
                "message": "¿Cuál es el monto de esa meta que querés alcanzar?"
            }
        
        monto = float(monto_match.group(1))
        nombre_match = re.search(r"para\s+(?:un|una|el|la)?\s*(\w+)", message)
        nombre = nombre_match.group(1) if nombre_match else "Meta"
        
        UserRepository.set_pending_state(
            self._current_user_id, 
            ActionState.WAIT_META_DETAILS.value, 
            {"nombre": nombre, "monto": monto}
        )
        
        return {
            "success": True,
            "message": f"Buenísimo, una meta para {nombre} de ${monto:,.2f}. ¿En cuántos meses pensás lograrlo y cuál es tu ingreso mensual aproximado para ayudarte con el cálculo?"
        }
    
    async def _handle_ingreso(self, message: str) -> Dict[str, Any]:
        """Manejar ingreso - pregunta para confirmar"""
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            return {
                "success": True,
                "message": "¿De cuánto fue el ingreso?"
            }
        
        monto = float(monto_match.group(1))
        UserRepository.set_pending_state(
            self._current_user_id, 
            ActionState.WAIT_CONFIRMA_INGRESO.value, 
            {"monto": monto}
        )
        
        return {
            "success": True,
            "message": f"Entendí ${monto}. ¿Es tu ingreso mensual fijo o algo puntual?"
        }
    
    async def _handle_deuda(self, message: str) -> Dict[str, Any]:
        """Manejar deuda"""
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            return {"success": True, "message": "¿Cuánto debés?"}
        
        monto = float(monto_match.group(1))
        acreedor_match = re.search(r"con\s+(?:el|la)?\s*(\w+)", message)
        acreedor = acreedor_match.group(1) if acreedor_match else "Acreedor"
        
        result = self.engine.debt_create(user_id=self._current_user_id, acreedor=acreedor, monto_total=monto)
        return {
            "success": result["success"],
            "message": f"Anotado, debés ${monto:,.2f} a {acreedor}. ¿Tenés una fecha límite para pagarlo?"
        }
    
    async def _handle_presupuesto(self, message: str) -> Dict[str, Any]:
        """Manejar consulta de presupuesto"""
        result = self.engine.budget_get(self._current_user_id)
        return {
            "success": result["success"],
            "message": f"{result['message']}\n\n¿Te parece bien o querés que lo ajustemos?"
        }
    
    async def _handle_psicologia(self, message: str, intention: str) -> Dict[str, Any]:
        """Manejar tema psicológico"""
        UserRepository.set_pending_state(self._current_user_id, ActionState.WAIT_ENERGIA.value)
        return {
            "success": True,
            "message": "Te entiendo. Antes de seguir, ¿del 1 al 100 cómo sentís tu energía ahora mismo?"
        }
    
    async def _handle_checkin(self, message: str) -> Dict[str, Any]:
        """Manejar check-in emocional"""
        UserRepository.set_pending_state(self._current_user_id, ActionState.WAIT_ENERGIA.value)
        return {
            "success": True,
            "message": "¿Cómo va ese día? Contame del 1 al 100 cómo estás de ánimo y energía."
        }
    
    async def _handle_legal(self, message: str) -> Dict[str, Any]:
        """Manejar consulta legal"""
        temas = self._detect_legal_topic(message)
        if "consumidor" in temas:
            respuesta = "Sobre tus derechos como consumidor: tenés derecho a información veraz y garantía. Si es una compra online, recordá el derecho de retracto. ¿Qué te pasó puntualmente?"
        elif "contrato" in temas:
            respuesta = "Los contratos son sagrados pero deben ser claros. Leé siempre la letra chica. ¿Estás por firmar algo o tenés dudas de uno ya firmado?"
        elif "empleo" in temas:
            respuesta = "En temas laborales es clave saber tus prestaciones y tiempos. ¿Es por una liquidación o algo del día a día?"
        else:
            respuesta = "En temas legales te puedo orientar con lo básico. ¿Qué situación te preocupa?"
        
        return {"success": True, "message": respuesta}
    
    async def _handle_general(self, message: str) -> Dict[str, Any]:
        """Manejar mensaje general"""
        msg_lower = message.lower().strip()
        saludos = ["hola", "buenas", "buenos dias", "buenas noches", "hello", "hi", "que tal", "como estas", "buen dia"]
        
        if any(msg_lower.startswith(s) for s in saludos):
            return {
                "success": True,
                "message": "¡Hola! Acá Consiglieri. Te ayudo a poner en orden tus finanzas, tus metas y tu bienestar. ¿Por dónde querés arrancar hoy?"
            }
        
        if len(message) < 30:
            return {
                "success": True,
                "message": "Estoy listo. Podés decirme algo como 'gasté 500 en café', 'quiero ahorrar para un viaje' o simplemente contarme cómo te sentís."
            }
        
        return {
            "success": True,
            "message": "No te seguí del todo. Recordá que puedo registrar tus gastos, ayudarte con tus metas de ahorro o charlar un poco sobre bienestar. ¿Qué necesitás?"
        }
    
    # ==================== SEGUNDOS PASOS ====================
    
    async def _execute_pending(self, message: str, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar acción pendiente cargada de la BD"""
        
        if action == ActionState.WAIT_MONTO.value:
            monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
            if monto_match:
                monto = float(monto_match.group(1))
                if data.get("type") == "meta":
                    UserRepository.set_pending_state(self._current_user_id, ActionState.WAIT_META_DETAILS.value, {"monto": monto})
                    return {"success": True, "message": f"Dale, ${monto}. ¿Para qué es esta meta y en cuánto tiempo la querés cumplir?"}
                
                result = self.engine.expense_create(user_id=self._current_user_id, monto=monto, categoria="Otro", descripcion=message)
                UserRepository.clear_pending_state(self._current_user_id)
                return {"success": result["success"], "message": "¡Listo! Ya quedó registrado el gasto. ¿Algo más?"}
        
        elif action == ActionState.WAIT_CATEGORIA.value:
            categoria = message.strip().title()
            monto = data.get('monto', 0)
            if monto > 0:
                result = self.engine.expense_create(user_id=self._current_user_id, monto=monto, categoria=categoria, descripcion=message)
                UserRepository.clear_pending_state(self._current_user_id)
                return {"success": result["success"], "message": f"Perfecto, guardé los ${monto} en {categoria}. ¡Bien ahí por llevar el control!"}
        
        elif action == ActionState.WAIT_META_DETAILS.value:
            meses_match = re.search(r'(\d+)\s*(?:mes|meses)', message.lower())
            ingreso_match = re.search(r'(\d+(?:\.\d+)?)', message)
            
            nombre = data.get('nombre', 'Meta')
            monto = data.get('monto', 0)
            meses = int(meses_match.group(1)) if meses_match else 12
            ingreso = float(ingreso_match.group(1)) if ingreso_match else 0
            
            result = self.engine.goal_create(user_id=self._current_user_id, nombre=nombre, meta_amount=monto)
            UserRepository.clear_pending_state(self._current_user_id)
            
            if meses > 0:
                ahorro_mensual = monto / meses
                if ingreso > 0:
                    porcentaje = (ahorro_mensual / ingreso) * 100
                    return {"success": True, "message": f"¡Meta creada! Para {nombre} de ${monto:,.2f} en {meses} meses, tendrías que ahorrar unos ${ahorro_mensual:,.2f} por mes. Eso es el {porcentaje:.1f}% de tu ingreso. ¿Te parece viable?"}
                return {"success": True, "message": f"Meta creada para {nombre}. En {meses} meses tendrías que ahorrar unos ${ahorro_mensual:,.2f} mensuales. ¡A darle con todo!"}
        
        elif action == ActionState.WAIT_ENERGIA.value:
            energia_match = re.search(r"(\d+)", message)
            if energia_match:
                energia = int(energia_match.group(1))
                result = self.engine.emotional_checkin_create(user_id=self._current_user_id, nivel_energia=energia, notas=message)
                UserRepository.clear_pending_state(self._current_user_id)
                
                if energia >= 70:
                    msg = f"¡Qué nivel! Con {energia} de energía estás para comerte el mundo. Aprovechá ese impulso."
                elif energia >= 40:
                    msg = f"Entiendo, un {energia} de energía. Está bien para mantener el ritmo, pero no te olvides de pausar un poco."
                else:
                    msg = f"Uff, un {energia} es poquito. Tomalo con calma hoy, no te exijas de más. Mañana será otro día."
                return {"success": True, "message": msg}
        
        elif action == ActionState.WAIT_CONFIRMA_INGRESO.value:
            msg_lower = message.lower().strip()
            if any(p in msg_lower for p in ["si", "sí", "fijo", "mensual", "correcto"]):
                monto = data.get('monto', 0)
                result = self.engine.income_create(user_id=self._current_user_id, monto=monto, fuente="Ingreso mensual")
                UserRepository.clear_pending_state(self._current_user_id)
                return {"success": result["success"], "message": f"Excelente, ya sumé esos ${monto} a tus ingresos del mes."}
            else:
                monto = data.get('monto', 0)
                UserRepository.set_pending_state(self._current_user_id, ActionState.WAIT_CATEGORIA.value, {"monto": monto})
                return {"success": True, "message": f"Ah, entonces es un gasto de ${monto}. ¿En qué categoría lo pongo?"}
        
        UserRepository.clear_pending_state(self._current_user_id)
        return {"success": False, "message": "Me perdí un poco, hermano. ¿Podés repetirme lo último?"}
    
    # ==================== HELPERS ====================
    
    def _infer_categoria(self, message: str) -> str:
        """Inferir categoría del gasto"""
        message_lower = message.lower()
        categorias = {
            "Alimentos": ["comida", "supermercado", "almuerzo", "cena", "desayuno", "restaurante"],
            "Transporte": ["taxi", "uber", "bus", "metro", "gasolina", "gas", "peaje"],
            "Servicios": ["luz", "agua", "internet", "celular", "telefono", "gas"],
            "Entretenimiento": ["netflix", "spotify", "cine", "salida", "party", "bar", "cerveza"],
            "Salud": ["medicina", "doctor", "farmacia", "hospital", "dentista"],
            "Personal": ["ropa", "zapatos", "peluqueria", "barberia"],
            "Educación": ["curso", "libro", "universidad", "escuela"],
        }
        for categoria, keywords in categorias.items():
            if any(kw in message_lower for kw in keywords):
                return categoria
        return "Otro"

    def _detect_legal_topic(self, message: str) -> List[str]:
        """Detectar tema legal"""
        message_lower = message.lower()
        temas = []
        if any(k in message_lower for k in ["consumidor", "tienda", "devolver", "garantía", "reclamo"]): temas.append("consumidor")
        if any(k in message_lower for k in ["contrato", "firma", "acuerdo", "clausula"]): temas.append("contrato")
        if any(k in message_lower for k in ["empleo", "despido", "liquidación", "trabajo", "sueldo"]): temas.append("empleo")
        if any(k in message_lower for k in ["arrendamiento", "alquiler", "inquilino", "propietario"]): temas.append("arrendamiento")
        return temas


# ==================== FACTORY ====================

class SkillManagerFactory:
    """Factory para el skill manager"""
    _instance: Optional[ConsiglieriSkillManager] = None
    @classmethod
    def get_manager(cls, execution_engine) -> ConsiglieriSkillManager:
        if cls._instance is None:
            cls._instance = ConsiglieriSkillManager(execution_engine)
        return cls._instance

def get_skill_manager(execution_engine) -> ConsiglieriSkillManager:
    """Obtener instancia del skill manager"""
    return SkillManagerFactory.get_manager(execution_engine)