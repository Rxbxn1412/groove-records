import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def conectar():
    """Abre una conexión con la base de datos PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'tienda'),
        user=os.getenv('DB_USER', 'tienda_user'),
        password=os.getenv('DB_PASSWORD', ''),
    )


def consultar(sql, params=None, uno=False):
    """Ejecuta un SELECT y devuelve una lista de diccionarios (o uno solo)."""
    conn = conectar()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone() if uno else cur.fetchall()
    finally:
        conn.close()


def ejecutar(sql, params=None):
    """Ejecuta un INSERT, UPDATE o DELETE y confirma la transacción."""
    conn = conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def transaccion():
    """Agrupa varias sentencias en una sola transacción.

    Si dentro del bloque `with` salta una excepción se hace ROLLBACK y no se
    guarda nada; si todo va bien se hace COMMIT al salir.
    """
    conn = conectar()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
