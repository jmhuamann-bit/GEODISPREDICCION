"""
Event Engine — ingesta, normalizacion, clasificacion y deduplicacion de eventos reales para
Bogota, siguiendo el esquema de evento estructurado (ver models/event.py).

Fuentes activas hoy (reales, publicas, gratuitas, verificadas):
  - RSS de El Tiempo - Bogota (medio de comunicacion)
  - RSS del portal oficial Bogota.gov.co (fuente oficial)

Clasificacion de tipo/severidad/estado: reglas por palabras clave (NLP-lite), no un modelo de
lenguaje entrenado - se declara explicitamente para no presentar esto como mas de lo que es.
Preparado para reemplazarse por un clasificador de texto entrenado sin tocar el resto del
pipeline (misma idea que el registro ALGORITHMS de ml/training/trainer.py).

Nunca se presenta una senal de una sola fuente como un hecho confirmado: ver calcular_confianza.
"""
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone

import feedparser

from extensions import db
from models.event import Event
from services import bogota_geo

RSS_SOURCES = [
    {
        "name": "El Tiempo - Bogotá",
        "url": "https://www.eltiempo.com/rss/bogota.xml",
        "source": "media",
        "reliability": 0.72,
    },
    {
        "name": "Bogotá.gov.co",
        "url": "https://bogota.gov.co/rss.xml",
        "source": "official",
        "reliability": 0.90,
    },
]

# Orden de prioridad: mas especifico/grave primero. Se usa el primer tipo cuyo patron aparezca.
EVENT_KEYWORDS = [
    ("incendio", ["incendio", "conato de incendio", "quema"]),
    ("deslizamiento", ["deslizamiento", "derrumbe"]),
    ("inundacion", ["inundacion", "inundado", "encharcamiento severo"]),
    ("accidente", ["accidente", "choque", "volcamiento", "colision"]),
    ("manifestacion", ["manifestacion", "marcha", "movilizacion social"]),
    ("protesta", ["protesta", "protestan", "bloqueo de manifestantes"]),
    ("huelga", ["huelga", "paro laboral", "cese de actividades"]),
    ("bloqueo", ["bloqueo", "bloqueado", "via bloqueada"]),
    ("cierre_vial", ["cierre vial", "via cerrada", "cierre de la via", "cierre temporal de la"]),
    ("orden_publico", ["disturbios", "alteracion del orden", "orden publico"]),
    ("delito", ["hurto", "robo", "atraco"]),
    ("lluvia_intensa", ["lluvia intensa", "aguacero", "lluvias fuertes", "alerta amarilla", "alerta naranja", "alerta roja"]),
    ("congestion_extrema", ["trancon", "congestion", "embotellamiento", "pico y placa"]),
    ("interrupcion_transporte", ["transmilenio suspendido", "sin servicio", "interrupcion del servicio", "suspension del servicio"]),
    ("falla_infraestructura", ["falla electrica", "falla en el servicio", "corte de energia", "dano en la tuberia"]),
    ("obra_vial", ["obra vial", "obras en la via", "mantenimiento vial", "reparacion vial"]),
    ("evento_masivo", ["concierto", "evento masivo", "marcha atletica"]),
    ("emergencia", ["emergencia", "alerta roja"]),
]

SEVERITY_BASE = {
    "incendio": 0.85, "deslizamiento": 0.85, "inundacion": 0.75, "emergencia": 0.85,
    "accidente": 0.55, "manifestacion": 0.5, "protesta": 0.55, "huelga": 0.5,
    "bloqueo": 0.6, "cierre_vial": 0.45, "orden_publico": 0.65, "delito": 0.4,
    "lluvia_intensa": 0.5, "congestion_extrema": 0.35, "interrupcion_transporte": 0.5,
    "falla_infraestructura": 0.4, "obra_vial": 0.25, "evento_masivo": 0.3, "otro": 0.3,
}

