import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "app", "core"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "app", "exporters"))

from rule_engine import encontrar_regla, normalizar_texto
from learning_engine import sugerir_regla_desde_clasificacion_manual
from policy_generator import generar_poliza
from rules_repository import RepositorioReglas
from contpaqi_exporter import MovimientoPoliza, ImpuestoPoliza, FacturaAplicada
from contpaqi_txt_exporter import exportar_polizas_contpaqi_txt
from licencia import verificar_licencia_empresa, LicenciaInvalida

from db import get_connection


def insertar_movimientos(empresa_id, documento_id, movimientos):
    con = get_connection()
    cur = con.cursor()
    ids = []
    for mov in movimientos:
        cur.execute(
            """INSERT INTO movimientos
               (empresa_id, documento_id, fecha, descripcion, descripcion_normalizada,
                tipo, total, rfc_contraparte, cuenta_bancaria_contraparte,
                referencia_bancaria, numero_factura, fila_original, estado_clasificacion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente')""",
            (
                empresa_id, documento_id, mov["fecha"].strftime("%Y-%m-%d"),
                mov["descripcion"], normalizar_texto(mov["descripcion"]),
                mov["tipo"], mov["total"], mov.get("rfc_contraparte"),
                mov.get("cuenta_bancaria_contraparte"), mov.get("referencia_bancaria"),
                mov.get("numero_factura") or "", mov.get("fila_original"),
            ),
        )
        ids.append(cur.lastrowid)
    con.commit()
    con.close()
    return ids



import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "core")))
from ml_engine import EntrenadorML

def registrar_memoria_ml_exitosa(empresa_id, descripcion, tipo, regla_id):
    con = get_connection()
    try:
        con.execute(
            """INSERT INTO memoria_ml (empresa_id, descripcion_limpia, tipo, regla_asignada_id) 
               VALUES (?, ?, ?, ?)
               ON CONFLICT(empresa_id, descripcion_limpia, tipo, regla_asignada_id) 
               DO UPDATE SET frecuencia = memoria_ml.frecuencia + 1, ultima_vez = CURRENT_TIMESTAMP""",
            (empresa_id, str(descripcion).strip(), str(tipo).strip(), regla_id)
        )
        con.commit()
    finally:
        con.close()

def entrenar_modelo_empresa(empresa_id):
    con = get_connection()
    datos = con.execute("SELECT descripcion_limpia as descripcion, tipo, regla_asignada_id as regla_id FROM memoria_ml WHERE empresa_id = ?", (empresa_id,)).fetchall()
    con.close()
    if datos:
        EntrenadorML.entrenar(empresa_id, [dict(d) for d in datos])

def _fila_a_movimiento_dict(fila):
    return {
        "id": fila["id"],
        "empresa_id": fila["empresa_id"],
        "fecha": datetime.strptime(fila["fecha"], "%Y-%m-%d"),
        "descripcion": fila["descripcion"],
        "tipo": fila["tipo"],
        "total": fila["total"],
        "rfc_contraparte": fila["rfc_contraparte"],
        "cuenta_bancaria_contraparte": fila["cuenta_bancaria_contraparte"],
        "numero_factura": fila["numero_factura"],
        "tiene_iva": True,
        "ret_iva": 0.0,
        "ret_isr": 0.0,
        "tipo_cambio": 1.0,
    }


