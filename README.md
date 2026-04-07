# 🎯 Consigliere AI 🤖

> Tu asistente IA omnicanal para finanzas, bienestar emocional y consultas legales.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Evolution_API-25D366)
![Supabase](https://img.shields.io/badge/Supabase-Database-3ECF8E)

## 🌟 Características

- **💰 Finanzas**: Registrá gastos, configurá presupuestos, seguí metas financieras
- **🧠 Metanoia**: Check-in de bienestar emocional, apoyo motivacional  
- **⚖️ Legal**: Consultas legales en lenguaje sencillo
- **🌐 Omnicanal**: Funciona en Telegram y WhatsApp (Evolution API)
- **🧠 IA**: Potenciado por DeepSeek para respuestas inteligentes
- **💾 Persistencia**: Supabase como base de datos
- **🎯 Contexto Aislado**: Sistema de dominios independiente (finanzas/metanoia/legal)

## 🚀 Quick Start

### Prerrequisitos

- Python 3.11+
- Docker y Docker Compose
- Cuenta de Supabase
- Bot de Telegram (obtené el token desde @BotFather)
- (Opcional) Evolution API para WhatsApp

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/consigliere-ai.git
cd consigliere-ai
```

### 2. Configurar variables de entorno

```bash
cp backend/.env.example backend/.env
# Editá el .env con tus credenciales
```

### 3. Levantar con Docker

```bash
docker-compose up --build
```

Esto levanta:
- **Backend** (puerto 8000): API de Consigliere
- **Evolution API** (puerto 8080): Para WhatsApp
- **PostgreSQL**: Base de datos para Evolution

### 4. Verificar que esté corriendo

```bash
# API
curl http://localhost:8000

# Health
curl http://localhost:8000/health

# Evolution API (para WhatsApp)
curl http://localhost:8080
```

## 📱 Configurar Telegram

1. Hablá con @BotFather en Telegram
2. Enviá `/newbot` y seguí las instrucciones
3. Copiá el TOKEN y agregalo a tu `.env`

## 📱 Configurar WhatsApp (Opcional)

1. Andá a `http://localhost:8080`
2. Login con: `atendai` / `evolucion2024`
3. Ir a **Instances** → crear nueva instancia
4. Escaneá el QR con tu WhatsApp
5. Ir a **Evolution Bot** → Create Bot:
   - **Instance**: tu instancia
   - **apiUrl**: `http://backend:8000/bot/evolution`
   - **triggerType**: `all`
   - **triggerOperator**: `none`

## 📁 Estructura del Proyecto

```
consigliere-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # Entry point de FastAPI
│   │   ├── config.py            # Configuración (Settings)
│   │   └── services/
│   │       ├── telegram.py      # Handlers del bot de Telegram
│   │       ├── whatsapp.py      # Servicio de WhatsApp (Evolution API)
│   │       ├── deepseek.py      # Cliente de IA (DeepSeek)
│   │       └── database.py      # Repositorios de Supabase
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml           # Backend + Evolution API + PostgreSQL
├── .gitignore
└── README.md
```

## 🛠️ Desarrollo Local (Sin Docker)

```bash
# Entrar al backend
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editá las credenciales

# Ejecutar
uvicorn app.main:app --reload

# Ver: http://localhost:8000
```

## 📡 Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Health check básico |
| `/health` | GET | Estado detallado de servicios |
| `/api/usuario/{telegram_id}` | GET | Datos del usuario |
| `/api/{telegram_id}/gastos` | GET | Lista de gastos |
| `/api/{telegram_id}/metas` | GET | Lista de metas |
| `/bot/evolution` | POST | Endpoint para Evolution Bot (WhatsApp) |
| `/webhook/whatsapp` | POST | Webhook de WhatsApp |

## 🎯 Comandos del Bot

| Comando | Descripción |
|---------|-------------|
| `/start` | Iniciar el bot |
| `/gastos` | Ver gastos recientes |
| `/metas` | Ver metas financieras |
| `/bienestar` | Check-in emocional |
| `/presupuesto` | Ver estado del presupuesto |
| `/reporte` | Reporte semanal |
| `/ayuda` | Mostrar ayuda |

## 🧠 Sistema de Dominios

Consigliere usa un sistema de **contexto aislado por dominio** que evita "context bleeding":

```
Usuario: "gasté 500 en taxi"     → Dominio: finanzas (session: finanzas_123)
Usuario: "extraño a mi papá"     → Dominio: metanoia (session: metanoia_123)
Usuario: "cuánto me queda?"     → Solo usa historial de finanzas, NO arrastra lo emocional
```

| Dominio | Contenido |
|---------|-----------|
| `finanzas` | Gastos, presupuestos, metas |
| `metanoia` | Bienestar emocional |
| `legal` | Consultas legales |
| `general` | Conversaciones generales |

## 🧪 Testing

```bash
# Tests con pytest
cd backend
pytest

# Con coverage
pytest --cov=app
```

## 🤝 Contribuir

1. Fork del repositorio
2. Crear una rama (`git checkout -b feature/nueva-caracteristica`)
3. Commit de tus cambios
4. Push a la rama
5. Abrir un Pull Request

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE)

## 👤 Autor

**Tu nombre**  
- GitHub: [@tu-usuario](https://github.com/tu-usuario)

---

⭐️ Si te gusta este proyecto, dale una estrella!