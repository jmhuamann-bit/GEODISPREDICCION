"""
Clima real de Bogota via OpenWeather (Current Weather Data API, capa gratuita).

Sigue el mismo patron que las integraciones de notificacion (config.py + Configuracion): si no
hay OPENWEATHER_API_KEY configurada, la funcion devuelve None de forma explicita en vez de
simular datos - nunca se inventa un valor de clima.
"""
from datetime import datetime, timezone

import requests
from flask import current_app

from services.bogota_geo import BOGOTA_CENTER

_cache = {"data": None, "fetched_at": None}
CACHE_TTL_SECONDS = 600  # el clima no cambia lo bastante rapido como para consultar en cada request


def get_current_weather() -> dict | None:
    api_key = current_app.config.get("OPENWEATHER_API_KEY")
    if not api_key:
        return None

    now = datetime.now(timezone.utc)
    if _cache["data"] and _cache["fetched_at"] and (now - _cache["fetched_at"]).total_seconds() < CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "lat": BOGOTA_CENTER["lat"], "lon": BOGOTA_CENTER["lon"],
                "appid": api_key, "units": "metric", "lang": "es",
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        raw = resp.json()
    except requests.RequestException:
        return None

    lluvia_mm = (raw.get("rain") or {}).get("1h", 0.0)
    data = {
        "temperatura_c": raw.get("main", {}).get("temp"),
        "sensacion_c": raw.get("main", {}).get("feels_like"),
        "humedad_pct": raw.get("main", {}).get("humidity"),
        "descripcion": (raw.get("weather") or [{}])[0].get("description"),
        "viento_kmh": round((raw.get("wind", {}).get("speed") or 0) * 3.6, 1),
        "lluvia_mm_1h": lluvia_mm,
        "nivel_riesgo_lluvia": _nivel_riesgo_lluvia(lluvia_mm),
        "obtenido_en": now.isoformat(),
        "fuente": "OpenWeather (tiempo real)",
    }
    _cache["data"] = data
    _cache["fetched_at"] = now
    return data


def _nivel_riesgo_lluvia(mm_1h: float) -> str:
    if mm_1h >= 15:
        return "Alto"
    if mm_1h >= 5:
        return "Medio"
    return "Bajo"
