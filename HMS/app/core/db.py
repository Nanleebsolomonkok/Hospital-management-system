# ============================================================
# app/core/db.py  —  Database helpers
# ============================================================

from mysql.connector import connect, Error, pooling
from flask import current_app
import os

_pool = None

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'HospitalManagement_STU001'),
    'port':     int(os.environ.get('DB_PORT', 3306)),
}


def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name='medicore',
            pool_size=5,
            pool_reset_session=True,
            **DB_CONFIG
        )
    return _pool


def get_db():
    """Return a pooled connection. Caller must close() it."""
    try:
        return get_pool().get_connection()
    except Error as exc:
        current_app.logger.error('DB pool error: %s', exc)
        # Fall back to direct connection
        try:
            return connect(**DB_CONFIG)
        except Error as exc2:
            current_app.logger.error('DB direct connect error: %s', exc2)
            return None


class DbCursor:
    """Context manager: auto-commits on success, rolls back on exception, closes connection."""

    def __init__(self, dictionary=True, auto_commit=True):
        self.dictionary  = dictionary
        self.auto_commit = auto_commit
        self.conn = None
        self.cur  = None

    def __enter__(self):
        self.conn = get_db()
        if self.conn is None:
            raise RuntimeError('Database unavailable')
        self.cur = self.conn.cursor(dictionary=self.dictionary)
        return self.cur, self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cur:
            self.cur.close()
        if self.conn:
            if exc_type is None and self.auto_commit:
                self.conn.commit()
            elif exc_type is not None:
                self.conn.rollback()
            self.conn.close()
        return False  # don't suppress exceptions
