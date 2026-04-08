"""
Cliente de Supabase - Repository Pattern
"""

from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from ..config import get_settings


class SupabaseClient:
    """Cliente de Supabase - single responsibility: DB operations"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_instance(cls) -> Client:
        """Singleton del cliente de Supabase"""
        if cls._instance is None:
            settings = get_settings()
            if not settings.supabase_url or not settings.supabase_anon_key:
                raise ValueError("SUPABASE_URL y SUPABASE_ANON_KEY son requeridos")
            cls._instance = create_client(settings.supabase_url, settings.supabase_anon_key)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset para testing"""
        cls._instance = None


class UserRepository:
    """Repositorio de usuarios - encapsula operaciones de users"""
    
    @staticmethod
    def get_by_telegram(telegram_id: int) -> Optional[Dict]:
        client = SupabaseClient.get_instance()
        result = client.table("users").select("*").eq("telegram_id", telegram_id).execute()
        return result.data[0] if result.data else None
    
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
            "presupuesto_mensual": 0  # Default - el bot preguntará al usuario
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
        client = SupabaseClient.get_instance()
        result = client.table("login_tokens").insert({
            "telegram_id": telegram_id
        }).execute()
        return result.data[0]["token"]

    @staticmethod
    def validate(token: str) -> Optional[Dict]:
        """Validar token y retornar datos del usuario si es válido"""
        client = SupabaseClient.get_instance()
        result = (
            client.table("login_tokens")
            .select("*")
            .eq("token", token)
            .eq("used", False)
            .gt("expires_at", "now()")
            .single()
            .execute()
        )
        if not result.data:
            return None

        token_data = result.data

        # Marcar como usado
        client.table("login_tokens").update({"used": True}).eq("id", token_data["id"]).execute()

        # Buscar usuario
        user = UserRepository.get_by_telegram(token_data["telegram_id"])
        return user