def clasificar_pendientes(empresa_id):

    con = get_connection()
    emp_cfg = con.execute("SELECT tasa_iva, tasa_retencion_iva, tasa_retencion_isr FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    if emp_cfg:
        tasa_iva = emp_cfg["tasa_iva"]
        tasa_ret_iva = emp_cfg["tasa_retencion_iva"]
        tasa_ret_isr = emp_cfg["tasa_retencion_isr"]
    else:
        tasa_ret_iva = 0.0
        tasa_ret_isr = 0.0

    """Corre el motor de reglas sobre los movimientos pendientes de la
    empresa y actualiza su estado. Regresa cuántos quedaron
    automáticos y cuántos siguen pendientes."""
    repo = RepositorioReglas()
    reglas, plantillas = repo.cargar_para_motor(empresa_id)

    con = get_connection()
    pendientes = con.execute(
        "SELECT * FROM movimientos WHERE empresa_id = ? AND estado_clasificacion = 'pendiente'",
        (empresa_id,),
    ).fetchall()

    automaticos = 0
    usos_por_regla = {}
    for fila in pendientes:
        mov = _fila_a_movimiento_dict(fila)
        match = encontrar_regla(mov, reglas)
        if match.regla is None:
            continue

        resultado = generar_poliza(
            movimiento=mov, plantilla=plantillas[match.regla.id],
            nombre_regla=match.regla.nombre, motivo_match=match.motivo,
            tasa_iva=tasa_iva, tasa_ret_iva=tasa_ret_iva, tasa_ret_isr=tasa_ret_isr
        )
        if not resultado.cuadrada:
            continue

        con.execute(
            """UPDATE movimientos
               SET regla_id = ?, confianza_clasificacion = ?, estado_clasificacion = 'automatico'
               WHERE id = ?""",
            (match.regla.id, match.confianza, fila["id"]),
        )
        usos_por_regla[match.regla.id] = usos_por_regla.get(match.regla.id, 0) + 1
        automaticos += 1
        registrar_memoria_ml_exitosa(empresa_id, mov["descripcion"], mov["tipo"], match.regla.id)

    con.commit()
    con.close()

    for regla_id, veces in usos_por_regla.items():
        for _ in range(veces):
            repo.registrar_uso(regla_id)

    return {"automaticos": automaticos, "pendientes_restantes": len(pendientes) - automaticos}


def listar_movimientos(empresa_id, estado=None):
    con = get_connection()
    query = "SELECT * FROM movimientos WHERE empresa_id = ?"
    params = [empresa_id]
    if estado:
        query += " AND estado_clasificacion = ?"
        params.append(estado)
    query += " ORDER BY fecha DESC, id DESC"
    filas = con.execute(query, params).fetchall()
    con.close()
    return filas


def sugerencia_para_movimiento(movimiento_id):
    con = get_connection()
    fila = con.execute("SELECT * FROM movimientos WHERE id = ?", (movimiento_id,)).fetchone()
    con.close()
    if fila is None:
        return None, None
    mov = _fila_a_movimiento_dict(fila)
    return mov, sugerir_regla_desde_clasificacion_manual(mov)


def generar_polizas_pendientes(empresa_id):

    con = get_connection()
    emp_cfg = con.execute("SELECT tasa_iva, tasa_retencion_iva, tasa_retencion_isr FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    if emp_cfg:
        tasa_iva = emp_cfg["tasa_iva"]
        tasa_ret_iva = emp_cfg["tasa_retencion_iva"]
        tasa_ret_isr = emp_cfg["tasa_retencion_isr"]
    else:
        tasa_ret_iva = 0.0
        tasa_ret_isr = 0.0

    """Genera pólizas para todos los movimientos ya clasificados
    (estado 'automatico' o 'manual') que todavía no tienen póliza."""
    con_lic = get_connection()
    empresa_lic = con_lic.execute("SELECT nombre FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    con_lic.close()
    verificar_licencia_empresa(empresa_lic["nombre"] if empresa_lic else "")

    repo = RepositorioReglas()
    _, plantillas = repo.cargar_para_motor(empresa_id)

    con = get_connection()
    movimientos = con.execute(
        """SELECT * FROM movimientos
           WHERE empresa_id = ? AND poliza_id IS NULL
           AND estado_clasificacion IN ('automatico', 'manual')""",
        (empresa_id,),
    ).fetchall()

    ultimo_ingreso = con.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM polizas WHERE empresa_id = ? AND tipo = 'ingreso'",
        (empresa_id,),
    ).fetchone()[0]
    ultimo_egreso = con.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM polizas WHERE empresa_id = ? AND tipo = 'egreso'",
        (empresa_id,),
    ).fetchone()[0]

    generadas = 0
    cur = con.cursor()

    for fila in movimientos:
        if fila["regla_id"] is None:
            continue
        plantilla = plantillas.get(fila["regla_id"])
        if not plantilla:
            continue

        mov = _fila_a_movimiento_dict(fila)
        cur.execute("SELECT nombre FROM reglas WHERE id = ?", (fila["regla_id"],))
        nombre_regla = cur.fetchone()["nombre"]

        resultado = generar_poliza(
            movimiento=mov, plantilla=plantilla, nombre_regla=nombre_regla,
            motivo_match="Reclasificación al generar póliza.", tasa_iva=tasa_iva, tasa_ret_iva=tasa_ret_iva, tasa_ret_isr=tasa_ret_isr
        )
        if not resultado.cuadrada:
            continue

        if fila["tipo"] == "ingreso":
            ultimo_ingreso += 1
            numero = ultimo_ingreso
        else:
            ultimo_egreso += 1
            numero = ultimo_egreso

        cur.execute(
            """INSERT INTO polizas (empresa_id, tipo, numero, fecha, referencia, cuadrada)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (empresa_id, fila["tipo"], numero, fila["fecha"], mov["numero_factura"]),
        )
        poliza_id = cur.lastrowid

        for orden, linea in enumerate(resultado.lineas):
            cur.execute(
                """INSERT INTO poliza_lineas
                   (poliza_id, orden, cuenta, naturaleza, importe, descripcion, formula_usada)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (poliza_id, orden, linea.cuenta, linea.naturaleza, linea.importe,
                 linea.descripcion, linea.formula_usada),
            )

        for paso, texto in enumerate(resultado.explicacion):
            cur.execute(
                "INSERT INTO poliza_auditoria (poliza_id, paso, detalle) VALUES (?, ?, ?)",
                (poliza_id, paso, texto),
            )

        cur.execute("UPDATE movimientos SET poliza_id = ? WHERE id = ?", (poliza_id, fila["id"]))
        generadas += 1

    con.commit()
    con.close()
    return generadas


def exportar_polizas(empresa_id, ruta_salida):
    con = get_connection()

    empresa = con.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    try:
        verificar_licencia_empresa(empresa["nombre"] if empresa else "")
    except LicenciaInvalida:
        con.close()
        raise

    polizas = con.execute(
        "SELECT * FROM polizas WHERE empresa_id = ? ORDER BY tipo, numero", (empresa_id,)
    ).fetchall()

    movimientos_poliza = []
    
    # Eager Loading para N+1
    map_lineas = {}
    map_movs = {}
    if polizas:
        p_ids = [str(p["id"]) for p in polizas]
        placeholders = ",".join(p_ids)
        
        todas_lineas = con.execute(f"SELECT * FROM poliza_lineas WHERE poliza_id IN ({placeholders}) ORDER BY poliza_id, orden").fetchall()
        for l in todas_lineas:
            pid = l["poliza_id"]
            if pid not in map_lineas: map_lineas[pid] = []
            map_lineas[pid].append(l)
            
        todos_movs = con.execute(f"""SELECT m.*, b.cuenta_contable AS cuenta_banco
           FROM movimientos m
           LEFT JOIN documentos_importados d ON d.id = m.documento_id
           LEFT JOIN bancos b ON b.id = d.banco_id
           WHERE m.poliza_id IN ({placeholders})""").fetchall()
        for m in todos_movs:
            map_movs[m["poliza_id"]] = m

    for p in polizas:
        lineas_db = map_lineas.get(p["id"], [])
        mov_db = map_movs.get(p["id"])

        class _Linea:
            def __init__(self, fila):
                self.cuenta = fila["cuenta"]
                self.naturaleza = fila["naturaleza"]
                self.importe = fila["importe"]
                self.descripcion = fila["descripcion"]

        lineas = [_Linea(f) for f in lineas_db]

        cfdi_filas = con.execute(
            """SELECT cm.importe_aplicado, c.id AS cfdi_id, c.uuid, c.serie, c.folio,
                      c.total AS cfdi_total, c.tipo AS cfdi_tipo,
                      c.rfc_emisor, c.rfc_receptor
               FROM cfdi_movimiento cm JOIN cfdis c ON c.id = cm.cfdi_id
               WHERE cm.movimiento_id = ? AND cm.confirmado = 1""",
            (mov_db["id"] if mov_db else -1,),
        ).fetchall()

        cfdi_uuid = cfdi_serie = cfdi_folio = None
        cfdi_impuestos = []
        facturas = []
        cuenta_banco_mov = None

        cuenta_banco_real = mov_db["cuenta_banco"] if mov_db and mov_db["cuenta_banco"] else "1020001"

        if cfdi_filas:
            # Un movimiento puede quedar ligado a varias facturas (pago
            # combinado, referencia "VARIOS" en Contpaqi): cada una se
            # exporta como su propia FacturaAplicada, con sus propios
            # impuestos prorrateados si el importe aplicado es parcial
            # del total de esa factura (pago parcial/abono).
            cuenta_banco_mov = cuenta_banco_real.replace("-", "")

            for cf in cfdi_filas:
                factor = (cf["importe_aplicado"] / cf["cfdi_total"]) if cf["cfdi_total"] else 1.0
                impuestos_db = con.execute(
                    "SELECT * FROM cfdi_impuestos WHERE cfdi_id = ?", (cf["cfdi_id"],)
                ).fetchall()
                impuestos_factura = [
                    ImpuestoPoliza(
                        base=round(i["base"] * factor, 2),
                        importe=round(i["importe"] * factor, 2),
                        tasa=i["tasa"],
                        es_retencion=bool(i["es_retencion"]),
                        tipo_impuesto=i["tipo_impuesto"] or "IVA",
                    )
                    for i in impuestos_db
                ]
                # RFC de la contraparte de ESTA factura: si el CFDI es
                # 'recibido' (egreso), la contraparte es el emisor; si es
                # 'emitido' (ingreso), es el receptor.
                rfc_persona = (
                    cf["rfc_emisor"] if cf["cfdi_tipo"] == "recibido" else cf["rfc_receptor"]
                ) or ""
                facturas.append(FacturaAplicada(
                    uuid=cf["uuid"], serie=cf["serie"] or "", folio=cf["folio"] or "",
                    rfc_persona=rfc_persona, impuestos=impuestos_factura,
                ))
                cfdi_impuestos.extend(impuestos_factura)

            # Compatibilidad hacia atrás (un solo CFDI): se llenan también
            # los campos singulares por si algo más los sigue leyendo.
            if len(facturas) == 1:
                cfdi_uuid, cfdi_serie, cfdi_folio = facturas[0].uuid, facturas[0].serie, facturas[0].folio
        elif mov_db and (mov_db["afectable_impuestos"] is None or mov_db["afectable_impuestos"]):
            # Sin CFDI conciliado, pero el movimiento SÍ afecta impuestos
            # (se clasificó a mano): igual debe llevar F4/F6. Si se marcó
            # "aplica IVA" al clasificarlo, la línea de IVA que ya generó
            # policy_generator (contra la cuenta de IVA acreditable/
            # trasladado configurada) nos dice cuánto es; si no se marcó,
            # se llena en exento (base = total, IVA = 0, tasa = 0).
            #
            # Las RETENCIONES NO tienen método alterno: solo existen si
            # vienen del CFDI (<Retenciones> del XML). Sin CFDI conciliado
            # no se calcula ni se estima ninguna retención aquí — decisión
            # explícita del usuario, no un pendiente.
            cuenta_banco_mov = cuenta_banco_real.replace("-", "")
            cuenta_iva_esperada = (
                empresa["cuenta_iva_acreditable"] if p["tipo"] == "egreso"
                else empresa["cuenta_iva_trasladado"]
            ) if empresa else None
            cuenta_iva_esperada = str(cuenta_iva_esperada or "").replace("-", "")

            linea_iva = next(
                (l for l in lineas if str(l.cuenta).replace("-", "") == cuenta_iva_esperada
                 and cuenta_iva_esperada), None
            )
            total_mov = mov_db["total"]
            if linea_iva:
                importe_iva = round(linea_iva.importe, 2)
                cfdi_impuestos.append(ImpuestoPoliza(
                    base=round(total_mov - importe_iva, 2),
                    importe=importe_iva,
                    tasa=empresa["tasa_iva"] if empresa else 0.16,
                ))
            else:
                cfdi_impuestos.append(ImpuestoPoliza(base=round(total_mov, 2), importe=0.0, tasa=0.0))

        movimientos_poliza.append(MovimientoPoliza(
            numero_poliza=p["numero"], tipo=p["tipo"],
            fecha=datetime.strptime(p["fecha"], "%Y-%m-%d"),
            descripcion=mov_db["descripcion"] if mov_db else "",
            lineas=lineas, tiene_iva=bool(cfdi_uuid or facturas),
            numero_factura=p["referencia"] or "",
            cfdi_uuid=cfdi_uuid, cfdi_serie=cfdi_serie, cfdi_folio=cfdi_folio,
            cfdi_impuestos=cfdi_impuestos, facturas=facturas, cuenta_banco=cuenta_banco_mov,
        ))

    con.close()
    # Salida en .txt (layout de importación de Contpaqi), ya no .xls: el
    # archivo de Excel salía del proceso de conversión con LibreOffice,
    # que ya no se usa para esta exportación.
    return exportar_polizas_contpaqi_txt(movimientos_poliza, ruta_salida,
                                          nombre_empresa=empresa["nombre"] if empresa else None)
