"""
Consiglieri Skill Manager
Carga las skills y las ejecuta según la intención detectada
"""

import re
from typing import Optional, Dict, Any, List
from datetime import date
import logging

logger = logging.getLogger(__name__)


# ==================== PATRONES DE INTENCIÓN ====================

INTENTION_PATTERNS = {
    # FINANZAS
    "gasto": [
        r"gast[ée]\s+(\d+)",  # gasté 500
        r"compr[ée]\s+(\d+)", # compré 200
        r"pagu[ée]\s+(\d+)",  # pagué 100
        r"gasto\s+(\d+)",     # gasto 300
        r"(\d+)\s+en\s+(\w+)", # 500 en comida
    ],
    "meta": [
        r"quier[oe]\s+ahorrar\s+(\d+)",  # quiero ahorrar 5000
        r"meta\s+(\d+)",                # meta 3000
        r"ahorrar\s+para\s+(\w+)",      # ahorrar para viaje
        r"objetivo\s+(\d+)",            # objetivo 10000
    ],
    "ingreso": [
        r"gan[ée]\s+(\d+)",    # gané 1000
        r"recib[ée]\s+(\d+)", # recibí 500
        r"salario\s+(\d+)",    # salary 2000
        r"ingreso\s+(\d+)",    # ingreso 800
    ],
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
    Maneja la carga y ejecución de skills
    """
    
    def __init__(self, execution_engine):
        self.engine = execution_engine
        self._current_user_id = None
        self._pending_action = None  # Para acciones que requieren segundo paso
        
    def set_user(self, user_id: str):
        """Establecer usuario actual"""
        self._current_user_id = user_id
    
    def detect_intention(self, message: str) -> str:
        """Detectar intención del mensaje"""
        message_lower = message.lower()
        
        for intention, patterns in INTENTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intention
        
        return "general"
    
    def needs_second_step(self, intention: str) -> bool:
        """Determina si necesita segundo paso (más datos)"""
        return intention in ["gasto", "meta", "ingreso", "deuda", "checkin"]
    
    def execute(self, message: str, user_id: str) -> Dict[str, Any]:
        """
        Ejecutar la skill apropiada según la intención
        """
        self.set_user(user_id)
        
        # Verificar si hay acción pendiente (segundo paso)
        if self._pending_action:
            return self._execute_pending(message)
        
        # Detectar intención
        intention = self.detect_intention(message)
        
        # Verificar si necesita segundo paso
        if self.needs_second_step(intention):
            return self._handle_second_step(intention, message)
        
        # Ejecutar según intención
        if intention == "gasto":
            return self._handle_gasto(message)
        elif intention == "meta":
            return self._handle_meta(message)
        elif intention == "ingreso":
            return self._handle_ingreso(message)
        elif intention == "deuda":
            return self._handle_deuda(message)
        elif intention == "presupuesto":
            return self._handle_presupuesto(message)
        elif intention == "estres" or intention == "emocional" or intention == "energia":
            return self._handle_psicologia(message, intention)
        elif intention == "checkin":
            return self._handle_checkin(message)
        elif intention == "legal":
            return self._handle_legal(message)
        else:
            return self._handle_general(message)
    
    # ==================== HANDLERS ====================
    
    def _handle_gasto(self, message: str) -> Dict[str, Any]:
        """Manejar gasto - extraer monto y categoría"""
        # Extraer monto
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            return {
                "success": True,
                "message": "¿Cuánto gastaste?",
                "action": "WAIT_MONTO"
            }
        
        monto = float(monto_match.group(1))
        
        # Inferir categoría del contexto
        categoria = self._infer_categoria(message)
        
        # Ejecutar
        result = self.engine.expense_create(
            user_id=self._current_user_id,
            monto=monto,
            categoria=categoria,
            descripcion=message
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "next_step": "¿Algo más por registrar?"
        }
    
    async def _handle_meta(self, message: str) -> Dict[str, Any]:
        """Manejar meta de ahorro"""
        # Extraer monto
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            return {
                "success": True,
                "message": "¿Cuánto quieres ahorrar?",
                "action": "WAIT_MONTO"
            }
        
        monto = float(monto_match.group(1))
        
        # Extraer nombre de la meta
        # "quiero ahorrar 5000 para un carro" -> "carro"
        nombre_match = re.search(r"para\s+(?:un|una|el|la)?\s*(\w+)", message)
        nombre = nombre_match.group(1) if nombre_match else "Meta"
        
        result = self.engine.goal_create(
            user_id=self._current_user_id,
            nombre=nombre,
            meta_amount=monto
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "next_step": "¿Tienes fecha objetivo?"
        }
    
    def _handle_ingreso(self, message: str) -> Dict[str, Any]:
        """Manejar ingreso"""
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            return {
                "success": True,
                "message": "¿Cuánto ganaste?",
                "action": "WAIT_MONTO"
            }
        
        monto = float(monto_match.group(1))
        fuente = self._infer_fuente(message)
        
        result = self.engine.income_create(
            user_id=self._current_user_id,
            monto=monto,
            fuente=fuente,
            descripcion=message
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "next_step": "¿Actualizo tu presupuesto?"
        }
    
    def _handle_deuda(self, message: str) -> Dict[str, Any]:
        """Manejar deuda"""
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            return {
                "success": True,
                "message": "¿Cuánto debes?",
                "action": "WAIT_MONTO"
            }
        
        monto = float(monto_match.group(1))
        
        # Extraer acreedor
        acreedor_match = re.search(r"con\s+(?:el|la)?\s*(\w+)", message)
        acreedor = acreedor_match.group(1) if acreedor_match else "Acreedor"
        
        result = self.engine.debt_create(
            user_id=self._current_user_id,
            acreedor=acreedor,
            monto_total=monto
        )
        
        return {
            "success": result["success"],
            "message": result["message"],
            "next_step": "¿Fecha de vencimiento?"
        }
    
    def _handle_presupuesto(self, message: str) -> Dict[str, Any]:
        """Manejar consulta de presupuesto"""
        result = self.engine.budget_get(self._current_user_id)
        
        return {
            "success": result["success"],
            "message": result["message"] + "\n\n¿Querés ajustarlo?",
            "data": result.get("data")
        }
    
    def _handle_psicologia(self, message: str, intention: str) -> Dict[str, Any]:
        """Manejar tema psicológico"""
        # Solicitar nivel de energía
        return {
            "success": True,
            "message": "¿Del 1-100 cómo está tu energía hoy?",
            "action": "WAIT_ENERGIA"
        }
    
    def _handle_checkin(self, message: str) -> Dict[str, Any]:
        """Manejar check-in emocional"""
        return {
            "success": True,
            "message": "¿Del 1-100 cómo estás hoy?",
            "action": "WAIT_ENERGIA"
        }
    
    def _handle_legal(self, message: str) -> Dict[str, Any]:
        """Manejar consulta legal"""
        # Orientación básica - responder según el tema detectado
        temas = self._detect_legal_topic(message)
        
        if "consumidor" in temas:
            respuesta = "Sobre derechos del consumidor:\n"
            respuesta += "• Derecho a información veraz\n"
            respuesta += "• Garantía legal de productos\n"
            respuesta += "• Derecho a retracto (5 días)\n\n"
            respuesta += "⚠️ Esto es orientación general. Para casos complejos, consultá un abogado."
        elif "contrato" in temas:
            respuesta = "Sobre contratos:\n"
            respuesta += "• Elementos: partes, objeto, consentimiento\n"
            respuesta += "• Evitar cláusulas abusivas\n"
            respuesta += "• Todo por escrito\n\n"
            respuesta += "⚠️ Orientación general, no consejo legal."
        elif "empleo" in temas:
            respuesta = "Sobre empleo:\n"
            respuesta += "• Liquidación por despido\n"
            respuesta += "• Horas extras: 50% adicional\n"
            respuesta += "• Prestaciones sociales\n\n"
            respuesta += "⚠️ Te recomiendo un abogado laboral."
        else:
            respuesta = "Sobre ese tema legal, necesito más detalles. "
            respuesta += "¿Podrías contarme brevemente tu situación?"
        
        return {
            "success": True,
            "message": respuesta
        }
    
    def _handle_general(self, message: str) -> Dict[str, Any]:
        """Manejar mensaje general - pasar a IA"""
        return {
            "success": True,
            "message": "CONTINUAR_CON_IA",  # Señal para usar chat de IA
            "action": "IA_CHAT"
        }
    
    # ==================== SEGUNDOS PASOS ====================
    
    def _execute_pending(self, message: str) -> Dict[str, Any]:
        """Ejecutar acción pendiente según el tipo"""
        action = self._pending_action
        
        if action == "WAIT_MONTO":
            # El usuario respondió con el monto
            monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
            if monto_match:
                monto = float(monto_match.group(1))
                # Según la intención previa, ejecutar la acción
                # Por ahora, asume que es gasto
                result = self.engine.expense_create(
                    user_id=self._current_user_id,
                    monto=monto,
                    categoria="Otro",
                    descripcion=message
                )
                self._pending_action = None
                return {
                    "success": result["success"],
                    "message": result["message"]
                }
        
        elif action == "WAIT_ENERGIA":
            # El usuario respondió con nivel de energía
            energia_match = re.search(r"(\d+)", message)
            if energia_match:
                energia = int(energia_match.group(1))
                
                result = self.engine.emotional_checkin_create(
                    user_id=self._current_user_id,
                    nivel_energia=energia,
                    emocion_principal="",
                    notas=message
                )
                self._pending_action = None
                
                # Análisis según nivel
                if energia >= 80:
                    analisis = "🚀 Energía excelente. ¡Aprobala!"
                elif energia >= 60:
                    analisis = "✅ Energía bien. Mantené el ritmo."
                elif energia >= 40:
                    analisis = "⚠️ Energía media. Cuidate."
                elif energia >= 20:
                    analisis = "🛑 Energía baja. Descanso."
                else:
                    analisis = "🆘 Busca apoyo."
                
                return {
                    "success": True,
                    "message": f"📊 Registrado: {energia}/100\n{analisis}\n\n3 cosas: 1) Respirá 2) Movete 3) Escribí lo que pods controlar"
                }
        
        self._pending_action = None
        return {
            "success": False,
            "message": "No entendí. ¿Podés reformular?"
        }
    
    def _handle_second_step(self, intention: str, message: str) -> Dict[str, Any]:
        """Manejar intención que necesita segundo paso"""
        # Guardar la intención para el próximo mensaje
        self._pending_intention = intention
        
        if intention == "gasto":
            return self._handle_gasto(message)
        elif intention == "meta":
            return self._handle_meta(message)
        elif intention == "ingreso":
            return self._handle_ingreso(message)
        elif intention == "deuda":
            return self._handle_deuda(message)
        elif intention in ["checkin", "estres", "emocional"]:
            return self._handle_psicologia(message, intention)
        
        return self._handle_general(message)
    
    # ==================== HELPERS ====================
    
    def _infer_categoria(self, message: str) -> str:
        """Inferir categoría del gasto"""
        message_lower = message.lower()
        
        categorias = {
            "Alimentos": ["comida", "supermercado", "almuerzo", "cena", "desayuno"],
            "Transporte": ["taxi", "uber", "bus", "metro", "gasolina", "gas"],
            "Servicios": ["luz", "agua", "internet", "celular", "telefono"],
            "Entretenimiento": ["netflix", "spotify", "cine", "salida", "party"],
            "Salud": ["medicina", "doctor", "farmacia", "hospital"],
            "Personal": ["ropa", "zapatos", "peluqueria"],
            "Educación": ["curso", "libro", "universidad", "escuela"],
        }
        
        for categoria, keywords in categorias.items():
            for kw in keywords:
                if kw in message_lower:
                    return categoria
        
        return "Otro"
    
    def _infer_fuente(self, message: str) -> str:
        """Inferir fuente del ingreso"""
        message_lower = message.lower()
        
        fuentes = {
            "salario": ["salario", "sueldo", "nómina", "empleo"],
            "freelance": ["freelance", "proyecto", "consultoría"],
            "inversión": ["inversión", "dividendos", "renta"],
            "venta": ["vendi", "venta"],
        }
        
        for fuente, keywords in fuentes.items():
            for kw in keywords:
                if kw in message_lower:
                    return fuente
        
        return "otro"
    
    def _detect_legal_topic(self, message: str) -> List[str]:
        """Detectar tema legal"""
        message_lower = message.lower()
        temas = []
        
        if any(k in message_lower for k in ["consumidor", "tienda", "devolver", "garantía"]):
            temas.append("consumidor")
        if any(k in message_lower for k in ["contrato", "firma", "acuerdo"]):
            temas.append("contrato")
        if any(k in message_lower for k in ["empleo", "despido", "liquidación", "trabajo"]):
            temas.append("empleo")
        if any(k in message_lower for k in ["arrendamiento", "alquiler", "inquilino", "propietario"]):
            temas.append("arrendamiento")
        
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