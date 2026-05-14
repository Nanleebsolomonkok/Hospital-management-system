# ============================================================
# app/core/helpers.py  —  Shared utilities
# ============================================================

import hashlib
import random
import string
import math
from flask import session
from mysql.connector import Error


# ── Passwords ────────────────────────────────────────────────

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def generate_temp_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + '!@#$'
    return ''.join(random.choices(chars, k=length))


def validate_password(pw: str):
    """Return error string or None if valid."""
    if len(pw) < 8:                      return 'Password must be at least 8 characters.'
    if not any(c.isupper() for c in pw): return 'Password must contain an uppercase letter.'
    if not any(c.islower() for c in pw): return 'Password must contain a lowercase letter.'
    if not any(c.isdigit() for c in pw): return 'Password must contain a number.'
    return None


# ── Input sanitisation ───────────────────────────────────────

def sanitise_str(value, max_len: int = 255):
    """Strip and truncate a string field; return None for empty."""
    if value is None:
        return None
    value = str(value).strip()[:max_len]
    return value if value else None


def require_fields(data: dict, fields: tuple):
    """Return error string if any required field is missing, else None."""
    
    for f in fields:
        if not data.get(f):
            label = f.replace('_', ' ').capitalize()
            return f'{label} is required.'
    return None


# ── Pagination ───────────────────────────────────────────────

def paginate(query_result: list, page: int, per_page: int = 20) -> dict:
    """Slice a list and return pagination metadata."""
    total       = len(query_result)
    total_pages = max(1, math.ceil(total / per_page))
    page        = max(1, min(page, total_pages))
    start       = (page - 1) * per_page
    items       = query_result[start : start + per_page]
    return {
        'items':       items,
        'page':        page,
        'per_page':    per_page,
        'total':       total,
        'total_pages': total_pages,
        'has_prev':    page > 1,
        'has_next':    page < total_pages,
    }


# ── Audit logging ────────────────────────────────────────────

def log_audit(conn, table: str, action: str, new_values=None, record_id=None):
    try:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO AuditLog (table_name, action, record_id, new_values, user_name) '
            'VALUES (%s,%s,%s,%s,%s)',
            (table, action, record_id,
             str(new_values) if new_values else None,
             session.get('username', 'SYSTEM'))
        )
        cur.close()
    except Exception:
        pass  # audit failures should never break the main flow
