"""
Catalogo geografico estatico de las ciudades colombianas presentes en el dataset GEODIS.

El dataset no trae latitud/longitud (solo nombres de municipio/departamento), asi que se mantiene
aqui un diccionario de coordenadas de referencia (centroides urbanos de dominio publico) para poder
ubicar nodos y rutas en el Mapa Inteligente. Si se importan datos con ciudades nuevas, agregar su
entrada aqui (o, en una fase posterior, resolverlas contra un proveedor como OpenStreetMap/Nominatim).
"""

CITY_COORDS = {
    "Bogotá": {"lat": 4.7110, "lon": -74.0721, "es_puerto": False, "es_aeropuerto_principal": True},
    "Medellín": {"lat": 6.2442, "lon": -75.5812, "es_puerto": False, "es_aeropuerto_principal": True},
    "Cali": {"lat": 3.4516, "lon": -76.5320, "es_puerto": False, "es_aeropuerto_principal": True},
    "Barranquilla": {"lat": 10.9639, "lon": -74.7964, "es_puerto": True, "es_aeropuerto_principal": True},
    "Cartagena": {"lat": 10.3910, "lon": -75.4794, "es_puerto": True, "es_aeropuerto_principal": True},
    "Buenaventura": {"lat": 3.8801, "lon": -77.0312, "es_puerto": True, "es_aeropuerto_principal": False},
    "Santa Marta": {"lat": 11.2408, "lon": -74.1990, "es_puerto": True, "es_aeropuerto_principal": False},
    "Bucaramanga": {"lat": 7.1193, "lon": -73.1227, "es_puerto": False, "es_aeropuerto_principal": True},
    "Cúcuta": {"lat": 7.8939, "lon": -72.5078, "es_puerto": False, "es_aeropuerto_principal": True},
    "Pereira": {"lat": 4.8087, "lon": -75.6906, "es_puerto": False, "es_aeropuerto_principal": True},
    "Manizales": {"lat": 5.0703, "lon": -75.5138, "es_puerto": False, "es_aeropuerto_principal": False},
    "Ibagué": {"lat": 4.4389, "lon": -75.2322, "es_puerto": False, "es_aeropuerto_principal": False},
    "Villavicencio": {"lat": 4.1420, "lon": -73.6266, "es_puerto": False, "es_aeropuerto_principal": False},
    "Neiva": {"lat": 2.9273, "lon": -75.2819, "es_puerto": False, "es_aeropuerto_principal": False},
    "Pasto": {"lat": 1.2136, "lon": -77.2811, "es_puerto": False, "es_aeropuerto_principal": True},
    "Popayán": {"lat": 2.4448, "lon": -76.6147, "es_puerto": False, "es_aeropuerto_principal": False},
    "Montería": {"lat": 8.7479, "lon": -75.8814, "es_puerto": False, "es_aeropuerto_principal": True},
    "Sincelejo": {"lat": 9.3047, "lon": -75.3978, "es_puerto": False, "es_aeropuerto_principal": False},
    "Valledupar": {"lat": 10.4631, "lon": -73.2532, "es_puerto": False, "es_aeropuerto_principal": True},
    "Tunja": {"lat": 5.5353, "lon": -73.3678, "es_puerto": False, "es_aeropuerto_principal": False},
    "Armenia": {"lat": 4.5339, "lon": -75.6811, "es_puerto": False, "es_aeropuerto_principal": False},
    "Ipiales": {"lat": 0.8264, "lon": -77.6428, "es_puerto": False, "es_aeropuerto_principal": False},
}

COLOMBIA_CENTER = {"lat": 4.5, "lon": -74.0}


def get_coords(municipio: str) -> dict | None:
    return CITY_COORDS.get(municipio)
