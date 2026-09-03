# -*- coding: utf-8 -*-
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
"""
Repositorio de reglas para Orange Poliza Engine.

Esto es lo que hace que las reglas sean "configurables por datos" de
verdad: en vez de vivir como una lista de `Regla(...)` escrita a mano en
un script (como en los demos anteriores), viven en una base SQLite en
disco y se pueden agregar, quitar, activar/desactivar y editar en
cualquier momento, sin tocar cÃ³digo. Cuando pasemos a producciÃ³n con
Claude Code, este mismo repositorio se vuelve una capa sobre PostgreSQL
(las tablas ya estÃ¡n definidas en database/schema.sql); la interfaz de
este mÃ³dulo no deberÃ­a cambiar.

Uso tÃ­pico:

    repo = RepositorioReglas()

    regla_id = repo.crear_regla(
        empresa_id=1,
        nombre="Compras en Farmacias del Ahorro",
        tipo_movimiento="egreso",
        palabras_clave=["FARMACIAS DEL AHORRO", "FAHORRO"],
        plantilla=[
            {"cuenta": "6010-005", "naturaleza": "cargo", "formula": "BASE"},
            {"cuenta": "1180-001", "naturaleza": "cargo", "formula": "IVA"},
            {"cuenta": "1020-001", "naturaleza": "abono", "formula": "TOTAL"},
        ],
    )

    repo.desactivar_regla(regla_id)      # deja de aplicarse sin borrarla
    repo.eliminar_regla(regla_id)        # la borra por completo (con su plantilla)

    reglas, plantillas = repo.cargar_para_motor(empresa_id=1)
    # listas para pasarle directo a rule_engine.encontrar_regla(...)
"""

from typing import Optional

from db import get_connection
from rule_engine import Regla


