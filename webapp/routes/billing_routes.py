# ============================================================================
# PROPIEDAD INTELECTUAL Y LICENCIA COMERCIAL CERRADA
# ============================================================================
# Autor Legal y Titular de Derechos: JAVIER ILLAN GONZALEZ
# Organización: ORANGE CREW
# Contacto: ILLANJAVIER9@GMAIL.COM
#
# ADVERTENCIA LEGAL (MÉXICO Y GLOBAL):
# Este código fuente y su arquitectura son propiedad intelectual exclusiva de
# JAVIER ILLAN GONZALEZ. Queda estrictamente prohibida su reproducción,
# distribución, modificación, ingeniería inversa, copia o uso comercial sin la
# autorización expresa y por escrito del autor. Obra protegida conforme a la
# Ley Federal del Derecho de Autor y tratados internacionales aplicables.
# ============================================================================
from flask import Blueprint, redirect, render_template, request, url_for, g, flash
from auth import login_required
from db import get_connection
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))
from billing_service import get_checkout_url, reactivar_suscripcion

billing_bp = Blueprint('billing', __name__)

@billing_bp.route("/pagar")
@login_required
def pagar_suscripcion():
    org_id = g.usuario['organizacion_id']
    url = get_checkout_url(org_id, success_url="/billing/exito", cancel_url="/")
    return redirect(url)

@billing_bp.route("/mock-checkout", methods=["GET", "POST"])
def mock_checkout():
    org_id = request.args.get("org_id")
    if request.method == "POST":
        # Simulamos webhook
        reactivar_suscripcion(org_id, dias=30)
        return redirect(url_for("billing.pago_exitoso"))
        
    return render_template("mock_checkout.html", org_id=org_id)

@billing_bp.route("/exito")
@login_required
def pago_exitoso():
    return render_template("pago_exitoso.html")

