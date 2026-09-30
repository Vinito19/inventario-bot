import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from security import encrypt_field, decrypt_field, hash_password

DB_NAME = "inventario.db"


def _ahora():
    """Fecha y hora actual en la zona horaria configurada (Ecuador)."""
    return datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                username TEXT,
                password_hash TEXT,
                rol TEXT DEFAULT 'pendiente',
                activo INTEGER DEFAULT 0,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS repuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                cantidad INTEGER DEFAULT 0,
                precio REAL DEFAULT 0,
                file_id_1 TEXT,
                file_id_2 TEXT,
                file_id_3 TEXT,
                file_id_4 TEXT,
                file_id_5 TEXT,
                file_id_6 TEXT,
                categoria_id INTEGER,
                ubicacion TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            );

            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            );

            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL NOT NULL,
                precio_registrado REAL NOT NULL,
                subtotal REAL NOT NULL,
                usuario_id INTEGER,
                usuario_nombre TEXT,
                vendedor TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cambios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repuesto_codigo TEXT NOT NULL,
                campo TEXT NOT NULL,
                valor_anterior TEXT,
                valor_nuevo TEXT,
                usuario_id INTEGER,
                usuario_nombre TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Índices para mejorar rendimiento de búsquedas y reportes
            CREATE INDEX IF NOT EXISTS idx_repuestos_categoria ON repuestos(categoria_id);
            CREATE INDEX IF NOT EXISTS idx_repuestos_cantidad ON repuestos(cantidad);
            CREATE INDEX IF NOT EXISTS idx_repuestos_codigo ON repuestos(codigo);
            CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);
            CREATE INDEX IF NOT EXISTS idx_ventas_codigo ON ventas(codigo);
            CREATE INDEX IF NOT EXISTS idx_cambios_repuesto ON cambios(repuesto_codigo);
        """)
        conn.commit()
        _migrate_usuarios_schema(conn)
    finally:
        conn.close()


def _migrate_usuarios_schema(conn):
    """Agrega columnas nuevas a la tabla usuarios si no existen."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(usuarios)")
    cols = {row[1] for row in cursor.fetchall()}
    if "username" not in cols:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN username TEXT")
    if "password_hash" not in cols:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN password_hash TEXT")
    if "fecha_registro" not in cols:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN fecha_registro TIMESTAMP")
        cursor.execute("UPDATE usuarios SET fecha_registro = datetime('now') WHERE fecha_registro IS NULL")
    if "rol" in cols:
        cursor.execute("UPDATE usuarios SET rol='pendiente' WHERE rol='usuario' AND activo=0")
    conn.commit()


def registrar_admins(admin_ids):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for admin_id in admin_ids:
            cursor.execute("""
                INSERT INTO usuarios (user_id, nombre, rol, activo)
                VALUES (?, ?, 'admin', 1)
                ON CONFLICT(user_id) DO UPDATE SET rol='admin', activo=1
            """, (admin_id, encrypt_field(f"Admin-{admin_id}")))
        conn.commit()
    finally:
        conn.close()