class RepositorioReglas:
    """Las tablas que usa este repositorio (reglas, regla_palabras_clave,
    plantilla_movimientos) ya se crean en database/schema.sql al
    arrancar el servidor (ver db.inicializar_db()), asÃ­ que este
    repositorio solo se conecta con db.get_connection(); ya no recibe
    ruta de archivo porque la base ahora es PostgreSQL, compartida por
    todas las instancias de la app."""

    def _conectar(self):
        return get_connection()

    # -----------------------------------------------------------------
    # Crear / editar
    # -----------------------------------------------------------------

    def crear_regla(
        self,
        empresa_id: int,
        nombre: str,
        plantilla: list[dict],
        prioridad: int = 100,
        tipo_movimiento: Optional[str] = None,
        rfc_contraparte: Optional[str] = None,
        cuenta_bancaria_contraparte: Optional[str] = None,
        descripcion_exacta: Optional[str] = None,
        palabras_clave: Optional[list[str]] = None,
        creada_por: Optional[int] = None,
    ) -> int:
        """Crea una regla completa (condiciones + plantilla de movimientos)
        y regresa su id. `plantilla` es una lista de dicts:
        {"cuenta": ..., "naturaleza": "cargo"|"abono", "formula": ...,
         "descripcion_linea": ... (opcional)}"""
        con = self._conectar()
        cur = con.cursor()
        cur.execute(
            """INSERT INTO reglas
               (empresa_id, nombre, prioridad, activa, rfc_contraparte,
                cuenta_bancaria_contraparte, descripcion_exacta,
                tipo_movimiento, creada_por)
               VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)""",
            (empresa_id, nombre, prioridad, rfc_contraparte,
             cuenta_bancaria_contraparte, descripcion_exacta,
             tipo_movimiento, creada_por),
        )
        regla_id = cur.lastrowid

        for palabra in (palabras_clave or []):
            cur.execute(
                "INSERT INTO regla_palabras_clave (regla_id, palabra) VALUES (?, ?)",
                (regla_id, palabra),
            )

        for orden, linea in enumerate(plantilla):
            cur.execute(
                """INSERT INTO plantilla_movimientos
                   (regla_id, orden, cuenta, naturaleza, formula, descripcion_linea)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (regla_id, orden, linea["cuenta"], linea["naturaleza"],
                 linea["formula"], linea.get("descripcion_linea")),
            )

        con.commit()
        con.close()
        return regla_id

    def agregar_palabra_clave(self, regla_id: int, palabra: str):
        con = self._conectar()
        con.execute(
            "INSERT INTO regla_palabras_clave (regla_id, palabra) VALUES (?, ?)",
            (regla_id, palabra),
        )
        con.commit()
        con.close()

    def quitar_palabra_clave(self, regla_id: int, palabra: str):
        con = self._conectar()
        con.execute(
            "DELETE FROM regla_palabras_clave WHERE regla_id = ? AND palabra = ?",
            (regla_id, palabra),
        )
        con.commit()
        con.close()

    def agregar_linea_plantilla(self, regla_id: int, cuenta: str, naturaleza: str,
                                 formula: str, descripcion_linea: Optional[str] = None,
                                 orden: Optional[int] = None):
        """Agrega un movimiento mÃ¡s a la pÃ³liza que genera esta regla
        (ej. "ademÃ¡s, agrega un cargo del 4% a tal cuenta")."""
        con = self._conectar()
        cur = con.cursor()
        if orden is None:
            cur.execute(
                "SELECT COALESCE(MAX(orden), -1) + 1 FROM plantilla_movimientos WHERE regla_id = ?",
                (regla_id,),
            )
            orden = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO plantilla_movimientos
               (regla_id, orden, cuenta, naturaleza, formula, descripcion_linea)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (regla_id, orden, cuenta, naturaleza, formula, descripcion_linea),
        )
        con.commit()
        con.close()
        return cur.lastrowid

    def quitar_linea_plantilla(self, linea_id: int):
        con = self._conectar()
        con.execute("DELETE FROM plantilla_movimientos WHERE id = ?", (linea_id,))
        con.commit()
        con.close()

    def activar_regla(self, regla_id: int):
        self._set_activa(regla_id, True)

    def desactivar_regla(self, regla_id: int):
        self._set_activa(regla_id, False)

    def _set_activa(self, regla_id: int, activa: bool):
        con = self._conectar()
        con.execute("UPDATE reglas SET activa = ? WHERE id = ?", (1 if activa else 0, regla_id))
        con.commit()
        con.close()

    def eliminar_regla(self, regla_id: int):
        """Borra la regla por completo, junto con sus palabras clave y
        su plantilla de movimientos (ON DELETE CASCADE)."""
        con = self._conectar()
        con.execute("DELETE FROM reglas WHERE id = ?", (regla_id,))
        con.commit()
        con.close()

    def registrar_uso(self, regla_id: int):
        """Se llama cada vez que una regla se aplica a un movimiento;
        sirve para saber cuÃ¡les reglas son las mÃ¡s usadas."""
        con = self._conectar()
        con.execute(
            "UPDATE reglas SET veces_aplicada = veces_aplicada + 1 WHERE id = ?",
            (regla_id,),
        )
        con.commit()
        con.close()

    # -----------------------------------------------------------------
    # Consultar
    # -----------------------------------------------------------------

    def listar_reglas(self, empresa_id: int, solo_activas: bool = False) -> list[dict]:
        con = self._conectar()
        query = "SELECT * FROM reglas WHERE empresa_id = ?"
        params = [empresa_id]
        if solo_activas:
            query += " AND activa = 1"
        query += " ORDER BY prioridad ASC"
        filas = con.execute(query, params).fetchall()
        resultado = [dict(f) for f in filas]
        con.close()
        return resultado

    def obtener_plantilla(self, regla_id: int) -> list[dict]:
        con = self._conectar()
        filas = con.execute(
            "SELECT * FROM plantilla_movimientos WHERE regla_id = ? ORDER BY orden ASC",
            (regla_id,),
        ).fetchall()
        con.close()
        return [dict(f) for f in filas]

    def obtener_palabras_clave(self, regla_id: int) -> list[str]:
        con = self._conectar()
        filas = con.execute(
            "SELECT palabra FROM regla_palabras_clave WHERE regla_id = ?",
            (regla_id,),
        ).fetchall()
        con.close()
        return [f[0] for f in filas]

    def cargar_para_motor(self, empresa_id: int):
        """
        Trae todas las reglas activas de una empresa ya armadas como
        objetos `Regla` (de rule_engine.py), listas para pasarle a
        `encontrar_regla(movimiento, reglas)`, junto con un diccionario
        {regla_id: [LineaPlantilla, ...]} para generar_poliza().
        """
        from policy_generator import LineaPlantilla  # import local para evitar ciclos

        reglas_raw = self.listar_reglas(empresa_id, solo_activas=True)
        reglas = []
        plantillas = {}

        for r in reglas_raw:
            palabras = self.obtener_palabras_clave(r["id"])
            reglas.append(Regla(
                id=r["id"],
                empresa_id=r["empresa_id"],
                nombre=r["nombre"],
                prioridad=r["prioridad"],
                activa=bool(r["activa"]),
                rfc_contraparte=r["rfc_contraparte"],
                cuenta_bancaria_contraparte=r["cuenta_bancaria_contraparte"],
                descripcion_exacta=r["descripcion_exacta"],
                descripcion_contiene=palabras,
                tipo_movimiento=r["tipo_movimiento"],
            ))

            lineas_raw = self.obtener_plantilla(r["id"])
            plantillas[r["id"]] = [
                LineaPlantilla(
                    cuenta=l["cuenta"],
                    naturaleza=l["naturaleza"],
                    formula=l["formula"],
                    descripcion_linea=l["descripcion_linea"],
                )
                for l in lineas_raw
            ]

        return reglas, plantillas

