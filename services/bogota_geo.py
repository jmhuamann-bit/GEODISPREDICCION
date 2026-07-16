"""
Gazetteer estatico de Bogota: las 20 localidades oficiales y las vias principales mas
mencionadas en noticias de movilidad. Coordenadas de referencia (centroides aproximados,
hechos geograficos de dominio publico) usadas para geocodificar eventos detectados en texto
cuando no hay un servicio de geocodificacion en tiempo real conectado.

Si en el futuro se conecta un geocodificador real (Nominatim/Google/Mapbox), este modulo pasa
a ser solo el fallback offline - la interfaz (buscar_ubicacion) no cambia.
"""

BOGOTA_CENTER = {"lat": 4.6486, "lon": -74.0908}

LOCALIDADES = {
    "usaquen": {"nombre": "Usaquén", "lat": 4.6946, "lon": -74.0307},
    "chapinero": {"nombre": "Chapinero", "lat": 4.6486, "lon": -74.0628},
    "santa fe": {"nombre": "Santa Fe", "lat": 4.6097, "lon": -74.0721},
    "san cristobal": {"nombre": "San Cristóbal", "lat": 4.5573, "lon": -74.0836},
    "usme": {"nombre": "Usme", "lat": 4.4793, "lon": -74.1263},
    "tunjuelito": {"nombre": "Tunjuelito", "lat": 4.5722, "lon": -74.1319},
    "bosa": {"nombre": "Bosa", "lat": 4.6182, "lon": -74.1772},
    "kennedy": {"nombre": "Kennedy", "lat": 4.6280, "lon": -74.1487},
    "fontibon": {"nombre": "Fontibón", "lat": 4.6675, "lon": -74.1460},
    "engativa": {"nombre": "Engativá", "lat": 4.7126, "lon": -74.1112},
    "suba": {"nombre": "Suba", "lat": 4.7420, "lon": -74.0937},
    "barrios unidos": {"nombre": "Barrios Unidos", "lat": 4.6746, "lon": -74.0761},
    "teusaquillo": {"nombre": "Teusaquillo", "lat": 4.6408, "lon": -74.0925},
    "los martires": {"nombre": "Los Mártires", "lat": 4.6058, "lon": -74.0938},
    "antonio narino": {"nombre": "Antonio Nariño", "lat": 4.5866, "lon": -74.1027},
    "puente aranda": {"nombre": "Puente Aranda", "lat": 4.6156, "lon": -74.1156},
    "la candelaria": {"nombre": "La Candelaria", "lat": 4.5967, "lon": -74.0742},
    "rafael uribe": {"nombre": "Rafael Uribe Uribe", "lat": 4.5580, "lon": -74.1120},
    "ciudad bolivar": {"nombre": "Ciudad Bolívar", "lat": 4.4939, "lon": -74.1592},
    "sumapaz": {"nombre": "Sumapaz", "lat": 4.1500, "lon": -74.2833},
}

# Vias/avenidas principales mencionadas frecuentemente en noticias de movilidad
VIAS_PRINCIPALES = {
    "calle 26": {"nombre": "Calle 26 (Av. El Dorado)", "lat": 4.6486, "lon": -74.1050},
    "avenida el dorado": {"nombre": "Av. El Dorado", "lat": 4.6486, "lon": -74.1050},
    "calle 80": {"nombre": "Calle 80", "lat": 4.6820, "lon": -74.0800},
    "autopista norte": {"nombre": "Autopista Norte", "lat": 4.7300, "lon": -74.0450},
    "autopista sur": {"nombre": "Autopista Sur", "lat": 4.5600, "lon": -74.1600},
    "avenida boyaca": {"nombre": "Av. Boyacá", "lat": 4.6500, "lon": -74.1150},
    "nqs": {"nombre": "Av. NQS (Norte-Quito-Sur)", "lat": 4.6300, "lon": -74.0950},
    "avenida caracas": {"nombre": "Av. Caracas", "lat": 4.6200, "lon": -74.0700},
    "avenida ciudad de cali": {"nombre": "Av. Ciudad de Cali", "lat": 4.6600, "lon": -74.1450},
    "avenida suba": {"nombre": "Av. Suba", "lat": 4.7100, "lon": -74.0900},
    "carrera septima": {"nombre": "Carrera 7", "lat": 4.6600, "lon": -74.0550},
    "carrera 7": {"nombre": "Carrera 7", "lat": 4.6600, "lon": -74.0550},
    "carrera 30": {"nombre": "Carrera 30", "lat": 4.6300, "lon": -74.0950},
    "avenida 68": {"nombre": "Av. 68", "lat": 4.6600, "lon": -74.0980},
}

_ALL_PLACES = {**LOCALIDADES, **VIAS_PRINCIPALES}


def buscar_ubicacion(texto: str) -> dict | None:
    """Busca menciones de localidades/vias de Bogota en un texto (titulo+descripcion de una
    noticia). Devuelve el primer lugar encontrado con sus coordenadas, o None si no se
    encuentra ninguno. Coincidencia simple por substring, sin acentos."""
    normalizado = _normalizar(texto)
    for clave, datos in _ALL_PLACES.items():
        if clave in normalizado:
            return {"clave": clave, **datos}
    return None


def es_de_bogota(texto: str) -> bool:
    normalizado = _normalizar(texto)
    return "bogota" in normalizado or buscar_ubicacion(texto) is not None


def _normalizar(texto: str) -> str:
    import unicodedata
    texto = (texto or "").lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))