STATUS_KEYWORDS = [
    ("confirmado", ["confirmo", "confirman", "confirmado", "oficialmente"]),
    ("resuelto", ["restablecido", "normalizado", "controlado", "extinguido", "reabierta"]),
    ("activo", ["en este momento", "actualmente", "ahora mismo", "se mantiene"]),
    ("previsto", ["se espera", "pronostican", "anuncian para", "prevista para"]),
    ("probable", ["posible", "presuntamente", "se reporta", "reportan", "al parecer"]),
]


def _normalizar(texto: str) -> str:
    texto = (texto or "").lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def clasificar_tipo(texto: str) -> str:
    norm = _normalizar(texto)
    for tipo, palabras in EVENT_KEYWORDS:
        if any(p in norm for p in palabras):
            return tipo
    return "otro"


def clasificar_estado(texto: str) -> str:
    norm = _normalizar(texto)
    for estado, palabras in STATUS_KEYWORDS:
        if any(p in norm for p in palabras):
            return estado
    return "no_confirmado"


def estimar_severidad(texto: str, tipo: str) -> float:
    base = SEVERITY_BASE.get(tipo, 0.3)
    norm = _normalizar(texto)
    if any(p in norm for p in ["grave", "masivo", "fuerte", "critico", "critica"]):
        base = min(1.0, base + 0.15)
    return round(base, 2)


def calcular_confianza(source_reliability: float, sources_count: int, tiene_ubicacion: bool,
                        horas_desde_deteccion: float) -> float:
    """EVENT_CONFIDENCE = SOURCE_RELIABILITY x CROSS_SOURCE_CONFIRMATION x LOCATION_CONFIDENCE x TEMPORAL_FRESHNESS
    Una sola fuente nunca produce confianza alta (tope ~0.65) - evita tratar una publicacion
    aislada como un hecho confirmado."""
    cross_source = 1.0 if sources_count >= 2 else 0.65
    location_confidence = 1.0 if tiene_ubicacion else 0.55
    temporal_freshness = max(0.3, 1 - (horas_desde_deteccion / 48))
    confianza = source_reliability * cross_source * location_confidence * temporal_freshness
    return round(min(confianza, 0.97), 2)


def _next_event_code() -> str:
    last = Event.query.order_by(Event.id.desc()).first()
    next_n = (last.id + 1) if last else 1
    return f"EVT-{next_n:06d}"


def _corredores_bogota() -> list:
    from models.shipment import Shipment
    rows = (
        Shipment.query.with_entities(Shipment.corredor_logistico)
        .filter((Shipment.municipio_origen == "Bogotá") | (Shipment.municipio_destino == "Bogotá"))
        .distinct().limit(20).all()
    )
    return sorted({r[0] for r in rows if r[0]})


def _fetch_source(fuente: dict) -> list:
    """Descarga y parsea un feed RSS real. Si falla (red, formato), devuelve lista vacia -
    el resto del pipeline sigue funcionando con las demas fuentes (degradacion elegante)."""
    try:
        parsed = feedparser.parse(fuente["url"])
        items = []
        for entry in parsed.entries[:25]:
            titulo = entry.get("title", "")
            descripcion = entry.get("summary", "") or entry.get("description", "")
            link = entry.get("link", "")
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
            else:
                pub_dt = datetime.now(timezone.utc)
            items.append({
                "titulo": titulo, "descripcion": descripcion, "link": link,
                "publicado": pub_dt, "fuente": fuente,
            })
        return items
    except Exception:
        return []


