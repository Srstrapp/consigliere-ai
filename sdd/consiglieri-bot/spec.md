# Consiglieri Bot - Specification

## Purpose

Define el comportamiento del bot Consiglieri para manejar diferentes estados de usuario y flujos de conversación.

## Requirements

### Requirement: Detección de Estado de Usuario

El sistema DEBE identificar el estado del usuario en cada interacción.

#### Scenario: Usuario nuevo sin registro

- GIVEN el usuario envía "/start" por primera vez
- WHEN no existe en la base de datos (UserRepository retorna None)
- THEN el sistema DEBE crear el usuario en Supabase
- AND responder con mensaje de bienvenida para usuario nuevo
- AND indicar que debe registrarse en el dashboard

#### Scenario: Usuario existente sin auth

- GIVEN el usuario existe en la base de datos pero no tiene auth_user_id
- WHEN envía cualquier mensaje que no sea "/start"
- THEN el sistema DEBE solicitar registro antes de procesar
- AND NO ejecutar skills hasta que se registre

#### Scenario: Usuario completamente registrado

- GIVEN el usuario existe y tiene auth_user_id
- WHEN envía un mensaje
- THEN el sistema DEBE procesar normalmente a través del Skill Manager

### Requirement: Detección de Intención

El sistema DEBE detectar la intención del mensaje del usuario usando patrones regex.

#### Scenario: Intención clara (gasto)

- GIVEN el usuario envía "gasté 500"
- WHEN el patrón "gasté \d+" hace match
- THEN retornar intención "gasto"
- AND ejecutar el handler de gasto

#### Scenario: Intención ambigua (situación financiera)

- GIVEN el usuario envía "mi flujo es 910"
- WHEN el mensaje contiene más de 50 caracteres Y palabras clave de análisis
- THEN retornar intención "general" para pasar a IA

#### Scenario: Mensaje trivial

- GIVEN el usuario envía "hola"
- WHEN el mensaje tiene menos de 30 caracteres Y es saludo
- THEN responder directamente sin pasar a IA

### Requirement: Manejo de Acciones Pendientes

El sistema DEBE recordar acciones que requieren segundo paso.

#### Scenario: Confirmar categoría de gasto

- GIVEN el usuario envió "gasté 300"
- WHEN la intención es "gasto" pero falta la categoría
- THEN el sistema DEBE guardar el monto en _pending_data
- AND preguntar "¿En qué categoría?"
- AND esperar respuesta con estado "WAIT_CATEGORIA"

#### Scenario: Responder categoría pendiente

- GIVEN el usuario está en estado "WAIT_CATEGORIA"
- WHEN responde con una categoría válida
- THEN ejecutar expense_create con la categoría
- AND limpiar el estado pendiente

### Requirement: Flujo de Meta con Cálculo

El sistema DEBE calcular el ahorro necesario cuando se crea una meta.

#### Scenario: Crear meta con plazo e ingreso

- GIVEN el usuario envía "meta moto 2650"
- WHEN se detecta intención "meta"
- THEN preguntar "¿En cuánto tiempo (meses)? Y cuál es tu ingreso mensual?"

#### Scenario: Calcular ahorro mensual

- GIVEN el usuario responde "12 meses / 1000"
- WHEN se puede parsear plazo e ingreso del mensaje
- THEN calcular: ahorro_mensual = monto / meses
- AND calcular porcentaje del ingreso
- AND mostrar: "Para lograrla en X meses, necesitás ahorrar $Y/mes (Z% de tu ingreso)"

### Requirement: Respuestas según Tipo

El sistema DEBE responder de forma diferente según el tipo de contenido.

#### Scenario: Respuesta de skill (directa)

- GIVEN el resultado del skill tiene un mensaje diferente a "CONTINUAR_CON_IA"
- THEN enviar ese mensaje directamente
- AND NO usar IA

#### Scenario: Respuesta de IA (interpretación)

- GIVEN el resultado del skill es "CONTINUAR_CON_IA"
- THEN enviar el mensaje a DeepSeek con contexto limitado (últimos 5 mensajes)
- AND usar max_tokens = 200 según prompts.toml
- AND guardar la conversación en Supabase

## ADDED Requirements

### Requirement: Logging para Debugging

El sistema DEBE registrar cada paso del procesamiento para facilitar debugging.

#### Scenario: Log de entrada

- GIVEN llega un mensaje al webhook
- WHEN se procesa
- THEN registrar: user_id, mensaje(original), intención_detectada, acción_ejecutada

#### Scenario: Log de errores

- GIVEN ocurre una excepción en el processing
- WHEN se captura el error
- THEN registrar el error completo con traceback
- AND retornar mensaje genérico al usuario

### Requirement: Estados de Usuario Definidos

El sistema DEBE definir estados explícitos para el usuario.

#### States
- NEW_NO_AUTH: Usuario creado pero sin registro en dashboard
- REGISTERED: Usuario con auth_user_id configurado
- PENDING_ACTION: Usuario esperando respuesta para acción anterior

## MODIFIED Requirements

### Requirement: Patrones de Intención

Los patrones actuales son incompletos. DEBEN incluir:
- Variations de "mi flujo" → ingreso
- Variations de comandos (/start, /menu, /help)
- Palabras de análisis para pasar a IA

(Previously: Solo patrones básicos para gasto/meta)

### Requirement: Mensajes de Respuesta

Los mensajes DEBEN:
- Máximo 2-3 oraciones
- Un emoji solo si es necesario
- Sin asteriscos, sin listas, sin negritas
- En español coloquial

(Previously: Mensajes largos con muchos emojis y asteriscos)