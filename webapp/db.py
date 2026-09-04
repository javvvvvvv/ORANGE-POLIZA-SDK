# ============================================================================
#    PROPIEDAD INTELECTUAL Y LICENCIA COMERCIAL CERRADA
#    ============================================================================
#    Autor Legal y Titular de Derechos: JAVIER ILLAN GONZALEZ
#    Organización: ORANGE CREW
#    Contacto: ILLANJAVIER9@GMAIL.COM
#
#    ADVERTENCIA LEGAL (MÉXICO Y GLOBAL):
#    Este código fuente y su arquitectura son propiedad intelectual exclusiva de
#    JAVIER ILLAN GONZALEZ. Queda estrictamente prohibida su reproducción,
#    distribución, modificación, ingeniería inversa, copia o uso comercial sin la
#    autorización expresa y por escrito del autor. Obra protegida conforme a la
#    Ley Federal del Derecho de Autor y tratados internacionales aplicables.
#    ============================================================================
"""
Capa de acceso a datos de Orange Poliza Engine sobre PostgreSQL.

Antes este módulo usaba sqlite3 con un archivo local (orange_poliza.db).
Eso es lo que causaba "usuario o contraseña incorrectos" al correr la
app en varias computadoras: cada máquina creaba su propio archivo
.db vacío. Ahora todas las instancias de la app se conectan al MISMO
servidor PostgreSQL (definido por variables de entorno), así que
comparten la misma base sin importar desde qué computadora se abra
el navegador.

Para no tener que reescribir cada consulta de los repositorios
(webapp/*.py, backend/app/core/rules_repository.py) al migrar de
sqlite3 a psycopg2, este módulo expone una capa de compatibilidad:

  - con.execute("... WHERE id = ?", (valor,))   -> placeholders '?' igual que antes
  - cur.lastrowid                                -> igual que antes, vía RETURNING id
  - fila["columna"] y fila[0]                    -> igual que sqlite3.Row
  - con.executescript(sql)                       -> para el schema.sql con varias sentencias

Así, el resto del proyecto no cambia; solo esta capa.
"""

import os
import re

import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SCHEMA_PATH = os.path.join(BASE_DIR, "..", "database", "schema.sql")

# Tablas cuya llave primaria no se llama "id" (o no tienen una sola
# columna autoincremental): no se les debe agregar "RETURNING id".
_TABLAS_SIN_ID = {"usuario_empresa"}

