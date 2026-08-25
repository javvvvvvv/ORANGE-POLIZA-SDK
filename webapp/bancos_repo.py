from db import get_connection


def listar_bancos(empresa_id):
    con = get_connection()
    filas = con.execute(
        "SELECT * FROM bancos WHERE empresa_id = ? ORDER BY nombre", (empresa_id,)
    ).fetchall()
    con.close()
    return filas


def crear_banco(empresa_id, nombre, cuenta_contable, moneda="MXN"):
    con = get_connection()
    con.execute(
        "INSERT INTO bancos (empresa_id, nombre, cuenta_contable, moneda) VALUES (?, ?, ?, ?)",
        (empresa_id, nombre, cuenta_contable, moneda),
    )
    con.commit()
    con.close()


def eliminar_banco(banco_id):
    con = get_connection()
    con.execute("DELETE FROM bancos WHERE id = ?", (banco_id,))
    con.commit()
    con.close()


def obtener_empresa(empresa_id):
    con = get_connection()
    fila = con.execute("SELECT * FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    con.close()
    return fila


def actualizar_configuracion_iva(empresa_id, datos):
    con = get_connection()
    con.execute(
        """UPDATE empresas SET
           tasa_iva = ?, cuenta_iva_acreditable = ?, cuenta_iva_por_acreditar = ?,
           cuenta_iva_trasladado = ?, cuenta_iva_por_trasladar = ?,
           cuenta_complementaria_ingresos = ?, cuenta_complementaria_egresos = ?,
           cuenta_dif_cambiaria = ?, retenciones_activas = ?
           WHERE id = ?""",
        (
            datos["tasa_iva"], datos.get("cuenta_iva_acreditable"),
            datos.get("cuenta_iva_por_acreditar"), datos.get("cuenta_iva_trasladado"),
            datos.get("cuenta_iva_por_trasladar"), datos.get("cuenta_complementaria_ingresos"),
            datos.get("cuenta_complementaria_egresos"), datos.get("cuenta_dif_cambiaria"),
            1 if datos.get("retenciones_activas") else 0, empresa_id,
        ),
    )
    con.commit()
    con.close()
