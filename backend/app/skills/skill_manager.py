"""
Consiglieri Skill Manager
Carga las skills y las ejecuta según la intención detectada
"""

import re
from typing import Optional, Dict, Any, List
from datetime import date
import logging

from .enums import ActionState, IntentionType

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
    Implementa el flujo definido en spec.md:
    - Detecta intención del mensaje
    - Determina si necesita segundo paso
    - Ejecuta el handler apropiado
    - Retorna respuesta directa o pasa a IA
    """
    
    def __init__(self, execution_engine):
        self.engine = execution_engine
        self._current_user_id: Optional[str] = None
        self._pending_action: ActionState = ActionState.NONE
        self._pending_data: Dict[str, Any] = {}
        
        logger.info("ConsiglieriSkillManager inicializado")
    
    def set_user(self, user_id: str):
        """Establecer usuario actual y limpiar estado previo"""
        self._current_user_id = user_id
        self._pending_action = ActionState.NONE
        self._pending_data = {}
        logger.debug(f"Usuario establecido: {user_id}")
    
    def detect_intention(self, message: str) -> IntentionType:
        """
        Detectar intención del mensaje usando patrones regex.
        Retorna el tipo de intención detectado.
        """
        message_lower = message.lower().strip()
        
        # Primero verificar comandos especiales
        if message_lower in ["/start", "start", "/menu", "/menu", "/ayuda", "/help", "menu", "ayuda"]:
            logger.info(f"Intención detectada: MENU (comando especial)")
            return IntentionType.GENERAL
        
        # Buscar patrones de intención
        for intention_name, patterns in INTENTION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    try:
                        intention = IntentionType(intention_name)
                        logger.info(f"Intención detectada: {intention.value} - patrón: {pattern}")
                        return intention
                    except ValueError:
                        continue
        
        logger.info("Intención detectada: GENERAL (no matcheó ningún patrón)")
        return IntentionType.GENERAL
    
    def _should_pass_to_ia(self, message: str, intention: IntentionType) -> bool:
        """
        Determina si el mensaje debe pasar a IA para interpretación.
        Solo para mensajes largos con contenido real de análisis/situación.
        """
        msg_lower = message.lower().strip()
        
        # Si la intención ya es específica (gasto, meta, etc), no pasar a IA
        if intention != IntentionType.GENERAL:
            return False
        
        # Si es mensaje corto, responder directamente
        if len(message) < 30:
            logger.debug("Mensaje corto - no pasa a IA")
            return False
        
        # Detectar si es saludo trivial
        saludos = ["hola", "buenas", "buenos dias", "buenas noches", "hello", "hi", "que tal", "como estas", "buen dia"]
        if any(msg_lower.startswith(s) for s in saludos):
            logger.debug("Saludo trivial - no pasa a IA")
            return False
        
        # Verificar palabras que indican análisis real
        palabras_analisis = [
            "qué crees", "crees que", "me recomiendas", "opinión", "analiza", 
            "situación", "consejo", "piensas", "debería", "flujo", 
            "presupuesto", "deuda", "inversión", "ahorrar", "plan"
        ]
        
        if any(p in msg_lower for p in palabras_analisis) and len(message) > 50:
            logger.info("Mensaje con contenido real - pasa a IA para interpretación")
            return True
        
        return False
    
    def execute(self, message: str, user_id: str) -> Dict[str, Any]:
        """
        Ejecutar la skill apropiada según la intención.
        Flujo definido en spec.md:
        1. Si hay acción pendiente, ejecutar _execute_pending
        2. Detectar intención
        3. Si es GENERAL, verificar si debe pasar a IA
        4. Si necesita segundo paso, ejecutar handler correspondiente
        5. Ejecutar handler según intención
        """
        logger.info(f"=== PROCESANDO MENSAJE === User: {user_id[:8]}... | Mensaje: {message[:50]}...")
        
        self.set_user(user_id)
        
        # 1. Verificar si hay acción pendiente
        if self._pending_action != ActionState.NONE:
            logger.info(f"Ejecutando acción pendiente: {self._pending_action.value}")
            return self._execute_pending(message)
        
        # 2. Detectar intención
        intention = self.detect_intention(message)
        logger.info(f"Intención detectada: {intention.value}")
        
        # 3. Si es GENERAL, verificar si debe pasar a IA
        if intention == IntentionType.GENERAL:
            if self._should_pass_to_ia(message, intention):
                logger.info("Pasando a IA para interpretación")
                return {
                    "success": True,
                    "message": "CONTINUAR_CON_IA",
                    "action": "IA_CHAT"
                }
            else:
                # Responder directamente sin IA
                logger.info("Respondiendo directamente (mensaje trivial)")
                return self._handle_general(message)
        
        # 4. Determinar si necesita segundo paso
        intentions_need_second_step = [
            IntentionType.GASTO,
            IntentionType.META,
            IntentionType.INGRESO,
            IntentionType.DEUDA,
            IntentionType.CHECKIN
        ]
        
        if intention in intentions_need_second_step:
            logger.info(f"Ejecutando handler con segundo paso: {intention.value}")
            return self._handle_second_step(intention, message)
        
        # 5. Ejecutar según intención directamente
        logger.info(f"Ejecutando handler directo: {intention.value}")
        
        if intention == IntentionType.GASTO:
            return self._handle_gasto(message)
        elif intention == IntentionType.META:
            return self._handle_meta(message)
        elif intention == IntentionType.INGRESO:
            return self._handle_ingreso(message)
        elif intention == IntentionType.DEUDA:
            return self._handle_deuda(message)
        elif intention == IntentionType.PRESUPUESTO:
            return self._handle_presupuesto(message)
        elif intention in [IntentionType.ESTRES, IntentionType.EMOCIONAL, IntentionType.ENERGIA]:
            return self._handle_psicologia(message, intention)
        elif intention == IntentionType.CHECKIN:
            return self._handle_checkin(message)
        elif intention == IntentionType.LEGAL:
            return self._handle_legal(message)
        else:
            return self._handle_general(message)
    
    # ==================== HANDLERS ====================
    
    def _handle_gasto(self, message: str) -> Dict[str, Any]:
        """Manejar gasto - extraer monto y PREGUNTAR categoría"""
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
        
        # PREGUNTAR categoría antes de registrar
        return {
            "success": True,
            "message": f"Gastaste ${monto} en qué? (Alimentos, Transporte, Servicios, Entretenimiento, Salud, Personal, Educación, Otro)",
            "action": "WAIT_CATEGORIA",
            "pending_data": {"monto": monto, "categoria": categoria}
        }
    
    def _handle_meta(self, message: str) -> Dict[str, Any]:
        """Manejar meta de ahorro - pregunta plazo y presupuesto"""
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
        
        # Guardar datos pendientes y PREGUNTAR plazo + presupuesto
        self._pending_data = {"nombre": nombre, "monto": monto}
        
        return {
            "success": True,
            "message": f"Creo la meta: {nombre} - ${monto:,.2f}. En cuánto tiempo (meses)? Y cuál es tu ingreso mensual?",
            "action": "WAIT_META_DETAILS"
        }
    
    def _handle_ingreso(self, message: str) -> Dict[str, Any]:
        """Manejar ingreso - pregunta para confirmar si es ingreso"""
        monto_match = re.search(r"(\d+(?:\.\d+)?)", message)
        if not monto_match:
            return {
                "success": True,
                "message": "¿Cuánto ganaste?",
                "action": "WAIT_MONTO"
            }
        
        monto = float(monto_match.group(1))
        
        # Preguntar si es ingreso (no gasto)
        return {
            "success": True,
            "message": f"Entendí ${monto}. Es tu ingreso mensual, cierto?",
            "action": "WAIT_CONFIRMA_INGRESO",
            "pending_data": {"monto": monto}
        }
    
    def _handle_ingreso_confirmado(self, monto: float) -> Dict[str, Any]:
        """Procesar ingreso confirmado"""
        result = self.engine.income_create(
            user_id=self._current_user_id,
            monto=monto,
            fuente="Ingreso mensual",
            descripcion=""
        )
        
        return {
            "success": result["success"],
            "message": result["message"]
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
            respuesta = "Sobre derechos del consumidor: info veraz, garantia de productos, retracto 5 dias. Para casos complejos, consulta un abogado."
        elif "contrato" in temas:
            respuesta = "Sobre contratos: partes, objeto, consentimiento. Evita cláusulas abusivas, todo por escrito. No es consejo legal."
        elif "empleo" in temas:
            respuesta = "Sobre empleo: Liquidacion por despido, horas extras 50%, prestaciones sociales. Te recomiendo un abogado laboral."
        else:
            respuesta = "Sobre ese tema legal, necesito más detalles. Contame brevemente tu situación."
        
        return {
            "success": True,
            "message": respuesta
        }
    
    def _handle_general(self, message: str) -> Dict[str, Any]:
        """Manejar mensaje general - decide si pasar a IA o responder directamente"""
        msg_lower = message.lower().strip()
        
        # Detectar si es saludo trivial
        saludos = ["hola", "buenas", "buenos dias", "buenas noches", "hello", "hi", "que tal", "como estas", "buen dia"]
        if any(msg_lower.startswith(s) for s in saludos):
            return {
                "success": True,
                "message": "Hola! Soy Consiglieri. Te ayudo con finanzas, metas de ahorro, bienestar y temas legales. Qué necesitás?"
            }
        
        # Detectar si es mensaje corto trivial
        if len(message) < 30:
            return {
                "success": True,
                "message": "Estoy listo para ayudarte. Podés decirme: 'gasté X', 'crear meta Y', 'estoy stress' o lo que necesites."
            }
        
        # Solo pasar a IA si es un mensaje largo con contenido real (situación, análisis, consejo)
        # Palabras que indican que necesita análisis real
        palabras_analisis = ["qué crees", "crees que", "me recomiendas", "opinión", "analiza", "situación", "consejo", "piensas", "debería", "flujo", "presupuesto", "deuda"]
        
        if any(p in msg_lower for p in palabras_analisis) and len(message) > 50:
            return {
                "success": True,
                "message": "CONTINUAR_CON_IA",  # Señal para usar chat de IA
                "action": "IA_CHAT"
            }
        
        # Para otros mensajes generales, responder directamente sin IA
        return {
            "success": True,
            "message": "No entendí bien. Puedo ayudarte con: registrar gastos ('gasté 300'), crear metas ('meta moto 2000'), bienestar ('estoy stress') o temas legales. Qué necesitás?"
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
        
        elif action == "WAIT_CATEGORIA":
            # El usuario respondió con la categoría
            categoria = message.strip().title()
            
            # Obtener el monto del pending_data
            pending = getattr(self, '_pending_data', {})
            monto = pending.get('monto', 0)
            
            if monto > 0:
                result = self.engine.expense_create(
                    user_id=self._current_user_id,
                    monto=monto,
                    categoria=categoria,
                    descripcion=message
                )
                self._pending_action = None
                return {
                    "success": result["success"],
                    "message": result["message"]
                }
            else:
                self._pending_action = None
                return {
                    "success": False,
                    "message": "Hubo un error. ¿Cuánto fue?"
                }
        
        elif action == "WAIT_META_DETAILS":
            # El usuario respondió con plazo e ingreso
            # Parsear: "12 meses, 1000 ingresos" o "12 meses / 1000"
            import re
            
            # Buscar número de meses
            meses_match = re.search(r'(\d+)\s*(?:mes|meses)', message.lower())
            # Buscar ingreso mensual
            ingreso_match = re.search(r'(\d+(?:\.\d+)?)', message)
            
            pending = getattr(self, '_pending_data', {})
            nombre = pending.get('nombre', 'Meta')
            monto = pending.get('monto', 0)
            
            meses = int(meses_match.group(1)) if meses_match else 12
            ingreso = float(ingreso_match.group(1)) if ingreso_match else 0
            
            # Crear la meta
            result = self.engine.goal_create(
                user_id=self._current_user_id,
                nombre=nombre,
                meta_amount=monto
            )
            
            # Calcular ahorro mensual necesario
            if meses > 0:
                ahorro_mensual = monto / meses
                
                # Calcular cuanto del ingreso representa
                if ingreso > 0:
                    porcentaje = (ahorro_mensual / ingreso) * 100
                    msg = f"Meta creada: {nombre} - ${monto:,.2f}. Para lograrea en {meses} meses, necesitás ahorrar ${ahorro_mensual:,.2f}/mes ({porcentaje:.1f}% de tu ingreso)."
                else:
                    msg = f"Meta creada: {nombre} - ${monto:,.2f}. Para lograrea en {meses} meses, necesitás ahorrar ${ahorro_mensual:,.2f}/mes."
            else:
                msg = result["message"]
            
            self._pending_action = None
            return {
                "success": True,
                "message": msg
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
                    analisis = "Energia alta. Aprobala!"
                elif energia >= 60:
                    analisis = "Energia bien. Segui asi."
                elif energia >= 40:
                    analisis = "Energia media. Cuidate."
                elif energia >= 20:
                    analisis = "Energia baja. Descanso."
                else:
                    analisis = "Busca apoyo."
                
                return {
                    "success": True,
                    "message": f"Check-in guardado. Energia: {energia}/100. {analisis}"
                }
        
        elif action == "WAIT_CONFIRMA_INGRESO":
            # El usuario confirmó si es ingreso
            msg_lower = message.lower().strip()
            
            # Si dice sí, es ingreso. Si dice no, podría ser gasto
            if any(p in msg_lower for p in ["si", "sí", "yes", "es", "correcto", "si es", "si, es"]):
                pending = getattr(self, '_pending_data', {})
                monto = pending.get('monto', 0)
                result = self.engine.income_create(
                    user_id=self._current_user_id,
                    monto=monto,
                    fuente="Ingreso mensual",
                    descripcion=""
                )
                self._pending_action = None
                return {
                    "success": result["success"],
                    "message": result["message"]
                }
            else:
                # Si no es ingreso, asumir que es gasto
                pending = getattr(self, '_pending_data', {})
                monto = pending.get('monto', 0)
                return {
                    "success": True,
                    "message": f"Entendí ${monto}. En qué categoría? (Alimentos, Transporte, Servicios, Otro)",
                    "action": "WAIT_CATEGORIA",
                    "pending_data": {"monto": monto}
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