# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from db import get_connection
from auth import login_required, gerente_requerido, log_audit
from werkzeug.security import generate_password_hash

despacho_bp = Blueprint("despacho", __name__)

@despacho_bp.route("/despacho/usuarios")
@login_required
@gerente_requerido
def listar_usuarios():
    con = get_connection()
    usuarios = con.execute("SELECT * FROM usuarios WHERE organizacion_id = ? ORDER BY id DESC", (g.usuario["organizacion_id"],)).fetchall()
    con.close()
    return render_template("despacho_usuarios.html", usuarios=usuarios)

@despacho_bp.route("/despacho/usuarios/nuevo", methods=["POST"])
@login_required
@gerente_requerido
def nuevo_usuario():
    nombre = request.form.get("nombre")
    usuario = request.form.get("usuario")
    password = request.form.get("password")
    rol = request.form.get("rol", "analista")
    
    if not all([nombre, usuario, password]):
        flash("Todos los campos son obligatorios.", "error")
        return redirect(url_for("despacho.listar_usuarios"))
        
    con = get_connection()
    existente = con.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
    if existente:
        flash("El nombre de usuario ya está en uso.", "error")
        con.close()
        return redirect(url_for("despacho.listar_usuarios"))
        
    con.execute("INSERT INTO usuarios (organizacion_id, nombre, usuario, password_hash, rol_global) VALUES (?, ?, ?, ?, ?)",
                (g.usuario["organizacion_id"], nombre, usuario, generate_password_hash(password), rol))
    con.commit()
    con.close()
    
    log_audit(g.usuario["organizacion_id"], g.usuario["id"], "Crear Usuario", f"Se creó el usuario {usuario} ({rol})")
    flash("Usuario creado con éxito.", "exito")
    return redirect(url_for("despacho.listar_usuarios"))

@despacho_bp.route("/despacho/usuarios/<int:user_id>/eliminar", methods=["POST"])
@login_required
@gerente_requerido
def eliminar_usuario(user_id):
    if user_id == g.usuario["id"]:
        flash("No puedes eliminarte a ti mismo.", "error")
        return redirect(url_for("despacho.listar_usuarios"))
        
    con = get_connection()
    u = con.execute("SELECT usuario FROM usuarios WHERE id = ? AND organizacion_id = ?", (user_id, g.usuario["organizacion_id"])).fetchone()
    if u:
        con.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
        con.commit()
        log_audit(g.usuario["organizacion_id"], g.usuario["id"], "Eliminar Usuario", f"Se eliminó el usuario {u['usuario']}")
        flash("Usuario eliminado.", "exito")
    else:
        flash("Usuario no encontrado.", "error")
    con.close()
    return redirect(url_for("despacho.listar_usuarios"))

@despacho_bp.route("/despacho/bitacora")
@login_required
@gerente_requerido
def ver_bitacora():
    con = get_connection()
    logs = con.execute('''
        SELECT a.*, u.nombre as usuario_nombre
        FROM auditoria_despacho a
        LEFT JOIN usuarios u ON a.usuario_id = u.id
        WHERE a.organizacion_id = ?
        ORDER BY a.id DESC LIMIT 200
    ''', (g.usuario["organizacion_id"],)).fetchall()
    con.close()
    return render_template("despacho_bitacora.html", logs=logs)
