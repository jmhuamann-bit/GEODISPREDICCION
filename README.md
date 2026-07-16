# GEODISPREDICCIÓN

Plataforma empresarial de Decision Intelligence para GEODIS Colombia: anticipar, predecir,
gestionar y responder a contingencias logísticas en menos de 72 horas, sobre datos reales de
operación (22,000 embarques, 97 variables).

**Stack:** Python · Flask · Jinja2 · SQLAlchemy · Bootstrap 5 · scikit-learn · SQLite (desarrollo) ·
PostgreSQL (producción) · Render.

---

## Índice

1. [Estructura del proyecto](#estructura-del-proyecto)
2. [Clonar y ejecutar en local](#1-clonar-y-ejecutar-en-local)
3. [Subir el proyecto a GitHub](#2-subir-el-proyecto-a-github)
4. [Desplegar en Render](#3-desplegar-en-render)
5. [Actualizar la plataforma (git push)](#4-actualizar-la-plataforma-git-push)
6. [Variables de entorno](#variables-de-entorno)
7. [Cuentas de demostración](#cuentas-de-demostración)
8. [Arquitectura y buenas prácticas](#arquitectura-y-buenas-prácticas)
9. [Extender la plataforma](#extender-la-plataforma)

---

## Estructura del proyecto

```
GEODISPREDICCION/
├── app.py                  # Punto de entrada: application factory + Gunicorn apunta aquí
├── config.py                # Configuración por entorno (Development/Production/Testing)
├── extensions.py             # Instancias únicas de Flask-SQLAlchemy, Login, CORS, Migrate
├── requirements.txt
├── runtime.txt                # Versión de Python para Render
├── Procfile                   # Comando de arranque (Gunicorn)
├── render.yaml                 # Blueprint de Render (infraestructura como código)
├── .env.example                # Plantilla de variables de entorno
├── .gitignore
│
├── routes/                    # Blueprints — solo reciben la petición HTTP y llaman a services/
├── models/                    # Modelos SQLAlchemy (User, Shipment, Alert, AuditLog, MLModelRun)
├── services/                  # Lógica de negocio y acceso a datos (nunca SQL crudo en routes/)
├── ml/                         # Machine Learning: data / training / evaluation / prediction
├── database/                   # ETL: lectura, validación y carga de CSV/Excel a la base de datos
├── integrations/               # Adaptadores preparados: Email, WhatsApp, Teams, Slack
├── utils/                      # Decoradores y utilidades transversales
│
├── templates/                  # HTML (Jinja2), incluida templates/errors/ (404, 403, 500)
├── static/                     # CSS (sistema de diseño) y JS
├── scripts/                    # Scripts de línea de comandos (import_data, seed_users, train_model)
├── data/                       # Dataset fuente (CSV) — versionado en git
├── uploads/                    # Carpeta preparada para futuras cargas de archivos de usuario
│
├── instance/                   # Generado en tiempo de ejecución — SQLite local y modelos .joblib
│                                # (NO se versiona en git; en producción se usa PostgreSQL)
└── logs/                       # Logs rotativos en ejecución local (NO se versiona)
```

---

## 1. Clonar y ejecutar en local

### Requisitos
- Python 3.12
- Git
- Visual Studio Code (recomendado)

### Pasos

```powershell
# 1. Clonar el repositorio
git clone https://github.com/jmhuamann-bit/GEODISPREDICCION.git
cd GEODISPREDICCION

# 2. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env
# Editar .env y completar SECRET_KEY con una cadena aleatoria (dejar DATABASE_URL vacío para usar SQLite)

# 5. Importar el dataset real y crear los usuarios de demostración
python scripts\import_data.py
python scripts\seed_users.py

# 6. (Opcional pero recomendado) Entrenar el modelo de IA
python scripts\train_model.py

# 7. Ejecutar la aplicación
python app.py
```

Abrir `http://localhost:5000` (o el puerto que indique la consola si el 5000 está ocupado).

---

## 2. Subir el proyecto a GitHub

Estos pasos se ejecutan **una sola vez**, desde la terminal de Visual Studio Code.

```powershell
cd GEODISPREDICCION
git init
git add .
git commit -m "GEODISPREDICCION: plataforma inicial lista para produccion"
```

Crear el repositorio vacío en GitHub (elige una opción):

**Opción A — desde la web de GitHub:**
1. Ir a https://github.com/new
2. Owner: `jmhuamann-bit` — Nombre del repositorio: `GEODISPREDICCION`
3. Dejarlo **vacío** (sin README, sin .gitignore, sin licencia — ya los trae el proyecto)
4. Crear repositorio

**Opción B — con GitHub CLI** (si lo instalas y autenticas con `gh auth login`):
```powershell
gh repo create jmhuamann-bit/GEODISPREDICCION --public --source=. --remote=origin
```

Conectar el repositorio local con GitHub y subir el código:

```powershell
git remote add origin https://github.com/jmhuamann-bit/GEODISPREDICCION.git
git branch -M main
git push -u origin main
```

La primera vez, Windows/Git te pedirá iniciar sesión en GitHub (se abre el navegador) — es tu
propia autenticación, un único paso manual.

---

## 3. Desplegar en Render

1. Entrar a https://dashboard.render.com y crear una cuenta o iniciar sesión (con tu cuenta de GitHub es lo más rápido).
2. Clic en **New +** → **Blueprint**.
3. Conectar tu cuenta de GitHub (si no lo has hecho) y seleccionar el repositorio `jmhuamann-bit/GEODISPREDICCION`.
4. Render detecta automáticamente el archivo `render.yaml` de este proyecto y muestra el plan:
   un servicio web (`geodispredice`) + una base de datos PostgreSQL (`geodispredice-db`), ambos en el plan gratuito.
5. Clic en **Apply** / **Create New Resources**. Render instala dependencias, provisiona la base de
   datos, inyecta `DATABASE_URL` automáticamente y arranca la aplicación con Gunicorn.
6. Cuando el estado pase a **Live**, Render te entrega la URL pública, con el formato:
   `https://geodispredice.onrender.com`

### Primer despliegue: cargar los datos reales

Render crea las tablas automáticamente al arrancar (ver `app.py`), pero el dataset y el modelo de
IA se cargan con un comando manual **una sola vez**, desde la pestaña **Shell** del servicio en el
dashboard de Render:

```bash
python scripts/import_data.py
python scripts/seed_users.py
python scripts/train_model.py
```

> Nota: el plan gratuito de Render no conserva un disco persistente entre despliegues para archivos
> sueltos fuera de la base de datos. Los datos de `PostgreSQL` sí persisten (viven en la base de
> datos, no en disco), así que una vez importados quedan disponibles permanentemente. Si necesitas
> volver a importar tras cada deploy, considera automatizarlo con un **Render Cron Job** apuntando a
> `python scripts/import_data.py`, o upgradear a un plan con disco persistente.

---

## 4. Actualizar la plataforma (git push)

Este es el flujo del día a día, exactamente como lo pediste:

```powershell
# 1. Edita el proyecto en Visual Studio Code
# 2. Guarda tus cambios
git add .
git commit -m "Descripción del cambio"
git push

# 3. Render detecta el push automáticamente y despliega la nueva versión.
#    No hay que tocar nada más en el servidor.
```

Puedes ver el progreso del deploy en tiempo real en la pestaña **Events** o **Logs** del servicio
en el dashboard de Render.

---

## Variables de entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `SECRET_KEY` | Sí | Firma de sesiones/cookies. En Render, `render.yaml` la genera automáticamente. |
| `DATABASE_URL` | En producción | Cadena de conexión PostgreSQL. Render la inyecta sola desde el blueprint. Vacía = SQLite local. |
| `FLASK_ENV` | No | `development` o `production`. Render la fija en `production`. |
| `RISK_ALERT_THRESHOLD_PCT` | No | Umbral (%) de probabilidad de incumplimiento OTIF para generar una Alerta Crítica. Por defecto 80. |
| `SMTP_*`, `WHATSAPP_*`, `TEAMS_WEBHOOK_URL`, `SLACK_WEBHOOK_URL` | No | Integraciones de notificación, preparadas pero inactivas hasta configurar credenciales. |
| `LOG_LEVEL` | No | Nivel de logging (`INFO` por defecto). |

Ver `.env.example` para la plantilla completa.

---

## Cuentas de demostración

Creadas por `scripts/seed_users.py` (cambiar estas contraseñas antes de un uso real):

| Rol | Email | Password |
|---|---|---|
| Administrador | admin@geodis.com | Geodis2026! |
| Supervisor | supervisor@geodis.com | Geodis2026! |
| Operaciones | operaciones@geodis.com | Geodis2026! |
| Cliente | cliente@geodis.com | Geodis2026! |
| Analista | analista@geodis.com | Geodis2026! |

---

## Arquitectura y buenas prácticas

- **Blueprints**: cada dominio (`auth`, `dashboard`, `monitoring`, `predictions`, `simulator`, `map`,
  `shipments`, `clients`, `kpis`, `reports`, `chat`, `admin`, `contingencies`) es un blueprint
  independiente en `routes/`, sin lógica de negocio — solo reciben la petición y llaman a `services/`.
- **Separación de capas**: `routes/` (HTTP) → `services/` (lógica de negocio) → `models/` (datos).
  Ninguna consulta SQL vive en el frontend ni en las rutas.
- **Configuración por entornos**: `config.py` define `DevelopmentConfig`, `ProductionConfig` y
  `TestingConfig`, seleccionadas por la variable `FLASK_ENV`.
- **Base de datos intercambiable**: cambiar de SQLite a PostgreSQL (o SQL Server, MySQL) es
  cuestión de la variable `DATABASE_URL` — no requiere tocar modelos ni servicios.
- **Seguridad**: `SECRET_KEY` y credenciales solo por variables de entorno (nunca en el código),
  contraseñas con hash (`werkzeug.security`), control de acceso por rol (`utils/decorators.py`),
  cookies de sesión `HttpOnly` y `Secure` en producción, manejo de errores 403/404/500 con páginas
  propias, logging rotativo a archivo, bitácora de auditoría de acciones sensibles.
- **Machine Learning desacoplado**: `ml/data` (datos) → `ml/training` (entrenamiento) →
  `ml/evaluation` (métricas) → `ml/prediction` (servir predicciones), con un registro de
  algoritmos (`ml/training/trainer.py::ALGORITHMS`) listo para sumar Random Forest, XGBoost, etc.
  sin reescribir el resto del pipeline.

---

## Extender la plataforma

La estructura está pensada para crecer sin rehacer nada existente:

- **Nuevo módulo empresarial**: crear `services/nuevo_service.py` + `routes/nuevo.py` (Blueprint) +
  registrar el blueprint en `app.py::register_blueprints` + su plantilla en `templates/`.
- **Nuevo algoritmo de IA**: agregar una entrada a `ALGORITHMS` en `ml/training/trainer.py`.
- **Nueva integración externa**: agregar las variables de entorno correspondientes en `config.py`
  y el adaptador en `integrations/`.
- **Autenticación adicional (OAuth, SSO)**: `extensions.py::login_manager` ya centraliza la sesión;
  agregar el proveedor como un blueprint nuevo en `routes/`.
- **Bases de datos más grandes**: `DATABASE_URL` ya soporta PostgreSQL gestionado (Render, RDS,
  Azure Database, etc.) sin cambios de código.
