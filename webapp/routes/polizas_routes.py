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

polizas_bp = Blueprint('polizas', __name__)

# --- Pólizas ---

@polizas_bp.route("/empresas/<int:empresa_id>/polizas/generar", methods=["POST"])
@login_required
@empresa_requerida
def polizas_generar(empresa_id):
    con = get_connection()
    empresa = con.execute("SELECT tasa_iva FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    con.close()

    generadas = movimientos_repo.generar_polizas_pendientes(empresa_id)
    flash(f"{generadas} pólizas generadas y cuadradas.", "exito")
    return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))


@polizas_bp.route("/empresas/<int:empresa_id>/polizas/exportar")
@login_required
@empresa_requerida
def polizas_exportar(empresa_id):
    con = get_connection()
    empresa = con.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    con.close()

    nombre_archivo = f"polizas_{empresa['nombre'].replace(' ', '_')}"
    ruta_salida = os.path.join(tempfile.gettempdir(), nombre_archivo)

    resultado = movimientos_repo.exportar_polizas(empresa_id, ruta_salida)

    if "xlsx" in resultado["formato"]:
        flash(f"Se exportó en .xlsx en vez de .xls: {resultado['formato']}", "error")

    return send_file(resultado["archivo"], as_attachment=True,
                      download_name=os.path.basename(resultado["archivo"]))


# --- Revisión de pólizas generadas ---

@polizas_bp.route("/empresas/<int:empresa_id>/polizas")
@login_required
@empresa_requerida
def polizas_revision(empresa_id):
    con = get_connection()
    polizas = con.execute(
        """SELECT p.*, m.descripcion AS descripcion_movimiento
           FROM polizas p LEFT JOIN movimientos m ON m.poliza_id = p.id
           WHERE p.empresa_id = ? ORDER BY p.fecha DESC, p.tipo, p.numero""",
        (empresa_id,),
    ).fetchall()

    detalle = {}
    for p in polizas:
        lineas = con.execute(
            "SELECT * FROM poliza_lineas WHERE poliza_id = ? ORDER BY orden", (p["id"],)
        ).fetchall()
        explicacion = con.execute(
            "SELECT detalle FROM poliza_auditoria WHERE poliza_id = ? ORDER BY paso", (p["id"],)
        ).fetchall()
        detalle[p["id"]] = {"lineas": lineas, "explicacion": [e["detalle"] for e in explicacion]}
    con.close()

    return render_template("polizas.html", polizas=polizas, detalle=detalle)


