"""Gestion del ciclo de vida de las Alertas/Contingencias: alertas automaticas generadas por el
modelo de IA (tipo='prediccion_ia') y contingencias creadas manualmente por un operador
(tipo='contingencia_manual'). Flujo de estado: Abierta -> En Gestion -> Resuelta."""
from datetime import datetime, timezone

from extensions import db
from models.alert import Alert
from models.shipment import Shipment

ESTADOS_VALIDOS = ("Abierta", "En Gestion", "Resuelta")

# Canales de notificacion preparados (ver app/config.py) - se listan aqui para reflejar en el
# detalle de cada alerta a donde SE ENVIARIA la notificacion una vez se configuren credenciales.
CANALES_PREPARADOS = ("Email", "WhatsApp Business", "Microsoft Teams", "Slack")


def get_summary() -> dict:
    from sqlalchemy import func
    rows = Alert.query.with_entities(Alert.estado, func.count(Alert.id)).group_by(Alert.estado).all()
    counts = {estado: 0 for estado in ESTADOS_VALIDOS}
    for estado, total in rows:
        counts[estado] = total
    criticas_abiertas = Alert.query.filter_by(estado="Abierta", severidad="Critica").count()
    return {
        "abiertas": counts["Abierta"],
        "en_gestion": counts["En Gestion"],
        "resueltas": counts["Resuelta"],
        "criticas_abiertas": criticas_abiertas,
        "total": sum(counts.values()),
    }


def list_alerts(filtros: dict, page: int = 1, page_size: int = 20) -> dict:
    q = Alert.query
    if filtros.get("estado"):
        q = q.filter(Alert.estado == filtros["estado"])
    if filtros.get("severidad"):
        q = q.filter(Alert.severidad == filtros["severidad"])
    if filtros.get("tipo"):
        q = q.filter(Alert.tipo == filtros["tipo"])
    if filtros.get("busqueda"):
        q = q.filter(Alert.id_viaje.ilike(f"%{filtros['busqueda'].strip()}%"))

    q = q.order_by(Alert.creado_en.desc())
    total = q.count()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [a.to_dict() for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def get_alert_detail(alert_id: int) -> dict | None:
    alert = Alert.query.get(alert_id)
    if not alert:
        return None
    data = alert.to_dict()
    if alert.shipment_id:
        shipment = Shipment.query.get(alert.shipment_id)
        if shipment:
            data["embarque"] = {
                "id_viaje": shipment.id_viaje,
                "municipio_origen": shipment.municipio_origen,
                "municipio_destino": shipment.municipio_destino,
                "tipo_transporte": shipment.tipo_transporte,
                "prioridad_cliente": shipment.prioridad_cliente,
                "tiempo_programado_horas": shipment.tiempo_programado_horas,
                "nivel_riesgo": shipment.nivel_riesgo,
            }
    data["canales_preparados"] = list(CANALES_PREPARADOS)
    return data


def update_estado(alert_id: int, nuevo_estado: str) -> Alert | None:
    if nuevo_estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado invalido: {nuevo_estado}")
    alert = Alert.query.get(alert_id)
    if not alert:
        return None
    alert.estado = nuevo_estado
    alert.resuelto_en = datetime.now(timezone.utc) if nuevo_estado == "Resuelta" else None
    db.session.commit()
    return alert


def create_manual_contingency(data: dict) -> Alert:
    alert = Alert(
        id_viaje=data.get("id_viaje") or None,
        tipo="contingencia_manual",
        severidad=data.get("severidad", "Media"),
        titulo=data["titulo"],
        descripcion=data.get("descripcion"),
        probabilidad_pct=None,
        estado="Abierta",
    )
    if data.get("id_viaje"):
        shipment = Shipment.query.filter_by(id_viaje=data["id_viaje"]).first()
        if shipment:
            alert.shipment_id = shipment.id
    db.session.add(alert)
    db.session.commit()
    return alert
