"""
Servicios de Automatización
Módulo de alertas y notificaciones automáticas
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncio
from ..services.database import UserRepository, ExpenseRepository, GoalRepository


class BudgetAlert:
    """
    Sistema de alertas de presupuesto
    Notifica cuando el usuario supera umbrales de gasto
    """
    
    # UMBRALES CONFIGURABLES
    UMBRAL_ADVERTENCIA = 0.70  # 70% del presupuesto
    UMBRAL_CRITICO = 0.90      # 90% del presupuesto
    UMBRAL_EXCEDIDO = 1.00      # 100%
    
    @staticmethod
    async def check_spending(user_id: str, presupuesto_mensual: float = None) -> Optional[str]:
        """
        Verificar si el usuario superó umbrales de gasto
        Si no hay presupuesto, retorna None (no hay alertas)
        """
        if presupuesto_mensual is None or presupuesto_mensual <= 0:
            return None
            
        # Obtener gastos del mes actual
        gastos = ExpenseRepository.get_by_user(user_id, limit=1000)
        
        # Filtrar solo gastos del mes actual
        ahora = datetime.now()
        gastos_mes = [
            g for g in gastos 
            if g.get("fecha") and 
            datetime.strptime(str(g["fecha"]), "%Y-%m-%d").month == ahora.month and
            datetime.strptime(str(g["fecha"]), "%Y-%m-%d").year == ahora.year
        ]
        
        total_gastado = sum(g.get("monto", 0) for g in gastos_mes)
        porcentaje = total_gastado / presupuesto_mensual
        
        # Generar alerta según umbral
        if porcentaje >= BudgetAlert.UMBRAL_EXCEDIDO:
            return BudgetAlert._alert_excedido(total_gastado, presupuesto_mensual)
        elif porcentaje >= BudgetAlert.UMBRAL_CRITICO:
            return BudgetAlert._alert_critico(total_gastado, presupuesto_mensual, porcentaje)
        elif porcentaje >= BudgetAlert.UMBRAL_ADVERTENCIA:
            return BudgetAlert._alert_advertencia(total_gastado, presupuesto_mensual, porcentaje)
        
        return None
    
    @staticmethod
    def _alert_excedido(gastado: float, presupuesto: float) -> str:
        return f"""🚨 *ALERTA CRÍTICA - Presupuesto Excedido*

Ya gastaste ${gastado:.2f} de ${presupuesto:.2f} ({(gastado/presupuesto)*100:.0f}%)

⚠️ Has superado tu presupuesto mensual. 
Recomendaciones:
• Revisa tus gastos de esta semana
• Considera reducir gastos en categorías no esenciales
• Evita compras grandes hasta el próximo mes

¿Te ayudo a analizar dónde se fue el dinero?"""
    
    @staticmethod
    def _alert_critico(gastado: float, presupuesto: float, porcentaje: float) -> str:
        return f"""⚠️ *Alerta de Presupuesto - {(porcentaje*100):.0f}% Usado*

Llevas ${gastado:.2f} de ${presupuesto:.2f} este mes.

💡 Te quedan aproximadamente ${presupuesto-gastado:.2f} para las próximas semanas.
Consejos:
• Prioriza gastos esenciales
• Reduce gastos opcionales
• Registrás cada gasto para mantener control

¿Necesitás ayuda para ajustar el presupuesto?"""
    
    @staticmethod
    def _alert_advertencia(gastado: float, presupuesto: float, porcentaje: float) -> str:
        return f"""💡 *Recordatorio de Presupuesto*

Llevas {(porcentaje*100):.0f}% del presupuesto usado (${gastado:.2f} de ${presupuesto:.2f})

Tu presupuesto está en zona de advertencia.
¿Quieres que te ayude a revisar tus gastos por categoría?"""


class ReminderScheduler:
    """
    Programador de recordatorios automáticos
    """
    
    # Tipos de recordatorios
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"
    
    @staticmethod
    def get_daily_reminder_message() -> str:
        return """🌅 *Buenos días!*

Aquí tienes tu resumen de hoy:
• Revisa tus gastos de ayer
• Mantén tus metas en perspectiva
• Tu bienestar es importante

¿Hay algo en lo que pueda ayudarte hoy?"""
    
    @staticmethod
    def get_weekly_reminder_message() -> str:
        return """📅 *Resumen Semanal*

¡Es hora de tu check-in semanal!

¿Te gustaría:
1. Ver el resumen de tus gastos de esta semana?
2. Revisar el progreso de tus metas?
3. Comentar cómo te sientes (Metanoia)?
4. Hablar de algún tema legal?

respondeme con el número o lo que necesites!"""
    
    @staticmethod
    def get_goal_celebration(goal_name: str, progress: float) -> str:
        return f"""🎉 *¡Felicidades!*

Tu meta "{goal_name}" ha alcanzado el {progress:.0f}% de progreso!

¡Sigue así! Cada paso cuenta hacia tus objetivos.
¿Querés celebrar estableciendo una nueva meta?"""


class WellnessCheck:
    """
    Sistema de check-in de bienestar (Metanoia Proactivo)
    """
    
    # Preguntas para check-in emocional
    PREGUNTAS_BIENVENIDA = [
        "¿Cómo te sientes hoy en una escala del 1 al 10?",
        "¿Hay algo que te esté preocupando?",
        "¿Has tomado tus pausas hoy?",
        "¿Cómo está tu nivel de energía?",
    ]
    
    @staticmethod
    def should_trigger_checkin(user_id: str, dias_sin_actividad: int = 3) -> bool:
        """
        Determina si debe hacer check-in proactivo
        Basado en días sin actividad del usuario
        """
        # Por ahora returning True para demo
        # En producción, verificar última actividad en DB
        return True
    
    @staticmethod
    def get_checkin_message() -> str:
        return """🧠 *Check-in de Bienestar - Metanoia*

