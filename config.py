"""
Configuracion centralizada de GEODISPREDICCION, por entornos (Development / Production / Testing).

La capa de acceso a datos esta desacoplada del motor real: en desarrollo usa SQLite (carpeta
instance/, no versionada en git); en produccion (Render) usa PostgreSQL leyendo DATABASE_URL.
Cambiar de motor no requiere tocar modelos, servicios ni rutas.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DATA_DIR = os.path.join(BASE_DIR, "data")               # datasets fuente (versionados en git)
MODELS_DIR = os.path.join(INSTANCE_DIR, "ml_models")     # artefactos .joblib (NO versionados)
LOGS_DIR = os.path.join(BASE_DIR, "logs")


def _normalize_database_url(url: str) -> str:
    """Render/Heroku entregan DATABASE_URL con el esquema antiguo 'postgres://', pero
    SQLAlchemy 1.4+ requiere 'postgresql://'. Se normaliza automaticamente."""
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _build_default_sqlite_uri() -> str:
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    db_path = os.path.join(INSTANCE_DIR, "geodis.db")
    return f"sqlite:///{db_path}"


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "geodis-dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.environ.get("DATABASE_URL")) or _build_default_sqlite_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    JSON_SORT_KEYS = False
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Umbral de probabilidad (%) sobre el cual se dispara una Alerta Critica
    RISK_ALERT_THRESHOLD_PCT = float(os.environ.get("RISK_ALERT_THRESHOLD_PCT", 80))

    # Integraciones externas: se activan solo si existen credenciales (ver integrations/)
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = os.environ.get("SMTP_PORT")
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

    WHATSAPP_BUSINESS_TOKEN = os.environ.get("WHATSAPP_BUSINESS_TOKEN")
    WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")

    TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL")
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

    OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
    MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENV = "development"


class ProductionConfig(BaseConfig):
    DEBUG = False
    ENV = "production"
    SESSION_COOKIE_SECURE = True


class TestingConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    ENV = "testing"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
