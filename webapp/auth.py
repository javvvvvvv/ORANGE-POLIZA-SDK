from functools import wraps



from flask import g, redirect, request, session, url_for, flash



from db import get_connection





def login_required(vista):

    @wraps(vista)

    def envoltura(*args, **kwargs):

        if "usuario_id" not in session:

            return redirect(url_for("auth.login"))

        return vista(*args, **kwargs)

    return envoltura





def empresa_requerida(vista):

    """Verifica que el usuario tenga acceso a la empresa del URL y, de

    paso, bloquea cualquier mÃ©todo que modifique datos (POST/PUT/DELETE)

    si su rol en esa empresa es 'lector' â€” sin esto, "solo lectura"

    no significaba nada: cualquier rol podÃ­a borrar el catÃ¡logo,

    cambiar la config de IVA, eliminar bancos, etc."""

    @wraps(vista)

    def envoltura(empresa_id, *args, **kwargs):

        rol = obtener_rol_en_empresa(session["usuario_id"], empresa_id)

        if rol is None:

            return "No tienes acceso a esta empresa.", 403

        if rol == "lector" and request.method != "GET":

            return "Tu rol es de solo lectura en esta empresa.", 403

        g.empresa_id = empresa_id

        g.rol_empresa = rol

        return vista(empresa_id, *args, **kwargs)

    return envoltura





def obtener_empresas_del_usuario(usuario_id):
    con = get_connection()
    usr = con.execute("SELECT organizacion_id, rol_global FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if not usr:
        con.close()
        return []
    
    org_id = usr["organizacion_id"]
    rol = usr["rol_global"]
    
    filas = con.execute(
        "SELECT id, nombre, rfc, tasa_iva, ? as rol FROM empresas WHERE organizacion_id = ? AND activa = 1 ORDER BY nombre",
        (rol, org_id)
    ).fetchall()
    con.close()
    return filas





def obtener_rol_en_empresa(usuario_id, empresa_id):
    con = get_connection()
    usr = con.execute("SELECT organizacion_id, rol_global FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if not usr:
        con.close()
        return None
    
    emp = con.execute("SELECT id FROM empresas WHERE id = ? AND organizacion_id = ?", (empresa_id, usr["organizacion_id"])).fetchone()
    con.close()
    
    if emp:
        return usr["rol_global"]
    return None if fila else None


from werkzeug.exceptions import abort

def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            token = session.get('_csrf_token', None)
            if not token or token != request.form.get('csrf_token'):
                abort(403, description='Token CSRF inválido o expirado. Vuelve atrás, recarga la página e inténtalo de nuevo.')
        return f(*args, **kwargs)
    return decorated_function






def gerente_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.usuario.get("rol_global") not in ("superadmin", "gerente", "admin"):
            flash("No tienes permisos de gerente para realizar esta acción.", "error")
            return redirect(url_for("empresas.selector_empresas"))
        return f(*args, **kwargs)
    return decorated_function

def log_audit(organizacion_id, usuario_id, accion, detalle=""):
    from db import get_connection
    con = get_connection()
    try:
        con.execute("INSERT INTO auditoria_despacho (organizacion_id, usuario_id, accion, detalle) VALUES (?, ?, ?, ?)",
                    (organizacion_id, usuario_id, accion, detalle))
        con.commit()
    finally:
        con.close()

def superadmin_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("auth.login"))
        con = get_connection()
        usr = con.execute("SELECT rol_global FROM usuarios WHERE id = ?", (session["usuario_id"],)).fetchone()
        con.close()
        if not usr or usr["rol_global"] != "superadmin":
            from flask import flash
            flash("Acceso denegado: Se requiere permiso de Super Administrador SaaS.", "error")
            return redirect(url_for("empresas.lista_empresas"))
        return vista(*args, **kwargs)
    return envoltura

def admin_despacho_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("auth.login"))
        con = get_connection()
        usr = con.execute("SELECT rol_global FROM usuarios WHERE id = ?", (session["usuario_id"],)).fetchone()
        con.close()
        if not usr or usr["rol_global"] not in ("superadmin", "admin"):
            from flask import flash
            flash("Acceso denegado: Se requiere permiso de Administrador de Despacho.", "error")
            return redirect(url_for("empresas.lista_empresas"))
        return vista(*args, **kwargs)
    return envoltura
