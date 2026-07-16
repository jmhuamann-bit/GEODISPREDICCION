"""
Motor del Chat IA — Fase actual: intenciones basadas en reglas (patrones de palabras clave)
que consultan los servicios ya existentes (dashboard, monitoring, predictions, clients).

Preparado para conectar un LLM en una fase posterior: basta con reemplazar `answer()` por una
llamada a un proveedor (por ejemplo, usando estas mismas funciones de servicio como "tools" que
el modelo de lenguaje invoque), sin tocar la API ni el frontend.
"""
import re
import unicodedata

from models.alert import Alert
from models.shipment import Shipment
from services import client_service, dashboard_service

ID_VIAJE_PATTERN = re.compile(r"GDS-\d{4}-\d{6}", re.IGNORECASE)


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _contains_any(text: str, *keywords) -> bool:
    return any(k in text for k in keywords)


def answer(message: str) -> dict:
    raw = message or ""
    text = _normalize(raw)

    id_match = ID_VIAJE_PATTERN.search(raw.upper())
    if id_match:
        return _answer_shipment_lookup(id_match.group(0))

    if _contains_any(text, "hola", "buenas", "buenos dias", "buenas tardes", "hey"):
        return _text("¡Hola! Soy el asistente de GEODIS. Puedo ayudarte con OTIF, Lead Time, "
                      "contingencias, predicciones de riesgo, clientes o el estado de un embarque "
                      "(escribe su ID, ej. GDS-2024-000123). ¿Qué necesitas saber?")

    if _contains_any(text, "que puedes hacer", "ayuda", "opciones", "capacidades"):
        return _text(
            "Puedo responder sobre:\n"
            "• OTIF y Lead Time actuales\n"
            "• Contingencias y alertas críticas abiertas\n"
            "• Desempeño del modelo de Predicciones IA\n"
            "• Corredores logísticos con mayor riesgo\n"
            "• Segmentos de cliente (sector y prioridad)\n"
            "• Estado de un embarque específico (dame su ID, ej. GDS-2024-000123)"
        )

    if _contains_any(text, "otif"):
        return _answer_otif()

    if _contains_any(text, "lead time", "tiempo de entrega", "tiempo promedio"):
        return _answer_leadtime()

    if _contains_any(text, "contingencia", "alerta critica", "alertas criticas", "riesgo alto"):
        return _answer_contingencias()

    if _contains_any(text, "prediccion", "modelo", "ia ", "inteligencia artificial", "auc", "precision"):
        return _answer_prediccion()

    if _contains_any(text, "corredor", "ruta mas riesgosa", "rutas riesgosas"):
        return _answer_corredores()

    if _contains_any(text, "cliente", "sector", "segmento"):
        return _answer_clientes()

    if _contains_any(text, "kpi", "indicador", "resumen", "dashboard"):
        return _answer_kpis()

    return _text(
        "No estoy seguro de haber entendido. Puedo ayudarte con OTIF, Lead Time, contingencias, "
        "predicciones de IA, corredores de riesgo, clientes, o el estado de un embarque "
        "(ej. GDS-2024-000123). ¿Puedes reformular tu pregunta?"
    )


def _text(respuesta: str, tipo: str = "texto", datos=None) -> dict:
    return {"respuesta": respuesta, "tipo": tipo, "datos": datos}


def _answer_otif():
    k = dashboard_service.get_kpis()
    return _text(
        f"El OTIF actual es de **{k['otif_pct']}%** sobre {k['total_embarques']:,} embarques "
        f"(fill rate {k['fill_rate_pct']}%). Nivel de servicio compuesto: {k['nivel_servicio_pct']}%."
    )


def _answer_leadtime():
    k = dashboard_service.get_kpis()
    return _text(f"El Lead Time promedio actual es de **{k['lead_time_promedio_dias']} días**, sobre {k['total_embarques']:,} embarques.")


def _answer_contingencias():
    abiertas = Alert.query.filter_by(estado="Abierta").order_by(Alert.probabilidad_pct.desc()).limit(5).all()
    total = Alert.query.filter_by(estado="Abierta").count()
    if not total:
        return _text("No hay contingencias ni alertas críticas abiertas en este momento.")
    detalle = "\n".join(f"• {a.titulo} ({a.probabilidad_pct}%)" for a in abiertas)
    return _text(f"Hay **{total} alertas críticas abiertas**. Las de mayor probabilidad:\n{detalle}", tipo="lista")


def _answer_prediccion():
    from models.ml_model import MLModelRun
    run = MLModelRun.query.filter_by(activo=True).order_by(MLModelRun.creado_en.desc()).first()
    if not run:
        return _text("Aún no se ha entrenado ningún modelo de Predicciones IA. Ve al módulo Predicciones IA para entrenarlo.")
    return _text(
        f"El modelo activo es **{run.algoritmo}** (versión {run.version}), entrenado con "
        f"{run.n_muestras_entrenamiento:,} embarques. Métricas sobre el conjunto de prueba: "
        f"AUC {run.auc}, Accuracy {run.accuracy}, Recall {run.recall}, Precision {run.precision_}, F1 {run.f1_score}."
    )


def _answer_corredores():
    corredores = dashboard_service.get_top_corredores_riesgo(limit=5)
    if not corredores:
        return _text("No hay suficientes datos para calcular corredores de riesgo.")
    detalle = "\n".join(f"• {c['corredor']}: riesgo {c['riesgo_promedio_pct']}%, OTIF {c['otif_pct']}%" for c in corredores)
    return _text(f"Los corredores con mayor riesgo actualmente son:\n{detalle}", tipo="lista")


def _answer_clientes():
    sectores = client_service.get_sector_summary()[:5]
    detalle = "\n".join(f"• {s['sector_cliente']}: {s['total_embarques']:,} embarques, OTIF {s['otif_pct']}%" for s in sectores)
    return _text(f"Resumen por sector de cliente:\n{detalle}", tipo="lista")


def _answer_kpis():
    k = dashboard_service.get_kpis()
    return _text(
        f"Resumen ejecutivo:\n"
        f"• Embarques: {k['total_embarques']:,}\n"
        f"• OTIF: {k['otif_pct']}%\n"
        f"• Lead Time: {k['lead_time_promedio_dias']} días\n"
        f"• Costo total: $ {k['costo_total_cop']:,.0f} COP\n"
        f"• CO₂ estimado: {k['co2_toneladas']:,.1f} ton\n"
        f"• Contingencias activas: {k['contingencias_activas']:,}",
        tipo="lista",
    )


def _answer_shipment_lookup(id_viaje: str):
    s = Shipment.query.filter_by(id_viaje=id_viaje.upper()).first()
    if not s:
        return _text(f"No encontré ningún embarque con ID **{id_viaje.upper()}**.")
    otif_txt = "cumplió" if s.otif else "incumplió"
    riesgo_txt = f", riesgo estimado {s.prob_riesgo_incumplimiento}% ({s.nivel_riesgo})" if s.prob_riesgo_incumplimiento is not None else ""
    return _text(
        f"**{s.id_viaje}** — {s.municipio_origen} → {s.municipio_destino} ({s.corredor_logistico}), "
        f"transporte {s.tipo_transporte}, prioridad {s.prioridad_cliente}. "
        f"Lead Time real: {s.leadtime_real_dias} días, {otif_txt} OTIF{riesgo_txt}."
    )
