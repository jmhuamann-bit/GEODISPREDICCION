"""
Entrena el modelo de Predicciones IA sobre los embarques reales, aplica las probabilidades
resultantes a cada embarque y regenera las Alertas Criticas automaticas.

Uso:
    venv/Scripts/python.exe scripts/train_model.py [algoritmo]

algoritmo por defecto: logistic_regression
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from ml.training.trainer import ALGORITHM_LABELS, REGRESSION_TARGETS, train_and_evaluate, train_regression
from services.alert_service import regenerate_ai_alerts
from services.prediction_service import apply_predictions_to_all_shipments


def main():
    algorithm = sys.argv[1] if len(sys.argv) > 1 else "logistic_regression"

    app = create_app()
    with app.app_context():
        db.create_all()
        print(f"Entrenando modelo: {ALGORITHM_LABELS.get(algorithm, algorithm)} ...")
        t0 = time.time()
        run = train_and_evaluate(algorithm)
        print(f"  Entrenado en {time.time() - t0:.1f}s (version {run.version})")
        print(f"  Muestras entrenamiento/prueba: {run.n_muestras_entrenamiento} / {run.n_muestras_prueba}")
        print(f"  Accuracy={run.accuracy}  Precision={run.precision_}  Recall={run.recall}  "
              f"F1={run.f1_score}  AUC={run.auc}")

        print("Aplicando predicciones a todos los embarques...")
        t1 = time.time()
        n = apply_predictions_to_all_shipments()
        print(f"  {n} embarques actualizados en {time.time() - t1:.1f}s")

        print("Regenerando Alertas Criticas...")
        n_alerts = regenerate_ai_alerts()
        print(f"  {n_alerts} alertas criticas generadas (probabilidad >= "
              f"{app.config['RISK_ALERT_THRESHOLD_PCT']}%)")

        print("Entrenando regresores auxiliares del Simulador (Lead Time y Costo)...")
        for target in REGRESSION_TARGETS:
            t2 = time.time()
            result = train_regression(target)
            print(f"  {result['label']}: MAE={result['mae']}  R2={result['r2']}  "
                  f"({time.time() - t2:.1f}s)")

        print(f"Listo. Tiempo total: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
