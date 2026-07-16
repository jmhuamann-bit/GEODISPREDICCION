"""
Entrenamiento de modelos de Predicciones IA.

Arquitectura desacoplada por diseno: este modulo NO sabe de donde vienen los datos (eso es
app/ml/data), ni como se calculan las metricas (eso es app/ml/evaluation), ni como se sirven
las predicciones (eso es app/ml/prediction). Solo arma el pipeline de scikit-learn, lo entrena
y evalua.

Para agregar un nuevo algoritmo (Random Forest, XGBoost, etc.) basta con registrar un constructor
en ALGORITHMS - el resto del pipeline (imputacion, escalado, one-hot, evaluacion, persistencia)
se reutiliza sin cambios.
"""
import json
import os
from datetime import datetime, timezone

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import MODELS_DIR
from extensions import db
from ml.data.dataset import (
    ALL_FEATURES_FOR_COST, CATEGORICAL_FEATURES, NUMERIC_FEATURES, NUMERIC_FEATURES_FOR_COST,
    load_training_dataframe, split_features_target, split_regression_target,
)
from ml.evaluation.metrics import (
    compute_classification_metrics, compute_confusion_matrix,
    compute_logreg_importance, compute_roc_curve,
)
from models.ml_model import MLModelRun

ALGORITHMS = {
    "logistic_regression": lambda: LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
    # Preparado para futuras fases (requiere agregar las librerias correspondientes a requirements.txt):
    # "random_forest": lambda: RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42),
    # "gradient_boosting": lambda: GradientBoostingClassifier(random_state=42),
    # "xgboost": lambda: XGBClassifier(eval_metric="logloss", random_state=42),
    # "lightgbm": lambda: LGBMClassifier(random_state=42),
}

ALGORITHM_LABELS = {
    "logistic_regression": "Regresión Logística",
}

# Config de los regresores auxiliares que alimentan al Simulador (no son el modelo de riesgo OTIF)
REGRESSION_TARGETS = {
    "leadtime_real_dias": {"numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES, "label": "Lead Time (días)"},
    "costo_total_cop": {"numeric": NUMERIC_FEATURES_FOR_COST, "categorical": CATEGORICAL_FEATURES, "label": "Costo total (COP)"},
}


def _build_preprocessor(numeric_features, categorical_features) -> ColumnTransformer:
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num", numeric_transformer, numeric_features),
        ("cat", categorical_transformer, categorical_features),
    ])


def build_pipeline(algorithm: str = "logistic_regression") -> Pipeline:
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Algoritmo no soportado: {algorithm}. Disponibles: {list(ALGORITHMS)}")

    preprocessor = _build_preprocessor(NUMERIC_FEATURES, CATEGORICAL_FEATURES)
    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", ALGORITHMS[algorithm]()),
    ])


def build_regression_pipeline(numeric_features, categorical_features) -> Pipeline:
    preprocessor = _build_preprocessor(numeric_features, categorical_features)
    return Pipeline([
        ("preprocessor", preprocessor),
        # Ridge (regresion lineal con regularizacion L2): estable con ~200 columnas dummy de las
        # variables categoricas de alta cardinalidad (corredor_logistico, ruta_principal, etc.).
        ("regressor", Ridge(alpha=1.0, random_state=42)),
    ])


def train_and_evaluate(algorithm: str = "logistic_regression", test_size: float = 0.2,
                        random_state: int = 42) -> MLModelRun:
    df = load_training_dataframe()
    X, y = split_features_target(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    # 1) Pipeline de evaluacion: se entrena SOLO con el conjunto de entrenamiento para poder
    #    medir el desempeno real sobre datos que el modelo no vio (conjunto de prueba).
    eval_pipeline = build_pipeline(algorithm)
    eval_pipeline.fit(X_train, y_train)
    y_pred = eval_pipeline.predict(X_test)
    y_proba = eval_pipeline.predict_proba(X_test)[:, 1]

    metrics = compute_classification_metrics(y_test, y_pred, y_proba)
    confusion = compute_confusion_matrix(y_test, y_pred)
    roc = compute_roc_curve(y_test, y_proba)
    importance = compute_logreg_importance(eval_pipeline, top_n=15) if algorithm == "logistic_regression" else []

    # 2) Pipeline de produccion: se re-entrena con el 100% de los datos (mas datos = mejor modelo
    #    final) para generar las predicciones que se guardan en cada embarque y para el simulador.
    #    Las metricas reportadas SIEMPRE provienen del paso 1 (conjunto de prueba), nunca de este.
    production_pipeline = build_pipeline(algorithm)
    production_pipeline.fit(X, y)

    os.makedirs(MODELS_DIR, exist_ok=True)
    version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    artifact_path = os.path.join(MODELS_DIR, f"{algorithm}_{version}.joblib")
    joblib.dump(production_pipeline, artifact_path)

    db.session.query(MLModelRun).update({MLModelRun.activo: False})

    run = MLModelRun(
        algoritmo=algorithm,
        version=version,
        objetivo="incumplimiento_otif",
        activo=True,
        accuracy=metrics["accuracy"],
        precision_=metrics["precision"],
        recall=metrics["recall"],
        f1_score=metrics["f1_score"],
        auc=metrics["auc"],
        n_muestras_entrenamiento=len(X_train),
        n_muestras_prueba=len(X_test),
        features_json=json.dumps(NUMERIC_FEATURES + CATEGORICAL_FEATURES),
        importancia_json=json.dumps(importance),
        matriz_confusion_json=json.dumps(confusion),
        curva_roc_json=json.dumps(roc),
        hiperparametros_json=json.dumps({"test_size": test_size, "random_state": random_state}),
        ruta_artefacto=artifact_path,
    )
    db.session.add(run)
    db.session.commit()
    return run


def train_regression(target: str, test_size: float = 0.2, random_state: int = 42) -> dict:
    """Entrena un regresor auxiliar (Lead Time o Costo) para el Simulador. No usa el modelo de
    riesgo OTIF ni comparte artefacto con el: se guarda por separado como regressor_<target>.joblib."""
    if target not in REGRESSION_TARGETS:
        raise ValueError(f"Objetivo de regresion no soportado: {target}")
    cfg = REGRESSION_TARGETS[target]

    df = load_training_dataframe()
    X, y = split_regression_target(df, target)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    eval_pipeline = build_regression_pipeline(cfg["numeric"], cfg["categorical"])
    eval_pipeline.fit(X_train, y_train)
    y_pred = eval_pipeline.predict(X_test).clip(min=0)

    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    production_pipeline = build_regression_pipeline(cfg["numeric"], cfg["categorical"])
    production_pipeline.fit(X, y)

    os.makedirs(MODELS_DIR, exist_ok=True)
    artifact_path = os.path.join(MODELS_DIR, f"regressor_{target}.joblib")
    joblib.dump(production_pipeline, artifact_path)

    return {"target": target, "label": cfg["label"], "mae": round(mae, 3), "r2": round(r2, 3),
            "n_train": len(X_train), "n_test": len(X_test), "path": artifact_path}
