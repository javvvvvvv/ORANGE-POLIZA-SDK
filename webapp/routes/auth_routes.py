# ============================================================================
# PROPIEDAD INTELECTUAL Y LICENCIA COMERCIAL CERRADA
# ============================================================================
# Autor Legal y Titular de Derechos: JAVIER ILLAN GONZALEZ
# Organización: ORANGE CREW
# Contacto: ILLANJAVIER9@GMAIL.COM
# ============================================================================
import os
import uuid
import tempfile
import shutil
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

from auth import login_required, empresa_requerida, obtener_empresas_del_usuario
from db import get_connection, hay_usuarios
import usuarios_repo
import bancos_repo
import catalogo_repo
import cfdi_repo
import marcado_repo
import movimientos_repo
import reglas_generales_repo
from rules_repository import RepositorioReglas


from excel_importer import (
    importar_excel, ConfiguracionImportacion, FORMATO_COLUMNAS_SEPARADAS,
    FORMATO_COLUMNA_CON_SIGNO, FORMATO_VALOR_ABSOLUTO_Y_TIPO,
    listar_hojas, vista_previa, vista_previa_cruda, detectar_fila_encabezado
)
from asignacion_rapida import construir_plantilla_simple, validar_cuentas_iva_configuradas




BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, '..', "uploads")

def _mover_archivo_con_reintentos(origen, destino, intentos=5, espera_segundos=0.4):
    import time
    ultimo_error = None
    for intento in range(intentos):
        try:
            shutil.move(origen, destino)
            return
        except (PermissionError, OSError) as e:
            ultimo_error = e
            time.sleep(espera_segundos)
    try:
        shutil.copy2(origen, destino)
    except Exception:
        raise ultimo_error
    try:
        os.remove(origen)
    except OSError:
        pass

auth_bp = Blueprint('auth', __name__)

# --- Configuración inicial (primer arranque) ---

@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():
    if hay_usuarios():
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        nombre_org = request.form["organizacion"].strip()
        nombre_usuario = request.form["nombre"].strip()
        usuario = request.form["usuario"].strip().lower()
        correo = request.form.get("correo", "").strip().lower() or None
        password = request.form["password"]
        nombre_empresa = request.form["empresa"].strip()
        rfc_empresa = request.form.get("rfc_empresa", "").strip().upper()

        if not usuario:
            flash("Escribe un nombre de usuario.", "error")
            return render_template("setup.html")
        if not usuarios_repo.usuario_disponible(usuario):
            flash(f"El usuario '{usuario}' ya está en uso, elige otro.", "error")
            return render_template("setup.html")

        con = get_connection()
        cur = con.cursor()
        cur.execute("INSERT INTO organizaciones (nombre) VALUES (?)", (nombre_org,))
        org_id = cur.lastrowid

        cur.execute(
            """INSERT INTO usuarios (organizacion_id, nombre, usuario, correo, password_hash, rol_global)
               VALUES (?, ?, ?, ?, ?, 'superadmin')""",
            (org_id, nombre_usuario, usuario, correo, generate_password_hash(password)),
        )
        usuario_id = cur.lastrowid

        cur.execute(
            "INSERT INTO empresas (organizacion_id, nombre, rfc) VALUES (?, ?, ?)",
            (org_id, nombre_empresa, rfc_empresa),
        )
        empresa_id = cur.lastrowid

        cur.execute(
            "INSERT INTO usuario_empresa (usuario_id, empresa_id, rol) VALUES (?, ?, 'admin')",
            (usuario_id, empresa_id),
        )
        con.commit()
        con.close()

        session["usuario_id"] = usuario_id
        flash("Cuenta y empresa creadas correctamente.", "exito")
        return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))

    return render_template("setup.html")


# --- Autenticación ---

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if not hay_usuarios():
        return redirect(url_for("auth.setup"))

    if request.method == "POST":
        nombre_usuario = request.form["usuario"].strip().lower()
        password = request.form["password"]

        con = get_connection()
        usuario = con.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND activo = 1", (nombre_usuario,)
        ).fetchone()
        con.close()

        if usuario and check_password_hash(usuario["password_hash"], password):
            session["usuario_id"] = usuario["id"]
            empresas = obtener_empresas_del_usuario(usuario["id"])
            if len(empresas) == 1:
                return redirect(url_for("empresas.dashboard", empresa_id=empresas[0]["id"]))
            return redirect(url_for("empresas.selector_empresas"))

        flash("Usuario o contraseña incorrectos.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))




@auth_bp.route("/suscripcion-vencida")
def suscripcion_vencida():
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("suscripcion_vencida.html")
