"""
Consiglieri Execution Engine
Ejecuta funciones de Supabase desde las skills
"""

from typing import Optional, Dict, Any, List
from datetime import date
import uuid
import logging

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Motor de ejecución que ejecuta funciones de Supabase
    baseado en las skills de Consiglieri
    """
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self._user_cache = {}
    
    # ==================== FINANZAS ====================
    
    def expense_create(
        self, 
        user_id: str, 
        monto: float, 
        categoria: str = "otro", 
        descripcion: str = "",
        fecha: Optional[date] = None
    ) -> Dict[str, Any]:
        """Registrar gasto en Supabase"""
        try:
            from app.services.database import ExpenseRepository
            
            expense = ExpenseRepository.create(
                user_id=user_id,
                monto=monto,
                categoria=categoria,
                descripcion=descripcion or "",
                fecha=fecha
            )
            
            return {
                "success": True,
                "message": f"✅ Gasto registrado: ${monto:,.2f} en {categoria}",
                "data": expense
            }
        except Exception as e:
            logger.error(f"Error creando gasto: {e}")
            return {
                "success": False,
                "message": f"Error guardando gasto: {str(e)}",
                "data": None
            }
    
    def income_create(
        self,
        user_id: str,
        monto: float,
        fuente: str = "otro",
        descripcion: str = "",
        moneda: str = "USD",
        fecha: Optional[date] = None
    ) -> Dict[str, Any]:
        """Registrar ingreso en Supabase"""
        try:
            from app.services.database import IncomeRepository
            
            income = IncomeRepository.create(
                user_id=user_id,
                monto=monto,
                fuente=fuente,
                descripcion=descripcion or "",
                moneda=moneda,
                fecha=fecha
            )
            
            return {
                "success": True,
                "message": f"💰 Ingreso registrado: ${monto:,.2f} de {fuente}",
                "data": income
            }
        except Exception as e:
            logger.error(f"Error creando ingreso: {e}")
            return {
                "success": False,
                "message": f"Error guardando ingreso: {str(e)}",
                "data": None
            }
    
    def goal_create(
        self,
        user_id: str,
        nombre: str,
        meta_amount: float,
        deadline: Optional[date] = None
    ) -> Dict[str, Any]:
        """Crear meta de ahorro"""
        try:
            from app.services.database import GoalRepository
            
            goal = GoalRepository.create(
                user_id=user_id,
                nombre=nombre,
                meta_amount=meta_amount,
                deadline=deadline
            )
            
            return {
                "success": True,
                "message": f"🎯 Meta creada: {nombre} - ${meta_amount:,.2f}",
                "data": goal
            }
        except Exception as e:
            logger.error(f"Error creando meta: {e}")
            return {
                "success": False,
                "message": f"Error creando meta: {str(e)}",
                "data": None
            }
    
    def goal_update_progress(
        self,
        user_id: str,
        goal_id: str,
        monto: float
    ) -> Dict[str, Any]:
        """Actualizar progreso de meta"""
        try:
            from app.services.database import GoalRepository
            
            goal = GoalRepository.update_progress(goal_id, monto)
            
            if goal:
                progreso = (goal["current_amount"] / goal["meta_amount"]) * 100
                return {
                    "success": True,
                    "message": f"📈 Progreso: ${goal['current_amount']:,.2f}/${goal['meta_amount']:,.2f} ({progreso:.1f}%)",
                    "data": goal
                }
            return {
                "success": False,
                "message": "Meta no encontrada",
                "data": None
            }
        except Exception as e:
            logger.error(f"Error actualizando meta: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }
    
    def goal_get_all(self, user_id: str) -> Dict[str, Any]:
        """Obtener todas las metas del usuario"""
        try:
            from app.services.database import GoalRepository
            
            goals = GoalRepository.get_by_user(user_id)
            
            if not goals:
                return {
                    "success": True,
                    "message": "No tenés metas aún. ¿Querés crear una?",
                    "data": []
                }
            
            # Formatear respuesta
            msg = "📊 Tus metas:\n"
            for g in goals:
                progreso = (g["current_amount"] / g["meta_amount"]) * 100 if g["meta_amount"] > 0 else 0
                msg += f"• {g['nombre']}: ${g['current_amount']:,.2f}/${g['meta_amount']:,.2f} ({progreso:.0f}%)\n"
            
            return {
                "success": True,
                "message": msg,
                "data": goals
            }
        except Exception as e:
            logger.error(f"Error obteniendo metas: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }
    
    def debt_create(
        self,
        user_id: str,
        acreedor: str,
        monto_total: float,
        fecha_vencimiento: Optional[date] = None
    ) -> Dict[str, Any]:
        """Registrar deuda"""
        try:
            from app.services.database import DebtRepository
            
            debt = DebtRepository.create(
                user_id=user_id,
                acreedor=acreedor,
                monto_total=monto_total,
                fecha_vencimiento=fecha_vencimiento
            )
            
            return {
                "success": True,
                "message": f"💳 Deuda registrada: ${monto_total:,.2f} con {acreedor}",
                "data": debt
            }
        except Exception as e:
            logger.error(f"Error creando deuda: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }
    
    def budget_get(self, user_id: str) -> Dict[str, Any]:
        """Obtener presupuesto mensual"""
        try:
            from app.services.database import UserRepository
            
            user = UserRepository.get_by_id(user_id)
            
            if not user:
                return {
                    "success": False,
                    "message": "Usuario no encontrado",
                    "data": None
                }
            
            presupuesto = user.get("presupuesto_mensual", 1000)
            
            return {
                "success": True,
                "message": f"💵 Tu presupuesto: ${presupuesto:,.2f}/mes",
                "data": {"presupuesto": presupuesto}
            }
        except Exception as e:
            logger.error(f"Error obteniendo presupuesto: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }
    
    def budget_set(self, user_id: str, monto: float) -> Dict[str, Any]:
        """Establecer presupuesto mensual"""
        try:
            from app.services.database import UserRepository
            
            UserRepository.update_presupuesto(user_id, monto)
            
            return {
                "success": True,
                "message": f"✅ Presupuesto actualizado: ${monto:,.2f}/mes",
                "data": {"presupuesto": monto}
            }
        except Exception as e:
            logger.error(f"Error estableciendo presupuesto: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }
    
    # ==================== PSICOLOGÍA ====================
    
    def emotional_checkin_create(
        self,
        user_id: str,
        nivel_energia: int,
        emocion_principal: str = "",
        notas: str = ""
    ) -> Dict[str, Any]:
        """Registrar check-in emocional"""
        try:
            from app.services.database import EmotionalCheckinRepository
            
            checkin = EmotionalCheckinRepository.create(
                user_id=user_id,
                nivel_energia=nivel_energia,
                emocion_principal=emocion_principal,
                notas=notas
            )
            
            # Análisis según nivel
            if nivel_energia >= 80:
                analisis = "🚀 Energía excelente. Aprovechá!"
            elif nivel_energia >= 60:
                "✅ Energia bien. Mantené el ritmo."
            elif nivel_energia >= 40:
                "⚠️ Energia media. Cuidate y tomá pausas."
            elif nivel_energia >= 20:
                "🛑 Energia baja. Descanso recomendado."
            else:
                "🆘 Energia muy baja. Buscá apoyo."
            
            return {
                "success": True,
                "message": f"📊 Check-in guardado. Nivel: {nivel_energia}/100\n{analisis}",
                "data": checkin
            }
        except Exception as e:
            logger.error(f"Error en check-in: {e}")
            return {
                "success": False,
                "message": f"Error guardando check-in: {str(e)}",
                "data": None
            }
    
    def emotional_get_latest(self, user_id: str) -> Dict[str, Any]:
        """Obtener último check-in"""
        try:
            from app.services.database import EmotionalCheckinRepository
            
            checkin = EmotionalCheckinRepository.get_latest(user_id)
            
            if not checkin:
                return {
                    "success": True,
                    "message": "No hay check-ins registrados. ¿Cómo estás hoy?",
                    "data": None
                }
            
            return {
                "success": True,
                "message": f"Último check-in: {checkin['nivel_energia']}/100 - {checkin.get('emocion_principal', 'N/A')}",
                "data": checkin
            }
        except Exception as e:
            logger.error(f"Error obteniendo check-in: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }
    
    def emotional_get_history(
        self,
        user_id: str,
        dias: int = 7
    ) -> Dict[str, Any]:
        """Obtener historial de check-ins"""
        try:
            from app.services.database import EmotionalCheckinRepository
            
            checkins = EmotionalCheckinRepository.get_history(user_id, dias)
            
            if not checkins:
                return {
                    "success": True,
                    "message": f"No hay check-ins en los últimos {dias} días",
                    "data": []
                }
            
            # Calcular promedio
            avg = sum(c["nivel_energia"] for c in checkins) / len(checkins)
            
            return {
                "success": True,
                "message": f"Promedio últimos {dias} días: {avg:.0f}/100 ({len(checkins)} registros)",
                "data": checkins
            }
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }
    
    # ==================== PSICOLOGÍA ====================


# ==================== FACTORY ====================

class ExecutionEngineFactory:
    """Factory para obtener el execution engine"""
    
    _instance: Optional[ExecutionEngine] = None
    
    @classmethod
    def get_engine(cls, supabase_client=None) -> ExecutionEngine:
        if cls._instance is None:
            cls._instance = ExecutionEngine(supabase_client)
        return cls._instance
    
    @classmethod
    def reset(cls):
        cls._instance = None


def get_execution_engine() -> ExecutionEngine:
    """Obtener instancia del execution engine"""
    return ExecutionEngineFactory.get_engine()