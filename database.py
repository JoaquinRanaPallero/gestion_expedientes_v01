"""Capa de base de datos SQLite para gestion de expedientes."""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from models import Expediente, Parte, PasoProcesal, Vencimiento, Honorario, Gasto

DB_NAME = "expedientes.db"


def _get_db_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)


@contextmanager
def _connect():
    """Context manager que garantiza cierre de conexion y rollback en caso de error."""
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS expedientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL UNIQUE,
                caratula TEXT NOT NULL,
                fuero_juzgado TEXT DEFAULT '',
                fecha_inicio TEXT DEFAULT '',
                tipo_proceso TEXT DEFAULT '',
                estado TEXT DEFAULT 'activo' CHECK(estado IN ('activo','archivado','cerrado')),
                observaciones TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS partes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expediente_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                tipo TEXT DEFAULT '',
                dni_cuit TEXT DEFAULT '',
                domicilio TEXT DEFAULT '',
                telefono TEXT DEFAULT '',
                email TEXT DEFAULT '',
                FOREIGN KEY (expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS pasos_procesales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expediente_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                observaciones TEXT DEFAULT '',
                FOREIGN KEY (expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS vencimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expediente_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente','cumplido','vencido')),
                FOREIGN KEY (expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS honorarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expediente_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                monto REAL NOT NULL,
                moneda TEXT DEFAULT 'ARS' CHECK(moneda IN ('ARS','USD')),
                concepto TEXT DEFAULT '',
                forma_pago TEXT DEFAULT '',
                FOREIGN KEY (expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expediente_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                monto REAL NOT NULL,
                moneda TEXT DEFAULT 'ARS' CHECK(moneda IN ('ARS','USD')),
                descripcion TEXT DEFAULT '',
                FOREIGN KEY (expediente_id) REFERENCES expedientes(id) ON DELETE CASCADE
            );
        """)


# --- Expedientes ---

def crear_expediente(exp: Expediente) -> int:
    with _connect() as conn:
        c = conn.execute(
            "INSERT INTO expedientes (numero, caratula, fuero_juzgado, fecha_inicio, tipo_proceso, estado, observaciones) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (exp.numero, exp.caratula, exp.fuero_juzgado, exp.fecha_inicio,
             exp.tipo_proceso, exp.estado, exp.observaciones),
        )
        return c.lastrowid


def actualizar_expediente(exp: Expediente) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE expedientes SET numero=?, caratula=?, fuero_juzgado=?, fecha_inicio=?, "
            "tipo_proceso=?, estado=?, observaciones=? WHERE id=?",
            (exp.numero, exp.caratula, exp.fuero_juzgado, exp.fecha_inicio,
             exp.tipo_proceso, exp.estado, exp.observaciones, exp.id),
        )


def eliminar_expediente(exp_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM expedientes WHERE id=?", (exp_id,))


def obtener_expediente(exp_id: int) -> Optional[Expediente]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM expedientes WHERE id=?", (exp_id,)).fetchone()
        if row:
            return Expediente(**dict(row))
        return None


def listar_expedientes(filtro_numero: str = "", filtro_caratula: str = "",
                       filtro_estado: str = "", filtro_juzgado: str = "") -> list[Expediente]:
    with _connect() as conn:
        query = "SELECT * FROM expedientes WHERE 1=1"
        params: list = []
        if filtro_numero:
            query += " AND numero LIKE ?"
            params.append(f"%{filtro_numero}%")
        if filtro_caratula:
            query += " AND caratula LIKE ?"
            params.append(f"%{filtro_caratula}%")
        if filtro_estado:
            query += " AND estado = ?"
            params.append(filtro_estado)
        if filtro_juzgado:
            query += " AND fuero_juzgado LIKE ?"
            params.append(f"%{filtro_juzgado}%")
        query += " ORDER BY fecha_inicio DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
        return [Expediente(**dict(r)) for r in rows]


def obtener_ultimo_movimiento(expediente_id: int) -> Optional[str]:
    """Retorna la fecha del ultimo paso procesal del expediente, o None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT MAX(fecha) as ultima FROM pasos_procesales WHERE expediente_id=?",
            (expediente_id,),
        ).fetchone()
        if row and row["ultima"]:
            return row["ultima"]
        return None


def obtener_ultimos_movimientos() -> dict[int, str]:
    """Retorna un dict {expediente_id: fecha_ultimo_movimiento} para todos los expedientes."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT expediente_id, MAX(fecha) as ultima FROM pasos_procesales GROUP BY expediente_id"
        ).fetchall()
        return {r["expediente_id"]: r["ultima"] for r in rows}


def numero_existe(numero: str, excluir_id: Optional[int] = None) -> bool:
    with _connect() as conn:
        if excluir_id:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM expedientes WHERE numero=? AND id!=?",
                (numero, excluir_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM expedientes WHERE numero=?", (numero,)
            ).fetchone()
        return row["cnt"] > 0


# --- Partes ---

def crear_parte(parte: Parte) -> int:
    with _connect() as conn:
        c = conn.execute(
            "INSERT INTO partes (expediente_id, nombre, tipo, dni_cuit, domicilio, telefono, email) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (parte.expediente_id, parte.nombre, parte.tipo, parte.dni_cuit,
             parte.domicilio, parte.telefono, parte.email),
        )
        return c.lastrowid


def actualizar_parte(parte: Parte) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE partes SET nombre=?, tipo=?, dni_cuit=?, domicilio=?, telefono=?, email=? WHERE id=?",
            (parte.nombre, parte.tipo, parte.dni_cuit, parte.domicilio,
             parte.telefono, parte.email, parte.id),
        )


def eliminar_parte(parte_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM partes WHERE id=?", (parte_id,))


def listar_partes(expediente_id: int) -> list[Parte]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM partes WHERE expediente_id=? ORDER BY tipo, nombre", (expediente_id,)
        ).fetchall()
        return [Parte(**dict(r)) for r in rows]


# --- Pasos Procesales ---

def crear_paso(paso: PasoProcesal) -> int:
    with _connect() as conn:
        c = conn.execute(
            "INSERT INTO pasos_procesales (expediente_id, fecha, descripcion, observaciones) "
            "VALUES (?, ?, ?, ?)",
            (paso.expediente_id, paso.fecha, paso.descripcion, paso.observaciones),
        )
        return c.lastrowid


def actualizar_paso(paso: PasoProcesal) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE pasos_procesales SET fecha=?, descripcion=?, observaciones=? WHERE id=?",
            (paso.fecha, paso.descripcion, paso.observaciones, paso.id),
        )


def eliminar_paso(paso_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM pasos_procesales WHERE id=?", (paso_id,))


def listar_pasos(expediente_id: int) -> list[PasoProcesal]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM pasos_procesales WHERE expediente_id=? ORDER BY fecha DESC, id DESC",
            (expediente_id,),
        ).fetchall()
        return [PasoProcesal(**dict(r)) for r in rows]


# --- Vencimientos ---

def crear_vencimiento(venc: Vencimiento) -> int:
    with _connect() as conn:
        c = conn.execute(
            "INSERT INTO vencimientos (expediente_id, fecha, descripcion, estado) VALUES (?, ?, ?, ?)",
            (venc.expediente_id, venc.fecha, venc.descripcion, venc.estado),
        )
        return c.lastrowid


def actualizar_vencimiento(venc: Vencimiento) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE vencimientos SET fecha=?, descripcion=?, estado=? WHERE id=?",
            (venc.fecha, venc.descripcion, venc.estado, venc.id),
        )


def eliminar_vencimiento(venc_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM vencimientos WHERE id=?", (venc_id,))


def listar_vencimientos(expediente_id: int) -> list[Vencimiento]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM vencimientos WHERE expediente_id=? ORDER BY fecha ASC",
            (expediente_id,),
        ).fetchall()
        return [Vencimiento(**dict(r)) for r in rows]


def listar_vencimientos_globales(filtro_estado: str = "") -> list[dict]:
    hoy = datetime.now().date().isoformat()
    with _connect() as conn:
        query = (
            "SELECT v.*, e.numero as expediente_numero FROM vencimientos v "
            "JOIN expedientes e ON v.expediente_id = e.id "
            "WHERE e.estado = 'activo'"
        )
        params: list = []
        if filtro_estado == "vencido":
            query += " AND (v.estado = 'vencido' OR (v.estado = 'pendiente' AND v.fecha < ?))"
            params.append(hoy)
        elif filtro_estado == "pendiente":
            query += " AND v.estado = 'pendiente' AND v.fecha >= ?"
            params.append(hoy)
        elif filtro_estado:
            query += " AND v.estado = ?"
            params.append(filtro_estado)
        query += " ORDER BY v.fecha ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --- Honorarios ---

def crear_honorario(hon: Honorario) -> int:
    with _connect() as conn:
        c = conn.execute(
            "INSERT INTO honorarios (expediente_id, fecha, monto, moneda, concepto, forma_pago) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (hon.expediente_id, hon.fecha, hon.monto, hon.moneda, hon.concepto, hon.forma_pago),
        )
        return c.lastrowid


def eliminar_honorario(hon_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM honorarios WHERE id=?", (hon_id,))


def listar_honorarios(expediente_id: int) -> list[Honorario]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM honorarios WHERE expediente_id=? ORDER BY fecha DESC",
            (expediente_id,),
        ).fetchall()
        return [Honorario(**dict(r)) for r in rows]


def totales_honorarios(expediente_id: int) -> dict[str, float]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT moneda, SUM(monto) as total FROM honorarios WHERE expediente_id=? GROUP BY moneda",
            (expediente_id,),
        ).fetchall()
        return {r["moneda"]: r["total"] for r in rows}


# --- Gastos ---

def crear_gasto(gasto: Gasto) -> int:
    with _connect() as conn:
        c = conn.execute(
            "INSERT INTO gastos (expediente_id, fecha, monto, moneda, descripcion) "
            "VALUES (?, ?, ?, ?, ?)",
            (gasto.expediente_id, gasto.fecha, gasto.monto, gasto.moneda, gasto.descripcion),
        )
        return c.lastrowid


def eliminar_gasto(gasto_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM gastos WHERE id=?", (gasto_id,))


def listar_gastos(expediente_id: int) -> list[Gasto]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM gastos WHERE expediente_id=? ORDER BY fecha DESC",
            (expediente_id,),
        ).fetchall()
        return [Gasto(**dict(r)) for r in rows]


def totales_gastos(expediente_id: int) -> dict[str, float]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT moneda, SUM(monto) as total FROM gastos WHERE expediente_id=? GROUP BY moneda",
            (expediente_id,),
        ).fetchall()
        return {r["moneda"]: r["total"] for r in rows}
