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
from db import get_connection


def listar(empresa_id, tipo_movimiento=None):
    con = get_connection()
    if tipo_movimiento:
        filas = con.execute(
            "SELECT * FROM reglas_generales WHERE empresa_id = ? AND tipo_movimiento = ? ORDER BY orden",
            (empresa_id, tipo_movimiento),
        ).fetchall()
    else:
        filas = con.execute(
            "SELECT * FROM reglas_generales WHERE empresa_id = ? ORDER BY tipo_movimiento, orden",
            (empresa_id,),
        ).fetchall()
    con.close()
    return filas


def agregar(empresa_id, tipo_movimiento, cuenta, naturaleza, formula, descripcion_linea=None):
    con = get_connection()
    cur = con.cursor()
    orden = cur.execute(
        "SELECT COALESCE(MAX(orden), -1) + 1 FROM reglas_generales WHERE empresa_id = ? AND tipo_movimiento = ?",
        (empresa_id, tipo_movimiento),
    ).fetchone()[0]
    cur.execute(
        """INSERT INTO reglas_generales
           (empresa_id, tipo_movimiento, orden, cuenta, naturaleza, formula, descripcion_linea)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (empresa_id, tipo_movimiento, orden, cuenta, naturaleza, formula, descripcion_linea),
    )
    con.commit()
    con.close()


def eliminar(linea_id):
    con = get_connection()
    con.execute("DELETE FROM reglas_generales WHERE id = ?", (linea_id,))
    con.commit()
    con.close()

