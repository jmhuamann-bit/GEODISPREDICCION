"""
One-off generator: reads the GEODIS data dictionary CSV and emits
backend/app/models/field_metadata.py (static, versioned, human-readable).

Run once (or whenever the dictionary changes): python scripts/_gen_field_metadata.py
"""
import csv
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT_PATH = os.path.join(ROOT, "data", "GEODIS_Colombia_Diccionario_Datos.csv")
OUT_PATH = os.path.join(ROOT, "models", "field_metadata.py")


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def to_column_name(variable: str) -> str:
    ascii_name = strip_accents(variable)
    ascii_name = re.sub(r"[^0-9a-zA-Z_]", "_", ascii_name)
    ascii_name = re.sub(r"_+", "_", ascii_name).strip("_")
    return ascii_name.lower()


def infer_sql_type(tipo_dato: str, variable: str) -> str:
    tipo = tipo_dato.lower()
    if "identificador" in tipo:
        return "String"
    if "fecha" in tipo:
        return "Date"
    if "binaria" in tipo:
        return "Integer"
    if "discreta" in tipo or "discreto" in tipo:
        return "Integer"
    if "continua" in tipo:
        return "Float"
    if "ordinal" in tipo or "categorica" in tipo or "categórica" in tipo_dato.lower():
        return "String"
    return "String"


def infer_group(variable: str) -> str:
    v = variable.lower()
    if v in ("id_viaje", "fecha", "dia_semana", "mes", "trimestre", "ano"):
        return "identificacion_temporal"
    if v.startswith(("departamento", "municipio", "corredor", "ruta")):
        return "geografia"
    if v.startswith(("tipo_transporte", "tipo_vehiculo", "tipo_carga", "sector_cliente", "peso", "volumen")):
        return "operacion_carga"
    if v.startswith(("distancia", "tiempo_", "velocidad_", "consumo")):
        return "tiempos_transito"
    if v.startswith(("costo", "precio", "ipc", "trm", "inflacion", "prima", "deducible", "valor_")):
        return "economico_financiero"
    if v.startswith(("disponibilidad_flota", "utilizacion_flota")):
        return "flota"
    if v.startswith(("estado_via", "indice_deterioro", "numero_cierres", "numero_bloqueos", "indice_bloqueos", "obras_viales", "restricciones")):
        return "infraestructura_vial"
    if v.startswith(("indice_seguridad", "riesgo_hurto", "numero_eventos_seguridad", "presencia_grupos", "indice_orden", "riesgo_extorsion", "riesgo_vandalismo", "riesgo_saqueo")):
        return "seguridad"
    if v.startswith(("numero_paros", "indice_protestas", "manifestaciones", "huelgas", "bloqueos_sociales")):
        return "orden_social"
    if v.startswith(("temperatura", "precipitacion", "humedad", "velocidad_viento", "alerta_ideam", "fenomeno")):
        return "clima"
    if v.startswith(("numero_inundaciones", "indice_inundaciones", "numero_deslizamientos", "indice_deslizamientos",
                      "numero_derrumbes", "indice_derrumbes", "numero_incendios", "indice_incendios",
                      "riesgo_geologico", "riesgo_hidrologico")):
        return "riesgo_natural"
    if v.startswith(("numero_accidentes", "intensidad_incidente", "duracion_incidente", "tiempo_cierre")):
        return "incidentes"
    if v.startswith(("indice_abastecimiento", "nivel_inventario", "demanda")):
        return "demanda_inventario"
    if v.startswith(("prioridad_cliente", "otif", "fill_rate", "nivel_servicio")):
        return "servicio_cliente"
    if v.startswith(("tiempo_almacenamiento", "cross_docking", "tipo_bodega", "capacidad_bodega", "utilizacion_bodega")):
        return "almacenamiento"
    if v.startswith(("aseguradora", "tipo_cobertura", "valor_asegurado", "siniestro", "estado_reclamacion")):
        return "seguros"
    if v == "leadtime_real_dias":
        return "objetivo"
    return "otro"


rows = []
with open(DICT_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        variable = r["Variable"].strip()
        if not variable:
            continue
        rows.append({
            "variable": variable,
            "column": to_column_name(variable),
            "tipo_dato": r["Tipo_de_Dato"].strip(),
            "sql_type": infer_sql_type(r["Tipo_de_Dato"], variable),
            "unidad": r["Unidad_de_Medida"].strip(),
            "fuente": r["Fuente_Publica_de_Referencia"].strip(),
            "descripcion": r["Descripcion"].strip(),
            "grupo": infer_group(variable),
        })

lines = []
lines.append('"""')
lines.append("Metadatos del diccionario de datos GEODIS Colombia (generado automaticamente).")
lines.append("Fuente: GEODIS_Colombia_Diccionario_Datos.csv")
lines.append("NO editar a mano: regenerar con backend/scripts/_gen_field_metadata.py")
lines.append('"""')
lines.append("")
lines.append("FIELDS = [")
for r in rows:
    lines.append("    {")
    for key in ("variable", "column", "tipo_dato", "sql_type", "unidad", "fuente", "descripcion", "grupo"):
        val = r[key].replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'        "{key}": "{val}",')
    lines.append("    },")
lines.append("]")
lines.append("")
lines.append("FIELDS_BY_COLUMN = {f['column']: f for f in FIELDS}")
lines.append("FIELDS_BY_VARIABLE = {f['variable']: f for f in FIELDS}")
lines.append("")

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"OK: {len(rows)} campos escritos en {OUT_PATH}")