_INSERT_RE = re.compile(r"^\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)


class ErrorConexionBD(Exception):
    """Se lanza cuando falta configuración de conexión a PostgreSQL o el
    servidor no responde, con un mensaje entendible para el usuario final."""
    pass


def _config_desde_entorno() -> dict:
    requeridas = ("ORANGE_DB_HOST", "ORANGE_DB_NAME", "ORANGE_DB_USER", "ORANGE_DB_PASSWORD")
    faltantes = [v for v in requeridas if not os.environ.get(v)]
    if faltantes:
        raise ErrorConexionBD(
            "Falta configurar la conexión a PostgreSQL (variables de entorno: "
            + ", ".join(faltantes) + "). Copia webapp/.env.example a webapp/.env "
            "con los datos de tu servidor, o corre instalar_postgres.bat en la "
            "computadora que actuará como servidor."
        )
    return {
        "host": os.environ["ORANGE_DB_HOST"],
        "port": os.environ.get("ORANGE_DB_PORT", "5432"),
        "dbname": os.environ["ORANGE_DB_NAME"],
        "user": os.environ["ORANGE_DB_USER"],
        "password": os.environ["ORANGE_DB_PASSWORD"],
        "connect_timeout": 5,
    }


class Row:
    """Emula sqlite3.Row: accesible por nombre (fila["columna"]) o por
    posición (fila[0]), e iterable/convertible con dict(fila). Se usa
    en vez del RealDictCursor de psycopg2 porque varias consultas del
    proyecto (ej. SELECT COUNT(*)) leen el resultado por posición."""

    __slots__ = ("_valores", "_columnas")

    def __init__(self, columnas, valores):
        self._columnas = columnas
        self._valores = dict(zip(columnas, valores))

    def __getitem__(self, clave):
        if isinstance(clave, int):
            return self._valores[self._columnas[clave]]
        return self._valores[clave]

    def get(self, clave, default=None):
        return self._valores.get(clave, default)

    def keys(self):
        return list(self._columnas)

    def __contains__(self, clave):
        return clave in self._valores

    def __iter__(self):
        return iter(self._columnas)

    def __eq__(self, otro):
        return isinstance(otro, Row) and self._valores == otro._valores

    def __repr__(self):
        return f"Row({self._valores!r})"


def _traducir_placeholders(sql: str) -> str:
    """Los repositorios están escritos con '?' al estilo sqlite3;
    psycopg2 espera '%s'. Ninguna consulta del proyecto trae literales
    con '?', así que el reemplazo directo es seguro."""
    return sql.replace("?", "%s")


class Cursor:
    def __init__(self, cursor_real):
        self._cursor = cursor_real
        self.lastrowid = None

    def execute(self, sql, params=()):
        sql_pg = _traducir_placeholders(sql)
        agregar_returning = False
        if "RETURNING" not in sql_pg.upper():
            m = _INSERT_RE.match(sql_pg)
            if m and m.group(1).lower() not in _TABLAS_SIN_ID:
                sql_pg = sql_pg.rstrip().rstrip(";") + " RETURNING id"
                agregar_returning = True
        self._cursor.execute(sql_pg, params)
        if agregar_returning:
            fila = self._cursor.fetchone()
            self.lastrowid = fila[0] if fila else None
        return self

    def executemany(self, sql, secuencia_params):
        self._cursor.executemany(_traducir_placeholders(sql), secuencia_params)
        return self

    def _empaquetar(self, fila):
        if fila is None:
            return None
        columnas = [d[0] for d in self._cursor.description]
        return Row(columnas, fila)

    def fetchone(self):
        return self._empaquetar(self._cursor.fetchone())

    def fetchall(self):
        return [self._empaquetar(f) for f in self._cursor.fetchall()]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class Connection:
    def __init__(self, con_real):
        self._con = con_real
        self.row_factory = None  # solo por compatibilidad; Row siempre está activo

    def cursor(self) -> Cursor:
        return Cursor(self._con.cursor())

    def execute(self, sql, params=()) -> Cursor:
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executescript(self, sql: str) -> None:
        """Ejecuta un bloque con varias sentencias separadas por ';'
        (usado para correr database/schema.sql completo)."""
        cur = self._con.cursor()
        try:
            cur.execute(sql)
        finally:
            cur.close()

    def commit(self):
        self._con.commit()

    def rollback(self):
        self._con.rollback()

    def close(self):
        if _pool is not None:
            _pool.putconn(self._con)
        else:
            self._con.close()


def _texto_legible(excepcion: Exception) -> str:
    """En Windows, cuando falla la conexión (ej. el servicio de
    PostgreSQL apagado, o el firewall bloqueando el puerto), el
    mensaje de error del sistema operativo viene en el idioma y la
    codificación de Windows (cp1252 en Windows en español), pero
    psycopg2 intenta decodificarlo como UTF-8 y lanza un
    UnicodeDecodeError que tapa el mensaje real. Aquí se recupera ese
    mensaje probando varias codificaciones en vez de dejar pasar el
    traceback críptico."""
    crudo = getattr(excepcion, "object", None)
    if isinstance(crudo, (bytes, bytearray)):
        for codificacion in ("utf-8", "cp1252", "latin-1"):
            try:
                return crudo.decode(codificacion)
            except UnicodeDecodeError:
                continue
        return repr(bytes(crudo))
    return str(excepcion) or repr(excepcion)


from psycopg2.pool import ThreadedConnectionPool

_pool = None

def get_connection() -> Connection:
    global _pool
    if _pool is None:
        try:
            _pool = ThreadedConnectionPool(1, 20, **_config_desde_entorno())
        except (psycopg2.OperationalError, UnicodeDecodeError, UnicodeError) as e:
            raise ErrorConexionBD(
                "No se pudo conectar al servidor PostgreSQL. Verifica que el "
                "servicio de PostgreSQL esté iniciado (en la computadora servidor, "
                'abre "Servicios" de Windows y busca "postgresql-x64-..."), que el '
                "puerto 5432 esté abierto en el Firewall, y que webapp/.env tenga "
                f"los datos correctos. Detalle: {_texto_legible(e)}"
            ) from e
    
    con = _pool.getconn()
    return Connection(con)


def inicializar_db():
    """Crea las tablas que falten (CREATE TABLE IF NOT EXISTS) y agrega
    columnas nuevas a instalaciones existentes. Segura de llamar en
    cada arranque del servidor."""
    con = get_connection()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        con.executescript(f.read())
    con.commit()
    _aplicar_migraciones(con)
    con.commit()
    con.close()


def _aplicar_migraciones(con: Connection):
    """Columnas agregadas después de la versión inicial del esquema.
    ADD COLUMN IF NOT EXISTS es idempotente en PostgreSQL, así que no
    hace falta revisar antes si la columna ya existe."""
    migraciones = [
        ("empresas", "tasa_retencion_iva", "REAL NOT NULL DEFAULT 0.0"),
        ("empresas", "tasa_retencion_isr", "REAL NOT NULL DEFAULT 0.0"),
        ("empresas", "base_datos_contpaqi", "TEXT"),
        ("documentos_importados", "ruta_archivo", "TEXT"),

        ("documentos_importados", "nombre_hoja", "TEXT"),
        ("movimientos", "fila_original", "INTEGER"),
        ("movimientos", "afectable_impuestos", "INTEGER"),
        ("cfdi_impuestos", "es_retencion", "INTEGER NOT NULL DEFAULT 0"),
        ("cfdi_impuestos", "tipo_impuesto", "TEXT NOT NULL DEFAULT 'IVA'"),
        ("empresas", "sql_servidor", "TEXT"),
        ("empresas", "sql_usuario", "TEXT"),
        ("empresas", "sql_password", "TEXT"),
        ("empresas", "sql_base_datos", "TEXT"),
        ("polizas", "concepto", "TEXT"),
        ("cfdis", "uuids_relacionados", "TEXT"),
    ]
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS auditoria_despacho (
        id SERIAL PRIMARY KEY,
        organizacion_id INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE CASCADE,
        usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        accion TEXT NOT NULL,
        detalle TEXT,
        fecha TEXT NOT NULL DEFAULT (NOW()::text)
    )
    """)

    for tabla, columna, tipo in migraciones:
        cur.execute(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}")
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario)"
    )


def hay_usuarios() -> bool:
    con = get_connection()
    try:
        total = con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    finally:
        con.close()
    return total > 0
