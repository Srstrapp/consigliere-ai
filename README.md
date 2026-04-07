# 🎯 Consigliere AI 🤖

> Tu asistente IA para finanzas, bienestar emocional y consultas legales.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)
![Supabase](https://img.shields.io/badge/Supabase-Database-3ECF8E)

## 🌟 Características

- **💰 Finanzas**: Registrá gastos, configurá presupuestos, seguí metas financieras
- **🧠 Metanoia**: Check-in de bienestar emocional, apoyo motivacional  
- **⚖️ Legal**: Consultas legales en lenguaje sencillo
- **🧠 IA**: Potenciado por DeepSeek para respuestas inteligentes
- **💾 Persistencia**: Supabase como base de datos
- **🎯 Contexto Aislado**: Sistema de dominios independiente (finanzas/metanoia/legal)
- **☁️ Deploy**: Listo para Railway

## 🚀 Deploy en Railway

### Prerrequisitos

- Cuenta de [Railway](https://railway.app)
- Cuenta de [Supabase](https://supabase.com)
- Bot de Telegram (obtené el token desde @BotFather)
- API Key de [DeepSeek](https://platform.deepseek.com)

### 1. Deploy

1. Hacé fork de este repo o clonalo
2. Iniciá sesión en [Railway](https://railway.app)
3. Click **New Project** → **Deploy from GitHub repo**
4. Seleccioná tu repositorio `consigliere-ai`
5. Railway detectará automaticamente el backend Python

### 2. Variables de entorno

En Railway, configurá las siguientes variables:

| Variable | Descripción |
|----------|-------------|
| `SUPABASE_URL` | URL de tu proyecto Supabase |
| `SUPABASE_ANON_KEY` | Anon key de Supabase |
| `DEEPSEEK_API_KEY` | Tu API key de DeepSeek |
| `TELEGRAM_BOT_TOKEN` | Token de tu bot de Telegram |

### 3. Deploy

Click **Deploy** y esperá a que build.

### 4. Configurar Webhook de Telegram

Una vez deployado, configurá el webhook:

```bash
# Reemplazá YOUR_RAILWAY_URL con tu URL de Railway
curl -X POST "https://TU-RAILWAY-URL.io/webhook/telegram"
```

O usá la API de Telegram:
```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://TU-RAILWAY-URL.io/webhook/telegram
```

---

## 🖥️ Desarrollo Local

### Prerrequisitos

- Python 3.11+
- Cuenta de Supabase
- Bot de Telegram

### 1. Clonar y setup

```bash
git clone https://github.com/Srstrapp/consigliere-ai.git
cd consigliere-ai
cd backend
```

### 2. Crear entorno virtual

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables

```bash
# Crear archivo .env
cp .env.example .env
# Editá con tus credenciales
```

### 5. Ejecutar

```bash
uvicorn app.main:app --reload
```

### 6. Verificar

```bash
curl http://localhost:8000
curl http://localhost:8000/health
```

---

## 📱 Configurar Telegram

1. Hablá con @BotFather en Telegram
2. Enviá `/newbot` y seguí las instrucciones
3. Copiá el TOKEN y agregalo a tu variable `TELEGRAM_BOT_TOKEN`
4. Configurá el webhook:
   ```
   https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://TU-DOMINIO/webhook/telegram
   ```

---

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

---

## 🧠 Sistema de Dominios

Consigliere usa un sistema de **contexto aislado por dominio**:

```
Usuario: "gasté 500 en taxi"     → Dominio: finanzas
Usuario: "extraño a mi papá"     → Dominio: metanoia
Usuario: "cuánto me queda?"     → Solo usa historial de finanzas
```

| Dominio | Contenido |
|---------|-----------|
| `finanzas` | Gastos, presupuestos, metas |
| `metanoia` | Bienestar emocional |
| `legal` | Consultas legales |
| `general` | Conversaciones generales |

---

## 📁 Estructura

```
consigliere-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuración
│   │   └── services/
│   │       ├── telegram.py      # Handlers del bot
│   │       ├── deepseek.py      # Cliente de IA
│   │       └── database.py      # Repositorios de Supabase
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🤝 Contribuir

1. Fork del repo
2. Crear branch: `git checkout -b feature/nueva-caracteristica`
3. Commit y push
4. Abrir Pull Request

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE)

---

⭐️ Hecho con ❤️ para la presentación