# Services package
from .database import (
    SupabaseClient,
    UserRepository,
    ExpenseRepository,
    GoalRepository,
    ConversationRepository
)
from .deepseek import DeepSeekService, AIServiceFactory, get_ia_service
from .whatsapp import WhatsAppService, WhatsAppServiceFactory, get_whatsapp_service
from .automation import (
    BudgetAlert,
    ReminderScheduler,
    WellnessCheck,
    WeeklyReport,
    GoalTracker
)