def obtener_usuario(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        # Descifrar campos sensibles
        row = dict(row)
        if row.get("nombre"):
            row["nombre"] = decrypt_field(row["nombre"])
        if row.get("username"):
            row["username"] = decrypt_field(row["username"])
        return row
    finally:
        conn.close()


def registrar_usuario(user_id, nombre, username=None, password=None, rol="pendiente", activo=0):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        password_hash = hash_password(password) if password else None
        cursor.execute("""
            INSERT INTO usuarios (user_id, nombre, username, password_hash, rol, activo)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                nombre=?, username=?, password_hash=?, rol=?, activo=?
        """, (
            user_id,
            encrypt_field(nombre) if nombre else None,
            encrypt_field(username) if username else None,
            password_hash,
            rol,
            activo,
            encrypt_field(nombre) if nombre else None,
            encrypt_field(username) if username else None,
            password_hash,
            rol,
            activo,
        ))
        conn.commit()
    finally:
        conn.close()


def cambiar_estado_usuario(user_id, activo):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET activo = ? WHERE user_id = ?", (activo, user_id))
        conn.commit()
    finally:
        conn.close()


def aprobar_usuario(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET rol = 'usuario', activo = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def esta_registrado(user_id):
    usuario = obtener_usuario(user_id)
    return usuario is not None and usuario["activo"] == 1


def es_admin(user_id):
    usuario = obtener_usuario(user_id)
    return usuario is not None and usuario["rol"] == "admin" and usuario["activo"] == 1


def obtener_usuarios():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios ORDER BY fecha DESC")
        return cursor.fetchall()
    finally:
        conn.close()


def eliminar_usuario_db(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def contar_admins_activos():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM usuarios WHERE rol = 'admin' AND activo = 1")
        return cursor.fetchone()["total"]
    finally:
        conn.close()


def obtener_categorias():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categorias ORDER BY nombre")
        return cursor.fetchall()
    finally:
        conn.close()


def agregar_categoria(nombre):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (nombre,))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def eliminar_categoria(categoria_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE repuestos SET categoria_id = NULL WHERE categoria_id = ?", (categoria_id,))
        cursor.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_categoria_por_nombre(nombre):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categorias WHERE nombre COLLATE NOCASE = ?", (nombre,))
        return cursor.fetchone()
    finally:
        conn.close()


def buscar_repuestos(termino):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        termino_escapado = termino.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        busqueda = f"%{termino_escapado}%"
        cursor.execute("""
            SELECT r.*, c.nombre as categoria_nombre
            FROM repuestos r
            LEFT JOIN categorias c ON r.categoria_id = c.id
            WHERE r.codigo LIKE ? ESCAPE '\\' OR r.nombre LIKE ? ESCAPE '\\' OR c.nombre LIKE ? ESCAPE '\\'
            ORDER BY r.nombre
        """, (busqueda, busqueda, busqueda))
        return cursor.fetchall()
    finally:
        conn.close()


def obtener_repuesto(codigo):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, c.nombre as categoria_nombre
            FROM repuestos r
            LEFT JOIN categorias c ON r.categoria_id = c.id
            WHERE r.codigo = ?
        """, (codigo,))
        return cursor.fetchone()
    finally:
        conn.close()


def agregar_repuesto(codigo, nombre, descripcion, cantidad, precio, file_ids, categoria_id, ubicacion):
    if not file_ids or len(file_ids) < 4 or len(file_ids) > 6:
        raise ValueError("Se requieren entre 4 y 6 fotos")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO repuestos (codigo, nombre, descripcion, cantidad, precio,
                                   file_id_1, file_id_2, file_id_3, file_id_4,
                                   file_id_5, file_id_6,
                                   categoria_id, ubicacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, nombre, descripcion, cantidad, precio,
              file_ids[0] if len(file_ids) > 0 else None,
              file_ids[1] if len(file_ids) > 1 else None,
              file_ids[2] if len(file_ids) > 2 else None,
              file_ids[3] if len(file_ids) > 3 else None,
              file_ids[4] if len(file_ids) > 4 else None,
              file_ids[5] if len(file_ids) > 5 else None,
              categoria_id, ubicacion))
        conn.commit()
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: repuestos.codigo" in str(e):
            raise ValueError(f"Ya existe un repuesto con el código '{codigo}'")
        raise
    finally:
        conn.close()


CAMPOS_PERMITIDOS = {
    "nombre": "nombre",
    "descripcion": "descripcion",
    "cantidad": "cantidad",
    "precio": "precio",
    "file_id_1": "file_id_1",
    "file_id_2": "file_id_2",
    "file_id_3": "file_id_3",
    "file_id_4": "file_id_4",
    "file_id_5": "file_id_5",
    "file_id_6": "file_id_6",
    "categoria_id": "categoria_id",
    "ubicacion": "ubicacion",
}


def editar_repuesto(codigo, campo, valor):
    columna = CAMPOS_PERMITIDOS.get(campo)
    if columna is None:
        raise ValueError(f"Campo no permitido: {campo}")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE repuestos SET {columna} = ? WHERE codigo = ?", (valor, codigo))
        conn.commit()
    finally:
        conn.close()


def editar_repuesto_fotos(codigo, file_ids):
    if len(file_ids) < 4:
        raise ValueError(f"Se esperaban 4 file_ids, se recibieron {len(file_ids)}")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE repuestos
            SET file_id_1=?, file_id_2=?, file_id_3=?, file_id_4=?
            WHERE codigo=?
        """, (file_ids[0], file_ids[1], file_ids[2], file_ids[3], codigo))
        conn.commit()
    finally:
        conn.close()


def eliminar_repuesto(codigo):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM repuestos WHERE codigo = ?", (codigo,))
        conn.commit()
    finally:
        conn.close()


def obtener_stock_cero():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, c.nombre as categoria_nombre
            FROM repuestos r
            LEFT JOIN categorias c ON r.categoria_id = c.id
            WHERE r.cantidad = 0
            ORDER BY r.codigo
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def eliminar_stock_cero():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM repuestos WHERE cantidad = 0")
        eliminados = cursor.rowcount
        conn.commit()
        return eliminados
    finally:
        conn.close()


def obtener_resumen():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM repuestos")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COALESCE(SUM(cantidad), 0) as unidades FROM repuestos")
        unidades = cursor.fetchone()["unidades"]

        cursor.execute("SELECT COUNT(*) as cero FROM repuestos WHERE cantidad = 0")
        cero = cursor.fetchone()["cero"]

        cursor.execute("SELECT COALESCE(SUM(cantidad * precio), 0) as valor FROM repuestos")
        valor = cursor.fetchone()["valor"]

        cursor.execute("""
            SELECT c.nombre, COUNT(r.id) as total, COALESCE(SUM(r.cantidad), 0) as unidades
            FROM categorias c
            LEFT JOIN repuestos r ON r.categoria_id = c.id
            GROUP BY c.id
            ORDER BY total DESC
        """)
        por_categoria = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as total, COALESCE(SUM(cantidad), 0) as unidades FROM repuestos WHERE categoria_id IS NULL")
        sc = cursor.fetchone()
        sin_categoria = [{"nombre": "Sin categoría", "total": sc["total"], "unidades": sc["unidades"]}] if sc["total"] > 0 else []

        return {
            "total": total,
            "unidades": unidades,
            "cero": cero,
            "valor": valor,
            "por_categoria": por_categoria,
            "sin_categoria": sin_categoria,
        }
    finally:
        conn.close()


def get_config(clave):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
        row = cursor.fetchone()
        return row["valor"] if row else None
    finally:
        conn.close()


def set_config(clave, valor):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
            (clave, valor),
        )
        conn.commit()
    finally:
        conn.close()


