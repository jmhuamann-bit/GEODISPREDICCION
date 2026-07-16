"""
GEODISPREDICCION — punto de entrada de la aplicacion.

Arma la app con el patron application factory, registra blueprints, autenticacion, logging y
manejo de errores. En local se ejecuta con `python app.py`; en produccion (Render) lo sirve
Gunicorn apuntando a este mismo modulo: `gunicorn app:app` (ver Procfile).
"""
import logging
import os
import socket
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from config import CONFIG_BY_NAME, LOGS_DIR
from extensions import cors, db, login_manager, migrate


def create_app(config_name: str = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(CONFIG_BY_NAME.get(config_name, CONFIG_BY_NAME["development"]))

    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, supports_credentials=True)

    with app.app_context():
        # Idempotente: crea las tablas que falten (no borra ni migra datos existentes). Para
        # cargar el dataset real y entrenar el modelo la primera vez, usar scripts/import_data.py
        # y scripts/train_model.py (ver README, seccion "Primer despliegue").
        import models  # noqa: F401  (registra los modelos en db.metadata antes de create_all)
        db.create_all()

    login_manager.init_app(app)
    login_manager.login_view = "web.login_page"

    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify({"error": "No autenticado"}), 401
        return redirect(url_for("web.login_page"))

    register_blueprints(app)
    register_error_handlers(app)

    app.logger.info("GEODISPREDICCION iniciado en modo '%s'", config_name)
    return app


def configure_logging(app: Flask) -> None:
    """Logging a consola siempre, y a archivo rotativo cuando no se ejecuta en modo debug
    (Render captura stdout/stderr automaticamente; el archivo es util para depuracion local)."""
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)
    app.logger.setLevel(log_level)

    if not app.debug and not app.testing:
        os.makedirs(LOGS_DIR, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(LOGS_DIR, "geodispredice.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s [%(module)s] %(message)s"
        ))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)


def register_blueprints(app: Flask) -> None:
    from routes.pages import bp as web_bp
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.monitoring import bp as monitoring_bp
    from routes.predictions import bp as predictions_bp
    from routes.simulator import bp as simulator_bp
    from routes.map import bp as map_bp
    from routes.shipments import bp as shipments_bp
    from routes.clients import bp as clients_bp
    from routes.kpis import bp as kpis_bp
    from routes.reports import bp as reports_bp
    from routes.chat import bp as chat_bp
    from routes.admin import bp as admin_bp
    from routes.contingencies import bp as contingencies_bp
    from routes.system import bp as system_bp
    from routes.events import bp as events_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(shipments_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(kpis_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(contingencies_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(events_bp)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Recurso no encontrado"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "No autorizado"}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Error interno")
        if request.path.startswith("/api/"):
            return jsonify({"error": "Error interno del servidor"}), 500
        return render_template("errors/500.html"), 500


def _pick_port(preferred: int) -> int:
    """Usa el puerto preferido si esta libre; si no, busca el siguiente libre (evita chocar
    con otros servidores locales). Solo aplica en ejecucion local; en Render, Gunicorn recibe
    el puerto correcto directamente via la variable de entorno PORT."""
    for port in range(preferred, preferred + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred


app = create_app()


if __name__ == "__main__":
    requested_port = int(os.environ.get("PORT", 5000))
    chosen_port = _pick_port(requested_port)
    if chosen_port != requested_port:
        print(f"AVISO: el puerto {requested_port} esta ocupado. Usando el puerto {chosen_port}.")
    app.run(host="0.0.0.0", port=chosen_port, debug=app.config["DEBUG"], use_reloader=False)
