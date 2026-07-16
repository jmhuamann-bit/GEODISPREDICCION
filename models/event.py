"""
Evento normalizado detectado en fuentes de datos reales (hoy: RSS de noticias oficiales/medios
de Bogota). Sigue el esquema de evento estructurado: tipo, ubicacion, severidad, confianza y
estado, para que cualquier fuente futura (trafico, clima, redes sociales oficiales) se integre
sin cambiar el resto del pipeline (event_processing -> geospatial -> risk_engine -> alerts).
"""
from datetime import datetime, timezone

from extensions import db

EVENT_TYPES = (
    "accidente", "bloqueo", "manifestacion", "protesta", "huelga", "cierre_vial",
    "congestion_extrema", "inundacion", "lluvia_intensa", "deslizamiento", "incendio",
    "emergencia", "delito", "orden_publico", "evento_masivo", "obra_vial",
    "falla_infraestructura", "interrupcion_transporte", "otro",
)

EVENT_STATUSES = ("confirmado", "probable", "previsto", "activo", "resuelto", "no_confirmado")


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    event_code = db.Column(db.String(30), unique=True, nullable=False, index=True)  # EVT-000001

    timestamp_detected = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    event_type = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)

    source = db.Column(db.String(30), nullable=False)  # official | media | weather
    source_name = db.Column(db.String(120))
    source_url = db.Column(db.String(500))

    location_text = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    locality = db.Column(db.String(100))

    severity = db.Column(db.Float)              # 0-1
    source_reliability = db.Column(db.Float)     # 0-1
    confidence = db.Column(db.Float)             # 0-1, ver event_service.calcular_confianza

    status = db.Column(db.String(20), default="no_confirmado")
    estimated_start = db.Column(db.DateTime)
    estimated_end = db.Column(db.DateTime)
    affected_radius_km = db.Column(db.Float, default=1.5)
    is_confirmed = db.Column(db.Boolean, default=False)

    cluster_id = db.Column(db.String(40), index=True)   # agrupa eventos duplicados de varias fuentes
    sources_count = db.Column(db.Integer, default=1)     # cuantas fuentes independientes confirman

    corredores_afectados = db.Column(db.Text)  # JSON: lista de corredor_logistico existentes que tocan Bogota

    creado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        import json
        return {
            "event_id": self.event_code,
            "timestamp_detected": self.timestamp_detected.isoformat() if self.timestamp_detected else None,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "location_text": self.location_text,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "locality": self.locality,
            "severity": self.severity,
            "source_reliability": self.source_reliability,
            "confidence": self.confidence,
            "status": self.status,
            "affected_radius_km": self.affected_radius_km,
            "is_confirmed": self.is_confirmed,
            "sources_count": self.sources_count,
            "corredores_afectados": json.loads(self.corredores_afectados) if self.corredores_afectados else [],
        }