Hola! Quiero saber como estas.

En una escala del 1-10, como te sientes hoy?
(1 = muy mal, 10 = excelentemente)

Y opcional: hay algo que te gustaria compartir o que te preocupe?"""
    
    @staticmethod
    def analyze_burnout_risk(mensaje: str) -> Dict[str, any]:
        """
        Analiza riesgo de burnout basado en mensaje del usuario
        """
        keywords_negativos = [
            "estrés", "stress", "cansado", "fatigado", "abrumado",
            "no puedo", "agotado", "desmotivado", "frustrado", "quemado"
        ]
        
        mensaje_lower = mensaje.lower()
        count = sum(1 for kw in keywords_negativos if kw in mensaje_lower)
        
        if count >= 3:
            nivel = "ALTO"
            respuesta = """🛑 *Señales de agotamiento detectadas*

Parece que estás llevando mucho. quiero que sepas:

1. Está bien no estar bien
2. Las pausas no son lujo, son necesidad
3. Hablar ayuda - aquí estoy para escucharte

¿Te gustaría que hagamos una pausa juntos? 
Puedo sugerirte ejercicios de respiración o simplemente conversar."""
        
        elif count >= 1:
            nivel = "MEDIO"
            respuesta = """💛 *Nota de bienestar*

Noté que estás pasando por un momento demanding.

Recuerda:
• Tu salud mental importa
• Las pausas son importantes
• Estás haciendo un gran trabajo

¿Quieres conversar sobre lo que te preocupa?"""
        else:
            nivel = "BAJO"
            respuesta = None
        
        return {
            "nivel": nivel,
            "respuesta": respuesta,
            "keywords_encontrados": count
        }


class WeeklyReport:
    """
    Generador de reportes semanales automáticos
    """
    
    @staticmethod
    async def generate_report(user_id: str) -> str:
        """
        Genera reporte semanal de gastos
        """
        gastos = ExpenseRepository.get_by_user(user_id, limit=100)
        metas = GoalRepository.get_by_user(user_id)
        
        # Calcular totales de la semana
        ahora = datetime.now()
        hace_7_dias = ahora - timedelta(days=7)
        
        gastos_semana = [
            g for g in gastos
            if g.get("created_at") and 
            datetime.fromisoformat(str(g["created_at"]).replace("Z", "+00:00")).date() >= hace_7_dias.date()
        ]
        
        total_semana = sum(g.get("monto", 0) for g in gastos_semana)
        
        # Gastos por categoría
        categorias = {}
        for g in gastos_semana:
            cat = g.get("categoría", "otro")
            categorias[cat] = categorias.get(cat, 0) + g.get("monto", 0)
        
        # Estado de metas
        metas_status = []
        for m in metas:
            prog = (m.get("current_amount", 0) / m.get("meta_amount", 1)) * 100
            metas_status.append({
                "nombre": m.get("nombre"),
                "progreso": prog
            })
        
        # Construir reporte
        reporte = f"""📊 *Reporte Semanal - Consigliere*

📅 Resumen de los últimos 7 días:

💰 *Gastos:* ${total_semana:.2f}
"""
        
        if categorias:
            reporte += "\n📂 *Por categoría:*\n"
            for cat, monto in sorted(categorias.items(), key=lambda x: x[1], reverse=True):
                reporte += f"• {cat}: ${monto:.2f}\n"
        
        if metas_status:
            reporte += "\n🎯 *Progreso de metas:*\n"
            for m in metas_status:
                reporte += f"• {m['nombre']}: {m['progreso']:.0f}%\n"
        
        reporte += """
¿Querés que profundice en algún aspecto del reporte?
1. Análisis más detallado
2. Ajustar presupuesto
3. Nueva meta
4. Hablar de bienestar (Metanoia)"""
        
        return reporte


class GoalTracker:
    """
    Seguimiento automático de metas
    """
    
    @staticmethod
    def check_milestones(user_id: str) -> List[Dict]:
        """
        Verificar si se alcanzaron hitos en las metas
        """
        metas = GoalRepository.get_by_user(user_id)
        
        hitos = []
        for m in metas:
            current = m.get("current_amount", 0)
            meta = m.get("meta_amount", 1)
            progreso = (current / meta) * 100 if meta > 0 else 0
            
            # Hitos en 25%, 50%, 75%, 100%
            for pct in [25, 50, 75, 100]:
                if progreso >= pct:
                    hitos.append({
                        "goal_name": m.get("nombre"),
                        "progreso": progreso,
                        "hito": pct
                    })
        
        return hitos
    
    @staticmethod
    def get_motivational_message(progreso: float) -> str:
        """
        Mensaje motivacional según progreso
        """
        if progreso >= 100:
            return "🎉¡Felicidades! Has alcanzado tu meta!"
        elif progreso >= 75:
            return "💪 ¡Casi ahí! Solo un poco más para llegar a tu meta."
        elif progreso >= 50:
            return "🌟 ¡A mitad de camino! Estás haciendo un gran trabajo."
        elif progreso >= 25:
            return "👍 ¡Buen comienzo! Sigue así."
        else:
            return "🚀 Cada paso cuenta. ¡Sigue adelante!"