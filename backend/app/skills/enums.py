"""
Consiglieri - Enum de Estados de Usuario
Define los estados posibles del usuario en el sistema
"""

from enum import Enum


class UserState(Enum):
    """Estados del usuario en el bot"""
    NEW_NO_AUTH = "new_no_auth"           # Usuario creado, sin registro en dashboard
    REGISTERED = "registered"             # Usuario con auth_user_id configurado
    PENDING_ACTION = "pending_action"    # Usuario esperando respuesta para acción


class ActionState(Enum):
    """Estados de acciones pendientes"""
    NONE = "none"
    WAIT_MONTO = "wait_monto"
    WAIT_CATEGORIA = "wait_categoria"
    WAIT_CONFIRMA_INGRESO = "wait_confirma_ingreso"
    WAIT_META_DETAILS = "wait_meta_details"
    WAIT_ENERGIA = "wait_energia"


class IntentionType(Enum):
    """Tipos de intención detectados"""
    GASTO = "gasto"
    INGRESO = "ingreso"
    META = "meta"
    DEUDA = "deuda"
    PRESUPUESTO = "presupuesto"
    ESTRES = "estres"
    EMOCIONAL = "emocional"
    ENERGIA = "energia"
    CHECKIN = "checkin"
    LEGAL = "legal"
    GENERAL = "general"