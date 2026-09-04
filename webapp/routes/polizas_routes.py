# ============================================================================
# PROPIEDAD INTELECTUAL Y LICENCIA COMERCIAL CERRADA
# ============================================================================
# Autor Legal y Titular de Derechos: JAVIER ILLAN GONZALEZ
# OrganizaciÃ³n: ORANGE CREW
# Contacto: ILLANJAVIER9@GMAIL.COM
# ============================================================================
import os
import uuid
import tempfile
import shutil
from datetime import datetime
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend/app')))
from exporters.contpaqi_sdk_exporter import exportar_polizas_via_sdk

class LineaPoliza:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MovimientoContpaqi:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

from auth import login_required, empresa_requerida, csrf_protect, obtener_empresas_del_usuario
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

# --- PÃ³lizas ---

@polizas_bp.route("/empresas/<int:empresa_id>/polizas/generar", methods=["POST"])
@login_required
@empresa_requerida
def polizas_generar(empresa_id):
    con = get_connection()
    empresa = con.execute("SELECT tasa_iva FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    con.close()

    inicio_i = request.form.get('inicio_ingreso', type=int)
    inicio_e = request.form.get('inicio_egreso', type=int)
    generadas = movimientos_repo.generar_polizas_pendientes(empresa_id, inicio_ingreso=inicio_i, inicio_egreso=inicio_e)
    flash(f"{generadas} pÃ³lizas generadas y cuadradas.", "exito")
    return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))


@polizas_bp.route("/empresas/<int:empresa_id>/polizas/exportar")
@login_required
@empresa_requerida
def polizas_exportar(empresa_id):
    con = get_connection()
    empresa = con.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    
    descuadradas = con.execute("SELECT COUNT(*) FROM polizas WHERE empresa_id = ? AND cuadrada = 0", (empresa_id,)).fetchone()[0]
    if descuadradas > 0:
        con.close()
        flash(f"CUIDADO: Tienes {descuadradas} póliza(s) descuadrada(s). Corrígelas antes de exportar.", "error")
        return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))
    con.close()

    nombre_archivo = f"polizas_{empresa['nombre'].replace(' ', '_')}"
    ruta_salida = os.path.join(tempfile.gettempdir(), nombre_archivo)

    resultado = movimientos_repo.exportar_polizas(empresa_id, ruta_salida)

    if "xlsx" in resultado["formato"]:
        flash(f"Se exportÃ³ en .xlsx en vez de .xls: {resultado['formato']}", "error")

    return send_file(resultado["archivo"], as_attachment=True,
                      download_name=os.path.basename(resultado["archivo"]))

