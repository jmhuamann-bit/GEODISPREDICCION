from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from services import event_service, weather_service
from services.auth_service import register_audit
from utils.decorators import roles_required

bp = Blueprint("events", __name__, url_prefix="/api/events")


@bp.get("/live")
@login_required
def live():
    max_age = request.args.get("max_age_hours", default=48, type=int)
    min_conf = request.args.get("min_confidence", default=0.0, type=float)
    return jsonify({
        "events": event_service.get_live_events(max_age, min_conf),
        "nota": "Clasificacion por reglas (NLP-lite) sobre fuentes RSS reales; una senal de una "
                "sola fuente nunca se presenta como hecho confirmado (ver 'confidence').",
    })


@bp.post("/refresh")
@login_required
@roles_required("Analista", "Supervisor")
def refresh():
    result = event_service.refresh_events()
    register_audit(current_user, "refrescar_eventos_bogota", detalle=str(result))
    return jsonify(result)


@bp.get("/weather")
@login_required
def weather():
    data = weather_service.get_current_weather()
    if data is None:
        return jsonify({"disponible": False, "mensaje": "OPENWEATHER_API_KEY no configurada"}), 200
    return jsonify({"disponible": True, **data})
