"""
Importa el dataset real de GEODIS Colombia (CSV) a la base de datos.
Uso:
    venv/Scripts/python.exe scripts/import_data.py [ruta_csv]

Si no se indica ruta, usa data/GEODIS_Colombia_Dataset_Sintetico.csv.
Aplica: lectura -> tipado -> validacion/dedup -> heuristica de riesgo -> carga a SQLite.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database.import_csv import read_csv
from database.loader import bulk_load, clear_shipments
from database.risk_heuristic import calcular_riesgo_heuristico
from database.validators import validate_and_clean
from extensions import db

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(PROJECT_ROOT, "data", "GEODIS_Colombia_Dataset_Sintetico.csv")


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    if not os.path.exists(csv_path):
        print(f"ERROR: no se encontro el archivo {csv_path}")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        db.create_all()

        t0 = time.time()
        print(f"Leyendo {csv_path} ...")
        df = read_csv(csv_path)
        print(f"  {len(df)} filas leidas, {len(df.columns)} columnas, {time.time() - t0:.1f}s")

        df, report = validate_and_clean(df)
        print("Reporte de validacion:")
        print(f"  filas originales: {report['filas_originales']}  ->  filas finales: {report['filas_finales']}")
        for e in report["errores"]:
            print(f"  - {e}")

        riesgo = calcular_riesgo_heuristico(df)
        df = df.reset_index(drop=True)
        df[["prob_riesgo_incumplimiento", "nivel_riesgo", "alerta_critica"]] = riesgo.reset_index(drop=True)

        print("Limpiando tabla shipments existente...")
        clear_shipments()

        print("Cargando a la base de datos...")
        t1 = time.time()
        total = bulk_load(df)
        print(f"  {total} embarques cargados en {time.time() - t1:.1f}s")
        print(f"Total: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
