# ============================================================
# app/core/decorators.py  —  Auth decorators
# ============================================================

from functools import wraps
from flask import session, redirect, request, jsonify


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify(ok=False, error='Not authenticated'), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify(ok=False, error='Not authenticated'), 401
                return redirect('/login')
            if session.get('role') not in roles:
                if request.path.startswith('/api/'):
                    return jsonify(ok=False, error='Access denied'), 403
                return redirect('/dashboard')
            return f(*args, **kwargs)
        return wrapper
    return decorator
