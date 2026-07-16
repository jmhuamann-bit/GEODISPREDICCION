from flask import Blueprint, jsonify, request
from flask_login import login_required

from services import simulator_service

bp = Blueprint("simulator", __name__, url_prefix="/api/simulator")


@bp.get("/options")
@login_required
def options():
    return jsonify(simulator_service.get_form_options())


@bp.post("/predict")
@login_required
def predict():
    data = request.get_json(silent=True) or {}
    try:
        result = simulator_service.simulate(data)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)