@polizas_bp.route("/empresas/<int:empresa_id>/polizas/exportar_sdk", methods=["POST"])
@login_required
@empresa_requerida
@csrf_protect
def exportar_polizas_sdk(empresa_id):
    con = get_connection()
    empresa = con.execute(
        "SELECT nombre, base_datos_contpaqi FROM empresas WHERE id = ?", (empresa_id,)
    ).fetchone()
    if not empresa:
        flash("Empresa no encontrada.", "error")
        con.close()
        return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))

    # Antes se tomaba de un campo de texto libre (nombre_empresa_contpaqi),
    # donde era facil capturar el nombre "bonito" en vez del nombre interno
    # de base de datos -- eso es justo lo que abreEmpresa() rechaza. Ahora
    # se usa siempre el valor ya confirmado y guardado en Configuracion.
    nombre_contpaqi = empresa["base_datos_contpaqi"]
    if not nombre_contpaqi:
        flash(
            "Falta configurar el nombre interno de CONTPAQi para esta empresa "
            "(Configuración > Catálogo, base de datos CONTPAQi).",
            "error",
        )
        con.close()
        return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))

    # VERIFICACION DE ROBUSTEZ: No exportar polizas descuadradas
    descuadradas = con.execute("SELECT COUNT(*) FROM polizas WHERE empresa_id = ? AND cuadrada = 0", (empresa_id,)).fetchone()[0]
    if descuadradas > 0:
        flash(f"CUIDADO: No se puede exportar. Tienes {descuadradas} póliza(s) descuadrada(s). Revisa el visor y corrígelas antes de enviar a CONTPAQi.", "error")
        con.close()
        return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))

    polizas = con.execute("""
        SELECT p.*, COALESCE(p.concepto, m.descripcion) AS concepto 
        FROM polizas p 
        LEFT JOIN movimientos m ON m.poliza_id = p.id 
        WHERE p.empresa_id = ? ORDER BY p.tipo, p.numero
    """, (empresa_id,)).fetchall()
    
    movimientos_poliza = []
    map_lineas = {}
    if polizas:
        p_ids = [str(p["id"]) for p in polizas]
        lineas_raw = con.execute(f"SELECT * FROM poliza_lineas WHERE poliza_id IN ({','.join(p_ids)})").fetchall()
        for l in lineas_raw:
            map_lineas.setdefault(l["poliza_id"], []).append(l)

        for p in polizas:
            lineas = []
            for l in map_lineas.get(p["id"], []):
                lineas.append(LineaPoliza(
                    cuenta=l["cuenta"],
                    naturaleza=l["naturaleza"],
                    importe=l["importe"],
                    descripcion=l["descripcion"],
                    segmento_negocio=""
                ))
            mov = MovimientoContpaqi(
                fecha=datetime.strptime(p["fecha"], "%Y-%m-%d"),
                tipo=p["tipo"],
                numero_poliza=p["numero"],
                descripcion=p["concepto"] or f"PÃ³liza {p['numero']}",
                lineas=lineas,
                numero_factura=p["referencia"] or ""
            )
            movimientos_poliza.append(mov)
    con.close()

    try:
        res = exportar_polizas_via_sdk(movimientos_poliza, nombre_interno_empresa=nombre_contpaqi)
        
        if res.get("exito"):
            flash(f"Ã‰xito: {res.get('mensaje')}", "exito")
            return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))
        else:
            flash(f"Error SDK: {res.get('mensaje')}", "error")
            return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))
    except Exception as e:
        flash(f"Error interno: {e}", "error")
        return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))


# --- RevisiÃ³n de pÃ³lizas generadas ---

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




@polizas_bp.route("/empresas/<int:empresa_id>/polizas/limpiar", methods=["POST"])
@login_required
@empresa_requerida
@csrf_protect
def polizas_limpiar(empresa_id):
    movimientos_repo.limpiar_polizas(empresa_id)
    flash("Se han eliminado todas las pólizas generadas. Los movimientos vuelven a estar pendientes.", "exito")
    return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))

@polizas_bp.route("/empresas/<int:empresa_id>/movimientos/limpiar", methods=["POST"])
@login_required
@empresa_requerida
@csrf_protect
def movimientos_limpiar(empresa_id):
    movimientos_repo.limpiar_movimientos(empresa_id)
    flash("Se han eliminado todos los movimientos, pólizas y documentos de la empresa. Lista para una carga nueva.", "exito")
    return redirect(url_for("empresas.dashboard", empresa_id=empresa_id))

@polizas_bp.route("/empresas/<int:empresa_id>/polizas/<int:poliza_id>/editar", methods=["POST"])
@login_required
@empresa_requerida
@csrf_protect
def polizas_editar(empresa_id, poliza_id):
    datos = request.get_json()
    if not datos or "lineas" not in datos:
        return {"exito": False, "mensaje": "Datos invalidos"}, 400
        
    try:
        movimientos_repo.actualizar_poliza(poliza_id, datos["lineas"])
        return {"exito": True, "mensaje": "Poliza actualizada correctamente."}
    except Exception as e:
        return {"exito": False, "mensaje": str(e)}, 500


