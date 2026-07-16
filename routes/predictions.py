from flask import Blueprint, jsonify
from flask_login import login_required

from ml.training.trainer import ALGORITHM_LABELS, train_and_evaluate
from models.ml_model import MLModelRun
from models.shipment import Shipment
from services.alert_service import regenerate_ai_alerts
from services.auth_service import register_audit
from services.prediction_service import apply_predictions_to_all_shipments
from utils.decorators import roles_required

bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")


@bp.get("/model")
@login_required
def current_model():
    run = MLModelRun.query.filter_by(activo=True).order_by(MLModelRun.creado_en.desc()).first()
    if not run:
        return jsonify({"model": None, "message": "Aún no se ha entrenado ningún modelo."})
    data = run.to_dict()
    data["algoritmo_label"] = ALGORITHM_LABELS.get(run.algoritmo, run.algoritmo)
    return jsonify({"model": data})


@bp.get("/algorithms")
@login_required
def algorithms():
    return jsonify({"algoritmos": [{"id": k, "label": v} for k, v in ALGORITHM_LABELS.items()]})


@bp.post("/train")
@login_required
@roles_required("Analista")
def train():
    run = train_and_evaluate("logistic_regression")
    n_shipments = apply_predictions_to_all_shipments()
    n_alerts = regenerate_ai_alerts()

    from flask_login import current_user
    register_audit(
        current_user, "entrenamiento_modelo_ia", entidad="MLModelRun", entidad_id=run.id,
        detalle=f"{run.algoritmo} v{run.version} — AUC={run.auc} — {n_shipments} embarques actualizados, "
                 f"{n_alerts} alertas criticas generadas",
    )

    data = run.to_dict()
    data["algoritmo_label"] = ALGORITHM_LABELS.get(run.algoritmo, run.algoritmo)
    return jsonify({"model": data, "embarques_actualizados": n_shipments, "alertas_generadas": n_alerts})


@bp.get("/top-riesgo")
@login_required
def top_riesgo():
    shipments = (
        Shipment.query.filter(Shipment.prob_riesgo_incumplimiento.isnot(None))
        .order_by(Shipment.prob_riesgo_incumplimiento.desc())
        .limit(20)
        .all()
    )
    return jsonify({
        "items": [
            {
                "id_viaje": s.id_viaje,
                "fecha": s.fecha.isoformat() if s.fecha else None,
                "corredor_logistico": s.corredor_logistico,
                "tipo_transporte": s.tipo_transporte,
                "prioridad_cliente": s.prioridad_cliente,
                "prob_riesgo_incumplimiento": s.prob_riesgo_incumplimiento,
                "nivel_riesgo": s.nivel_riesgo,
                "otif_real": bool(s.otif),
            }
            for s in shipments
        ]
    })