def refresh_events(max_age_hours: int = 48) -> dict:
    """Orquesta el Event Engine completo: descarga -> filtra Bogota -> clasifica -> geocodifica
    -> deduplica contra eventos recientes existentes -> calcula confianza -> persiste."""
    t0 = time.time()
    corredores_bogota = _corredores_bogota()
    nuevos, actualizados, descartados = 0, 0, 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    recientes = Event.query.filter(Event.timestamp_detected >= cutoff).all()

    for fuente in RSS_SOURCES:
        items = _fetch_source(fuente)
        for item in items:
            texto_completo = f"{item['titulo']} {item['descripcion']}"

            if not bogota_geo.es_de_bogota(texto_completo):
                descartados += 1
                continue

            if item["publicado"].tzinfo is None:
                item["publicado"] = item["publicado"].replace(tzinfo=timezone.utc)
            if item["publicado"] < cutoff:
                descartados += 1
                continue

            # La clasificacion de TIPO usa solo el titulo: las descripciones de RSS suelen ser
            # cuerpos de articulo largos donde una palabra clave incidental (ej. un articulo
            # sobre politica ambiental que menciona "inundacion" de pasada) generaria falsos
            # positivos. El titulo es la afirmacion central de la noticia.
            tipo = clasificar_tipo(item["titulo"])
            if tipo == "otro":
                descartados += 1
                continue
            ubicacion = bogota_geo.buscar_ubicacion(texto_completo)
            estado = clasificar_estado(texto_completo)
            severidad = estimar_severidad(texto_completo, tipo)

            # Deduplicacion: mismo tipo + misma localidad (o ambos genericos "Bogota") dentro
            # de la ventana de tiempo -> se considera la misma senal confirmada por otra fuente.
            duplicado = None
            for existente in recientes:
                if existente.event_type != tipo:
                    continue
                mismo_lugar = (
                    (ubicacion and existente.locality == ubicacion["nombre"])
                    or (not ubicacion and not existente.locality)
                )
                if mismo_lugar and existente.source_url != item["link"]:
                    duplicado = existente
                    break

            horas_desde = max(0.0, (datetime.now(timezone.utc) - item["publicado"]).total_seconds() / 3600)

            if duplicado:
                duplicado.sources_count = (duplicado.sources_count or 1) + 1
                if estado != "no_confirmado":
                    duplicado.status = estado
                duplicado.confidence = calcular_confianza(
                    max(duplicado.source_reliability, fuente["reliability"]),
                    duplicado.sources_count, bool(ubicacion or duplicado.locality), horas_desde,
                )
                actualizados += 1
                continue

            evento = Event(
                event_code=_next_event_code(),
                event_type=tipo,
                title=item["titulo"][:290],
                description=(item["descripcion"] or "")[:2000],
                source=fuente["source"],
                source_name=fuente["name"],
                source_url=item["link"],
                location_text=ubicacion["nombre"] if ubicacion else "Bogotá (ubicación general)",
                latitude=ubicacion["lat"] if ubicacion else bogota_geo.BOGOTA_CENTER["lat"],
                longitude=ubicacion["lon"] if ubicacion else bogota_geo.BOGOTA_CENTER["lon"],
                locality=ubicacion["nombre"] if ubicacion else None,
                severity=severidad,
                source_reliability=fuente["reliability"],
                status=estado,
                is_confirmed=(estado == "confirmado"),
                sources_count=1,
                timestamp_detected=item["publicado"],
            )
            evento.confidence = calcular_confianza(
                fuente["reliability"], 1, bool(ubicacion), horas_desde
            )
            import json
            evento.corredores_afectados = json.dumps(corredores_bogota[:8])

            db.session.add(evento)
            recientes.append(evento)
            nuevos += 1

    db.session.commit()
    return {
        "nuevos": nuevos, "actualizados": actualizados, "descartados_no_bogota_o_viejos": descartados,
        "fuentes_consultadas": len(RSS_SOURCES), "segundos": round(time.time() - t0, 1),
    }


def get_live_events(max_age_hours: int = 48, min_confidence: float = 0.0) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    eventos = (
        Event.query.filter(Event.timestamp_detected >= cutoff, Event.confidence >= min_confidence)
        .order_by(Event.severity.desc(), Event.timestamp_detected.desc())
        .limit(200)
        .all()
    )
    return [e.to_dict() for e in eventos]