# ---------- VENTAS ----------

def registrar_venta(codigo, cantidad, precio_unitario, precio_registrado, usuario_id, usuario_nombre, vendedor=None):
    """Descuenta stock y registra la venta de forma atómica (sin race condition)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Verificaciones básicas
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero")
        
        # UPDATE atómico con verificación de stock en la misma operación
        # Esto evita race condition (TOCTOU) entre check y update
        cursor.execute("""
            UPDATE repuestos 
            SET cantidad = cantidad - ?
            WHERE codigo = ? AND cantidad >= ?
        """, (cantidad, codigo, cantidad))
        
        if cursor.rowcount == 0:
            # Verificar si es por stock insuficiente o código inexistente
            cursor.execute("SELECT cantidad, nombre FROM repuestos WHERE codigo = ?", (codigo,))
            r = cursor.fetchone()
            if not r:
                raise ValueError("Repuesto no encontrado")
            raise ValueError(f"Stock insuficiente: disponible {r['cantidad']}, se intentaron vender {cantidad}")
        
        # Obtener nombre y nuevo stock para el registro de venta
        cursor.execute("SELECT cantidad, nombre FROM repuestos WHERE codigo = ?", (codigo,))
        r = cursor.fetchone()
        nuevo_stock = r["cantidad"]
        
        subtotal = round(cantidad * precio_unitario, 2)
        
        cursor.execute("""
            INSERT INTO ventas (codigo, nombre, cantidad, precio_unitario, precio_registrado, subtotal, usuario_id, usuario_nombre, vendedor, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, r["nombre"], cantidad, precio_unitario, precio_registrado, subtotal, usuario_id, usuario_nombre, vendedor, _ahora()))
        conn.commit()
        return {"nuevo_stock": nuevo_stock, "subtotal": subtotal, "nombre": r["nombre"]}
    except sqlite3.Error:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_ventas():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ventas ORDER BY fecha DESC, id DESC")
        return cursor.fetchall()
    finally:
        conn.close()


def obtener_resumen_ventas():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as ventas FROM ventas")
        ventas = cursor.fetchone()["ventas"]

        cursor.execute("SELECT COALESCE(SUM(cantidad), 0) as unidades FROM ventas")
        unidades = cursor.fetchone()["unidades"]

        cursor.execute("SELECT COALESCE(SUM(subtotal), 0) as total FROM ventas")
        total = cursor.fetchone()["total"]

        return {"ventas": ventas, "unidades": unidades, "total": total}
    finally:
        conn.close()


