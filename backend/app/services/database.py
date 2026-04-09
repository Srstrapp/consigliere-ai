"""
Cliente de Supabase - Repository Pattern
"""

from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from ..config import get_settings


class SupabaseClient:
    """Cliente de Supabase - single responsibility: DB operations"""

    _instance: Optional[Client] = None
    _service_instance: Optional[Client] = None

    @classmethod
    def get_instance(cls) -> Client:
        """Singleton del cliente de Supabase (anon key - para operaciones de lectura)"""
        if cls._instance is None:
            settings = get_settings()
            if not settings.supabase_url or not settings.supabase_anon_key:
                raise ValueError("SUPABASE_URL y SUPABASE_ANON_KEY son requeridos")
            cls._instance = create_client(settings.supabase_url, settings.supabase_anon_key)
        return cls._instance

    @classmethod
    def get_service_instance(cls) -> Client:
        """Singleton del cliente de Supabase con Service Role Key (bypass RLS)"""
        if cls._service_instance is None:
            settings = get_settings()
            if not settings.supabase_url or not settings.supabase_service_role_key:
                raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY son requeridos para operaciones administrativas")
            cls._service_instance = create_client(settings.supabase_url, settings.supabase_service_role_key)
        return cls._service_instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset para testing"""
        cls._instance = None
        cls._service_instance = None


class UserRepository:
    """Repositorio de usuarios - encapsula operaciones de users"""
    
    @staticmethod
    def get_by_telegram(telegram_id: int) -> Optional[Dict]:
        client = SupabaseClient.get_instance()
        result = client.table("users").select("*").eq("telegram_id", telegram_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def get_by_id(user_id: str) -> Optional[Dict]:
        """Obtener usuario por ID"""
        client = SupabaseClient.get_instance()
        result = client.table("users").select("*").eq("id", user_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def link_auth_user(user_id: str, auth_user_id: str) -> None:
        """Vincular el usuario de Telegram con el usuario de Supabase Auth"""
        client = SupabaseClient.get_instance()
        client.table("users").update({
            "auth_user_id": auth_user_id
        }).eq("id", user_id).execute()
    
    @staticmethod
    def create(telegram_id: int, nombre: Optional[str] = None) -> Dict:
        client = SupabaseClient.get_instance()
        
        # Verificar si existe
        existing = UserRepository.get_by_telegram(telegram_id)
        if existing:
            return existing
        
        # Crear nuevo
        result = client.table("users").insert({
            "telegram_id": telegram_id,
            "nombre": nombre,
            "presupuesto_mensual": 1000  # Default para que no tenga que pedirlo
        }).execute()
        return result.data[0]
    
    @staticmethod
    def update_presupuesto(user_id: str, presupuesto: float) -> Dict:
        """Actualizar presupuesto mensual del usuario"""
        client = SupabaseClient.get_instance()
        result = client.table("users").update({
            "presupuesto_mensual": presupuesto
        }).eq("id", user_id).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def set_mensaje_pendiente(user_id: str, mensaje: str) -> None:
        """Guardar mensaje pendiente por procesar después de configurar presupuesto"""
        client = SupabaseClient.get_instance()
        client.table("users").update({
            "mensaje_pendiente": mensaje
        }).eq("id", user_id).execute()
    
    @staticmethod
    def get_mensaje_pendiente(user_id: str) -> Optional[str]:
        """Obtener y borrar mensaje pendiente"""
        client = SupabaseClient.get_instance()
        result = client.table("users").select("mensaje_pendiente").eq("id", user_id).execute()
        if result.data and result.data[0].get("mensaje_pendiente"):
            # Limpiar el mensaje pendiente después de obtenerlo
            client.table("users").update({
                "mensaje_pendiente": None
            }).eq("id", user_id).execute()
            return result.data[0]["mensaje_pendiente"]
        return None

    @staticmethod
    def set_pending_state(user_id: str, action: Optional[str], data: Optional[Dict] = None) -> None:
        """Guardar el estado de la acción pendiente en la base de datos"""
        client = SupabaseClient.get_instance()
        client.table("users").update({
            "pending_action": action,
            "pending_data": data
        }).eq("id", user_id).execute()

    @staticmethod
    def get_pending_state(user_id: str) -> Dict[str, Any]:
        """Obtener el estado de la acción pendiente"""
        client = SupabaseClient.get_instance()
        result = client.table("users").select("pending_action, pending_data").eq("id", user_id).execute()
        if result.data:
            return {
                "action": result.data[0].get("pending_action"),
                "data": result.data[0].get("pending_data") or {}
            }
        return {"action": None, "data": {}}

    @staticmethod
    def clear_pending_state(user_id: str) -> None:
        """Limpiar el estado de la acción pendiente"""
        client = SupabaseClient.get_instance()
        client.table("users").update({
            "pending_action": None,
            "pending_data": None
        }).eq("id", user_id).execute()
    
    @staticmethod
    def clear_mensaje_pendiente(user_id: str) -> None:
        """Limpiar mensaje pendiente sin retornarlo"""
        client = SupabaseClient.get_instance()
        client.table("users").update({
            "mensaje_pendiente": None
        }).eq("id", user_id).execute()
    
    @staticmethod
    def get_by_whatsapp(phone: str) -> Optional[Dict]:
        """Obtener usuario por número de WhatsApp"""
        client = SupabaseClient.get_instance()
        result = client.table("users").select("*").eq("whatsapp_phone", phone).execute()
        return result.data[0] if result.data else None
    
    @staticmethod
    def create_by_phone(phone: str, nombre: Optional[str] = None) -> Dict:
        """Crear usuario por número de WhatsApp"""
        client = SupabaseClient.get_instance()
        
        # Verificar si existe
        existing = UserRepository.get_by_whatsapp(phone)
        if existing:
            return existing
        
        # Crear nuevo
        result = client.table("users").insert({
            "whatsapp_phone": phone,
            "nombre": nombre,
            "presupuesto_mensual": 0  # Default - el bot preguntará al usuario
        }).execute()
        return result.data[0]


class ExpenseRepository:
    """Repositorio de gastos - encapsula operaciones de expenses"""
    
    @staticmethod
    def create(user_id: str, monto: float, categoría: str, descripción: Optional[str] = None) -> Dict:
        client = SupabaseClient.get_instance()
        result = client.table("expenses").insert({
            "user_id": user_id,
            "monto": monto,
            "categoría": categoría,
            "descripción": descripción
        }).execute()
        return result.data[0]
    
    @staticmethod
    def get_by_user(user_id: str, limit: int = 10) -> List[Dict]:
        client = SupabaseClient.get_instance()
        result = (
            client.table("expenses")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    
    @staticmethod
    def get_summary(user_id: str) -> Dict[str, Any]:
        client = SupabaseClient.get_instance()
        result = client.table("expenses").select("categoría, monto").eq("user_id", user_id).execute()
        
        if not result.data:
            return {"total": 0, "categorías": {}}
        
        total = sum(r["monto"] for r in result.data)
        categorías = {}
        for r in result.data:
            cat = r["categoría"]
            categorías[cat] = categorías.get(cat, 0) + r["monto"]
        
        return {"total": total, "categorías": categorías}


class IncomeRepository:
    """Repositorio de ingresos - encapsula operaciones de incomes"""
    
    @staticmethod
    def create(user_id: str, monto: float, moneda: str = "USD", fuente: str = "otro", descripción: Optional[str] = None) -> Dict:
        client = SupabaseClient.get_instance()
        result = client.table("incomes").insert({
            "user_id": user_id,
            "monto": monto,
            "moneda": moneda,
            "fuente": fuente,
            "descripción": descripción
        }).execute()
        return result.data[0]
    
    @staticmethod
    def get_by_user(user_id: str, limit: int = 10) -> List[Dict]:
        client = SupabaseClient.get_instance()
        result = (
            client.table("incomes")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data
    
    @staticmethod
    def get_summary(user_id: str) -> Dict[str, Any]:
        client = SupabaseClient.get_instance()
        result = client.table("incomes").select("fuente, monto").eq("user_id", user_id).execute()
        
        if not result.data:
            return {"total": 0, "fuentes": {}}
        
        total = sum(r["monto"] for r in result.data)
        fuentes = {}
        for r in result.data:
            fuente = r["fuente"]
            fuentes[fuente] = fuentes.get(fuente, 0) + r["monto"]
        
        return {"total": total, "fuentes": fuentes}


class GoalRepository:
    """Repositorio de metas - encapsula operaciones de goals"""
    
    @staticmethod
    def create(user_id: str, nombre: str, meta_amount: float, deadline: Optional[str] = None) -> Dict:
        client = SupabaseClient.get_instance()
        result = client.table("goals").insert({
            "user_id": user_id,
            "nombre": nombre,
            "meta_amount": meta_amount,
            "deadline": deadline
        }).execute()
        return result.data[0]
    
    @staticmethod
    def get_by_user(user_id: str) -> List[Dict]:
        client = SupabaseClient.get_instance()
        result = (
            client.table("goals")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    
    @staticmethod
    def update_progress(goal_id: str, current_amount: float) -> Dict:
        client = SupabaseClient.get_instance()
        result = client.table("goals").update({"current_amount": current_amount}).eq("id", goal_id).execute()
        return result.data[0]


class ConversationRepository:
    """Repositorio de conversaciones - encapsula operaciones de conversations"""
    
    @staticmethod
    def save(user_id: str, messages: List[Dict], dominio: str = "general") -> Dict:
        """Guardar conversación con dominio específico"""
        client = SupabaseClient.get_instance()
        
        # Obtener la última conversación del usuario en ese dominio o crear nueva
        existing = ConversationRepository.get_by_dominio(user_id, dominio)
        
        if existing:
            # Actualizar la conversación existente
            result = client.table("conversations").update({
                "messages": messages
            }).eq("id", existing["id"]).execute()
            return result.data[0] if result.data else existing
        else:
            # Crear nueva conversación con dominio
            result = client.table("conversations").insert({
                "user_id": user_id,
                "messages": messages,
                "dominio": dominio
            }).execute()
            return result.data[0]
    
    @staticmethod
    def get_by_dominio(user_id: str, dominio: str) -> Optional[Dict]:
        """Obtener conversación por usuario y dominio específico"""
        client = SupabaseClient.get_instance()
        result = (
            client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .eq("dominio", dominio)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    
    @staticmethod
    def get_last(user_id: str) -> List[Dict]:
        client = SupabaseClient.get_instance()
        result = (
            client.table("conversations")
            .select("messages")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0]["messages"] if result.data else []


class LoginTokenRepository:
    """Repositorio de tokens de login para acceso desde el bot al dashboard"""

    @staticmethod
    def create(telegram_id: int) -> str:
        """Crear token de login válido 1 hora y retornar el token string"""
        import uuid
        client = SupabaseClient.get_instance()
        
        # Generar token único
        token = str(uuid.uuid4())
        
        # Insertar con user_id (no telegram_id)
        from datetime import datetime, timedelta
        expires = datetime.utcnow() + timedelta(hours=1)
        
        # Primero buscar el user_id por telegram_id
        user = UserRepository.get_by_telegram(telegram_id)
        user_id = user["id"] if user else None
        
        result = client.table("login_tokens").insert({
            "user_id": user_id,
            "token_hash": token,
            "expires_at": expires.isoformat()
        }).execute()
        return token

    @staticmethod
    def validate(token: str) -> Optional[Dict]:
        """Validar token y retornar datos del usuario si es válido"""
        client = SupabaseClient.get_instance()
        result = (
            client.table("login_tokens")
            .select("*")
            .eq("token_hash", token)
            .eq("is_used", False)
            .gt("expires_at", "now()")
            .single()
            .execute()
        )
        if not result.data:
            return None

        token_data = result.data

        # Marcar como usado
        client.table("login_tokens").update({"is_used": True}).eq("id", token_data["id"]).execute()

        # Buscar usuario
        user = UserRepository.get_by_id(token_data["user_id"])
        return user


class DebtRepository:
    """Repositorio de deudas - encapsula operaciones de debts"""
    
    @staticmethod
    def create(user_id: str, acreedor: str, monto_total: float, fecha_vencimiento: Optional[str] = None) -> Dict:
        client = SupabaseClient.get_instance()
        result = client.table("debts").insert({
            "user_id": user_id,
            "acreedor": acreedor,
            "monto_total": monto_total,
            "fecha_vencimiento": fecha_vencimiento,
            "estado": "pendiente"
        }).execute()
        return result.data[0]
    
    @staticmethod
    def get_by_user(user_id: str) -> List[Dict]:
        client = SupabaseClient.get_instance()
        result = (
            client.table("debts")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    
    @staticmethod
    def update_pago(debt_id: str, monto_pagado: float) -> Dict:
        client = SupabaseClient.get_instance()
        
        # Obtener deuda actual
        result = client.table("debts").select("*").eq("id", debt_id).single().execute()
        if not result.data:
            return None
        
        debt = result.data
        nuevo_pagado = (debt.get("monto_pagado", 0) or 0) + monto_pagado
        
        # Actualizar estado si está pagado
        estado = "pagado" if nuevo_pagado >= debt["monto_total"] else "pendiente"
        
        result = client.table("debts").update({
            "monto_pagado": nuevo_pagado,
            "estado": estado
        }).eq("id", debt_id).execute()
        return result.data[0]


class EmotionalCheckinRepository:
    """Repositorio de check-ins emocionales - encapsula operaciones de emotional_checkins"""
    
    @staticmethod
    def create(user_id: str, nivel_energia: int, emocion_principal: str = "", notas: str = "") -> Dict:
        client = SupabaseClient.get_instance()
        result = client.table("emotional_checkins").insert({
            "user_id": user_id,
            "nivel_energia": nivel_energia,
            "emocion_principal": emocion_principal,
            "notas": notas
        }).execute()
        return result.data[0]
    
    @staticmethod
    def get_latest(user_id: str) -> Optional[Dict]:
        client = SupabaseClient.get_instance()
        result = (
            client.table("emotional_checkins")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    
    @staticmethod
    def get_history(user_id: str, dias: int = 7) -> List[Dict]:
        client = SupabaseClient.get_instance()
        result = (
            client.table("emotional_checkins")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(dias)
            .execute()
        )
        return result.data