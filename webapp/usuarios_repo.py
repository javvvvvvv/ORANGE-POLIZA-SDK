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
from werkzeug.security import generate_password_hash

from db import get_connection


def listar_usuarios_de_empresa(empresa_id):
    con = get_connection()
    filas = con.execute(
        """SELECT u.id, u.nombre, u.usuario, u.correo, ue.rol
           FROM usuarios u JOIN usuario_empresa ue ON ue.usuario_id = u.id
           WHERE ue.empresa_id = ? ORDER BY u.nombre""",
        (empresa_id,),
    ).fetchall()
    con.close()
    return filas


def buscar_usuario_por_usuario(usuario):
    """Login es global por nombre de usuario (no depende de la empresa
    ni de la organizaciÃ³n): dos organizaciones no pueden compartir el
    mismo nombre de usuario, asÃ­ que basta buscarlo directo."""
    con = get_connection()
    fila = con.execute(
        "SELECT * FROM usuarios WHERE usuario = ?",
        (usuario.strip().lower(),),
    ).fetchone()
    con.close()
    return fila


def buscar_usuario_por_usuario_en_organizacion(organizacion_id, usuario):
    con = get_connection()
    fila = con.execute(
        "SELECT * FROM usuarios WHERE organizacion_id = ? AND usuario = ?",
        (organizacion_id, usuario.strip().lower()),
    ).fetchone()
    con.close()
    return fila


def usuario_disponible(usuario):
    return buscar_usuario_por_usuario(usuario) is None


def crear_usuario(organizacion_id, nombre, usuario, password, correo=None, rol_global="usuario"):
    usuario_norm = usuario.strip().lower()
    correo_norm = (correo or "").strip().lower() or None
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        """INSERT INTO usuarios (organizacion_id, nombre, usuario, correo, password_hash, rol_global)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (organizacion_id, nombre, usuario_norm, correo_norm, generate_password_hash(password), rol_global),
    )
    usuario_id = cur.lastrowid
    con.commit()
    con.close()
    return usuario_id


def asignar_a_empresa(usuario_id, empresa_id, rol):
    con = get_connection()
    con.execute(
        """INSERT INTO usuario_empresa (usuario_id, empresa_id, rol) VALUES (?, ?, ?)
           ON CONFLICT(usuario_id, empresa_id) DO UPDATE SET rol = excluded.rol""",
        (usuario_id, empresa_id, rol),
    )
    con.commit()
    con.close()


def quitar_de_empresa(usuario_id, empresa_id):
    con = get_connection()
    con.execute(
        "DELETE FROM usuario_empresa WHERE usuario_id = ? AND empresa_id = ?",
        (usuario_id, empresa_id),
    )
    con.commit()
    con.close()


def obtener_organizacion_de_empresa(empresa_id):
    con = get_connection()
    fila = con.execute("SELECT organizacion_id FROM empresas WHERE id = ?", (empresa_id,)).fetchone()
    con.close()
    return fila["organizacion_id"] if fila else None

