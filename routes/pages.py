"""Blueprint de paginas (renderizado de plantillas). Los datos siempre llegan via fetch() a /api/*."""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

bp = Blueprint("web", __name__)


@bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("web.login_page"))


@bp.get("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("web.dashboard"))
    return render_template("login.html")


@bp.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", active_page="dashboard")


@bp.get("/monitoreo")
@login_required
def monitoreo():
    return render_template("monitoreo.html", active_page="monitoreo")


@bp.get("/mapa")
@login_required
def mapa():
    return render_template("mapa.html", active_page="mapa")


@bp.get("/predicciones")
@login_required
def predicciones():
    return render_template("predicciones.html", active_page="predicciones")


@bp.get("/contingencias")
@login_required
def contingencias():
    return render_template("contingencias.html", active_page="contingencias")


@bp.get("/embarques")
@login_required
def embarques():
    return render_template("embarques.html", active_page="embarques")


@bp.get("/clientes")
@login_required
def clientes():
    return render_template("clientes.html", active_page="clientes")


@bp.get("/simulador")
@login_required
def simulador():
    return render_template("simulador.html", active_page="simulador")


@bp.get("/chat")
@login_required
def chat():
    return render_template("chat.html", active_page="chat")


@bp.get("/kpis")
@login_required
def kpis_page():
    return render_template("kpis.html", active_page="kpis")


@bp.get("/reportes")
@login_required
def reportes():
    return render_template("reportes.html", active_page="reportes")


@bp.get("/configuracion")
@login_required
def configuracion():
    return render_template("configuracion.html", active_page="configuracion")


@bp.get("/perfil")
@login_required
def perfil():
    return render_template("perfil.html", active_page="perfil")


@bp.get("/ayuda")
@login_required
def ayuda():
    return render_template("ayuda.html", active_page="ayuda")
