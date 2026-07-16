"""
Endpoints de arranque de datos para el primer despliegue en un entorno nuevo (p. ej. Render).

Protegidos por un token compartido (variable de entorno BOOTSTRAP_TOKEN). Divididos en pasos
pequeños e idempotentes (importar, entrenar clasificador, aplicar predicciones, entrenar
regresores) para que cada llamada quepa con margen dentro del timeout del servidor, en vez de
un solo paso monolitico largo - relevante en instancias con CPU/RAM limitadas (planes gratuitos).
"""
import os
import time

from flask import Blueprint, jsonify, request

from database.import_csv import read_csv
from database.loader import bulk_load, clear_shipments
from database.risk_heuristic import calcular_riesgo_heuristico
from database.validators import validate_and_clean
from ml.training.trainer import REGRESSION_TARGETS, train_and_evaluate, train_regression
from services.alert_service import regenerate_ai_alerts
from services.auth_service import create_user
from services.prediction_service import apply_predictions_to_all_shipments

bp = Blueprint("system", __name__, url_prefix="/api/system")

DEMO_USERS = [
    {"nombre_completo": "Administrador GEODIS", "email": "admin@geodis.com", "rol": "Administrador",
     "cargo": "Administrador de Plataforma"},
    {"nombre_completo": "Camila Restrepo", "email": "supervisor@geodis.com", "rol": "Supervisor",
     "cargo": "Supervisora de Operaciones"},
    {"nombre_completo": "Juan Pérez", "email": "operaciones@geodis.com", "rol": "Operaciones",
     "cargo": "Analista de Operaciones"},
    {"nombre_completo": "Cliente Demo S.A.S.", "email": "cliente@geodis.com", "rol": "Cliente",
     "cargo": "Contacto Logístico"},
    {"nombre_completo": "Valentina Gómez", "email": "analista@geodis.com", "rol": "Analista",
     "cargo": "Analista de Datos e IA"},
]
DEMO_PASSWORD = "Geodis2026!"


def _check_token():
    expected = os.environ.get("BOOTSTRAP_TOKEN")
    provided = request.headers.get("X-Bootstrap-Token") or request.args.get("token")
    return bool(expected) and provided == expected


def _unauthorized():
    return jsonify({"error": "Token invalido o no configurado"}), 403


@bp.get("/status")
def status():
    from models.ml_model import MLModelRun
    from models.shipment import Shipment
    from models.user import User
    return jsonify({
        "embarques": Shipment.query.count(),
        "usuarios": User.query.count(),
        "modelo_activo": MLModelRun.query.filter_by(activo=True).count() > 0,
        "embarques_con_riesgo": Shipment.query.filter(Shipment.prob_riesgo_incumplimiento.isnot(None)).count(),
    })


@bp.post("/bootstrap")
def bootstrap():
    """Paso 1: importa el dataset real y crea los usuarios demo. Rapido (segundos)."""
    if not _check_token():
        return _unauthorized()

    from models.shipment import Shipment
    from models.user import User

    result = {"pasos": []}
    t0 = time.time()

    if Shipment.query.count() == 0:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(project_root, "data", "GEODIS_Colombia_Dataset_Sintetico.csv")

        df = read_csv(csv_path)
        df, report = validate_and_clean(df)
        riesgo = calcular_riesgo_heuristico(df)
        df = df.reset_index(drop=True)
        df[["prob_riesgo_incumplimiento", "nivel_riesgo", "alerta_critica"]] = riesgo.reset_index(drop=True)
        clear_shipments()
        total = bulk_load(df)
        result["pasos"].append(f"embarques importados: {total}")
    else:
        result["pasos"].append(f"embarques ya existian: {Shipment.query.count()}")

    creados = 0
    for u in DEMO_USERS:
        if User.query.filter_by(email=u["email"]).first():
            continue
        create_user(u["nombre_completo"], u["email"], DEMO_PASSWORD, u["rol"], cargo=u["cargo"])
        creados += 1
    result["pasos"].append(f"usuarios demo creados: {creados}")

    result["segundos"] = round(time.time() - t0, 1)
    return jsonify(result)


@bp.post("/train-classifier")
def train_classifier():
    """Paso 2: entrena el clasificador de riesgo OTIF (Regresion Logistica) y aplica las
    predicciones a los embarques + regenera alertas. Es el paso mas pesado."""
    if not _check_token():
        return _unauthorized()

    t0 = time.time()
    run = train_and_evaluate("logistic_regression")
    t1 = time.time()
    n_shipments = apply_predictions_to_all_shipments()
    n_alerts = regenerate_ai_alerts()

    return jsonify({
        "algoritmo": run.algoritmo, "version": run.version, "auc": run.auc,
        "accuracy": run.accuracy, "recall": run.recall,
        "embarques_actualizados": n_shipments, "alertas_generadas": n_alerts,
        "segundos_entrenamiento": round(t1 - t0, 1), "segundos_total": round(time.time() - t0, 1),
    })


@bp.post("/train-regressors")
def train_regressors():
    """Paso 3: entrena los regresores auxiliares del Simulador (Lead Time y Costo)."""
    if not _check_token():
        return _unauthorized()

    t0 = time.time()
    resultados = []
    for target in REGRESSION_TARGETS:
        r = train_regression(target)
        resultados.append({"target": r["target"], "mae": r["mae"], "r2": r["r2"]})

    return jsonify({"regresores": resultados, "segundos": round(time.time() - t0, 1)})