def obtener_ventas_por_fecha(fecha_inicio=None, fecha_fin=None):
    """Obtiene ventas filtradas por rango de fechas (inclusive).
    fechas en formato 'YYYY-MM-DD' o 'YYYY-MM-DD HH:MM:SS'.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if fecha_inicio and fecha_fin:
            cursor.execute("""
                SELECT * FROM ventas 
                WHERE date(fecha) BETWEEN date(?) AND date(?)
                ORDER BY fecha DESC, id DESC
            """, (fecha_inicio, fecha_fin))
        elif fecha_inicio:
            cursor.execute("""
                SELECT * FROM ventas 
                WHERE date(fecha) >= date(?)
                ORDER BY fecha DESC, id DESC
            """, (fecha_inicio,))
        elif fecha_fin:
            cursor.execute("""
                SELECT * FROM ventas 
                WHERE date(fecha) <= date(?)
                ORDER BY fecha DESC, id DESC
            """, (fecha_fin,))
        else:
            cursor.execute("SELECT * FROM ventas ORDER BY fecha DESC, id DESC")
        return cursor.fetchall()
    finally:
        conn.close()


def obtener_resumen_ventas_por_fecha(fecha_inicio=None, fecha_fin=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if fecha_inicio and fecha_fin:
            query = """
                SELECT COUNT(*) as ventas,
                       COALESCE(SUM(cantidad), 0) as unidades,
                       COALESCE(SUM(subtotal), 0) as total
                FROM ventas
                WHERE date(fecha) BETWEEN date(?) AND date(?)
            """
            cursor.execute(query, (fecha_inicio, fecha_fin))
        elif fecha_inicio:
            query = """
                SELECT COUNT(*) as ventas,
                       COALESCE(SUM(cantidad), 0) as unidades,
                       COALESCE(SUM(subtotal), 0) as total
                FROM ventas
                WHERE date(fecha) >= date(?)
            """
            cursor.execute(query, (fecha_inicio,))
        elif fecha_fin:
            query = """
                SELECT COUNT(*) as ventas,
                       COALESCE(SUM(cantidad), 0) as unidades,
                       COALESCE(SUM(subtotal), 0) as total
                FROM ventas
                WHERE date(fecha) <= date(?)
            """
            cursor.execute(query, (fecha_fin,))
        else:
            cursor.execute("""
                SELECT COUNT(*) as ventas,
                       COALESCE(SUM(cantidad), 0) as unidades,
                       COALESCE(SUM(subtotal), 0) as total
                FROM ventas
            """)
        row = cursor.fetchone()
        return {"ventas": row["ventas"], "unidades": row["unidades"], "total": row["total"]}
    finally:
        conn.close()


def obtener_cambios_por_fecha(fecha_inicio=None, fecha_fin=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if fecha_inicio and fecha_fin:
            cursor.execute("""
                SELECT * FROM cambios 
                WHERE date(fecha) BETWEEN date(?) AND date(?)
                ORDER BY fecha DESC, id DESC
            """, (fecha_inicio, fecha_fin))
        elif fecha_inicio:
            cursor.execute("""
                SELECT * FROM cambios 
                WHERE date(fecha) >= date(?)
                ORDER BY fecha DESC, id DESC
            """, (fecha_inicio,))
        elif fecha_fin:
            cursor.execute("""
                SELECT * FROM cambios 
                WHERE date(fecha) <= date(?)
                ORDER BY fecha DESC, id DESC
            """, (fecha_fin,))
        else:
            cursor.execute("SELECT * FROM cambios ORDER BY fecha DESC, id DESC")
        return cursor.fetchall()
    finally:
        conn.close()


# ---------- HISTORIAL DE CAMBIOS ----------

def registrar_cambio(codigo, campo, valor_anterior, valor_nuevo, usuario_id, usuario_nombre):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cambios (repuesto_codigo, campo, valor_anterior, valor_nuevo, usuario_id, usuario_nombre, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (codigo, campo, str(valor_anterior), str(valor_nuevo), usuario_id, usuario_nombre, _ahora()))
        conn.commit()
    finally:
        conn.close()


def obtener_cambios():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cambios ORDER BY fecha DESC, id DESC")
        return cursor.fetchall()
    finally:
        conn.close()
