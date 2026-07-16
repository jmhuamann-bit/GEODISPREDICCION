from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from services import contingency_service
from services.auth_service import register_audit
from utils.decorators import roles_required

bp = Blueprint("contingencies", __name__, url_prefix="/api/contingencies")

MANAGE_ROLES = ("Operaciones", "Supervisor")


@bp.get("/summary")
@login_required
def summary():
    return jsonify(contingency_service.get_summary())


@bp.get("")
@login_required
def list_alerts():
    filtros = {
        "estado": request.args.get("estado"),
        "severidad": request.args.get("severidad"),
        "tipo": request.args.get("tipo"),
        "busqueda": request.args.get("busqueda"),
    }
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=20, type=int)
    return jsonify(contingency_service.list_alerts(filtros, page, page_size))


@bp.get("/<int:alert_id>")
@login_required
def detail(alert_id):
    data = contingency_service.get_alert_detail(alert_id)
    if not data:
        return jsonify({"error": "Alerta no encontrada"}), 404
    return jsonify(data)


@bp.put("/<int:alert_id>/estado")
@login_required
@roles_required(*MANAGE_ROLES)
def change_estado(alert_id):
    data = request.get_json(silent=True) or {}
    try:
        alert = contingency_service.update_estado(alert_id, data.get("estado"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if not alert:
        return jsonify({"error": "Alerta no encontrada"}), 404
    register_audit(current_user, "cambiar_estado_contingencia", entidad="Alert", entidad_id=alert.id,
                    detalle=f"{alert.id_viaje or ''} -> {alert.estado}")
    return jsonify(alert.to_dict())


@bp.post("")
@login_required
@roles_required(*MANAGE_ROLES)
def create_manual():
    data = request.get_json(silent=True) or {}
    if not data.get("titulo"):
        return jsonify({"error": "El título es obligatorio"}), 400
    alert = contingency_service.create_manual_contingency(data)
    register_audit(current_user, "crear_contingencia_manual", entidad="Alert", entidad_id=alert.id,
                    detalle=alert.titulo)
    return jsonify(alert.to_dict()), 201
