from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from models.user import ROLES, User
from services.auth_service import authenticate, register_audit

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "Email y contraseña son obligatorios"}), 400

    user = authenticate(email, password)
    if not user:
        return jsonify({"error": "Credenciales inválidas o usuario inactivo"}), 401

    login_user(user, remember=True)
    register_audit(user, "login", ip=request.remote_addr)
    return jsonify({"user": user.to_dict()})


@bp.post("/logout")
@login_required
def logout():
    register_audit(current_user, "logout", ip=request.remote_addr)
    logout_user()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return jsonify({"user": None}), 200
    return jsonify({"user": current_user.to_dict()})


@bp.post("/change-password")
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    actual = data.get("password_actual") or ""
    nueva = data.get("password_nueva") or ""
    if not current_user.check_password(actual):
        return jsonify({"error": "La contraseña actual no es correcta"}), 400
    if len(nueva) < 8:
        return jsonify({"error": "La nueva contraseña debe tener al menos 8 caracteres"}), 400
    current_user.set_password(nueva)
    from extensions import db
    db.session.commit()
    register_audit(current_user, "cambio_password")
    return jsonify({"ok": True})


@bp.get("/roles")
@login_required
def roles():
    return jsonify({"roles": list(ROLES)})
