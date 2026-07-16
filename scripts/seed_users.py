"""
Crea los usuarios demo iniciales (uno por rol) para poder iniciar sesion.
Ejecutar: venv/Scripts/python.exe scripts/seed_users.py

IMPORTANTE: estas son credenciales de demostracion. Cambiarlas antes de produccion.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.user import User

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

app = create_app()
with app.app_context():
    db.create_all()
    creados = 0
    for u in DEMO_USERS:
        if User.query.filter_by(email=u["email"]).first():
            continue
        user = User(nombre_completo=u["nombre_completo"], email=u["email"], rol=u["rol"], cargo=u["cargo"])
        user.set_password(DEMO_PASSWORD)
        db.session.add(user)
        creados += 1
    db.session.commit()
    print(f"OK: {creados} usuarios demo creados (o ya existian). Password para todos: {DEMO_PASSWORD}")
