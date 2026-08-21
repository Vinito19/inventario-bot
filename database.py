import sqlite3

DB_NAME = "inventario.db"


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
                rol TEXT DEFAULT 'usuario',
                activo INTEGER DEFAULT 1,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                categoria_id INTEGER,
                ubicacion TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            );
        """)
        conn.commit()
    finally:
        conn.close()


def registrar_admins(admin_ids):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for admin_id in admin_ids:
            cursor.execute("""
                INSERT INTO usuarios (user_id, nombre, rol, activo)
                VALUES (?, ?, 'admin', 1)
                ON CONFLICT(user_id) DO UPDATE SET rol='admin', activo=1
            """, (admin_id, f"Admin-{admin_id}"))
        conn.commit()
    finally:
        conn.close()


def obtener_usuario(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE user_id = ?", (user_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def registrar_usuario(user_id, nombre, rol="usuario", activo=1):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuarios (user_id, nombre, rol, activo)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET nombre=?, rol=?, activo=?
        """, (user_id, nombre, rol, activo, nombre, rol, activo))
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
        termino_escapado = termino.replace("%", "\\%").replace("_", "\\_")
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
    if not file_ids or len(file_ids) != 4:
        raise ValueError("Se requieren exactamente 4 fotos")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO repuestos (codigo, nombre, descripcion, cantidad, precio,
                                   file_id_1, file_id_2, file_id_3, file_id_4,
                                   categoria_id, ubicacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (codigo, nombre, descripcion, cantidad, precio,
              file_ids[0], file_ids[1], file_ids[2], file_ids[3],
              categoria_id, ubicacion))
        conn.commit()
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: repuestos.codigo" in str(e):
            raise ValueError(f"Ya existe un repuesto con el código '{codigo}'")
        raise
    finally:
        conn.close()


CAMPOS_PERMITIDOS = {
    "nombre", "descripcion", "cantidad", "precio",
    "file_id_1", "file_id_2", "file_id_3", "file_id_4",
    "categoria_id", "ubicacion",
}


def editar_repuesto(codigo, campo, valor):
    if campo not in CAMPOS_PERMITIDOS:
        raise ValueError(f"Campo no permitido: {campo}")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE repuestos SET {} = ? WHERE codigo = ?".format(campo), (valor, codigo))
        conn.commit()
    finally:
        conn.close()


def editar_repuesto_fotos(codigo, file_ids):
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
