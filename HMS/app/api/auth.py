from flask import Blueprint, request, session, jsonify
from mysql.connector import Error
from app import limiter
from app.core.db import DbCursor
from app.core.helpers import hash_password, validate_password, sanitise_str
from app.core.decorators import login_required

bp = Blueprint('auth', __name__, url_prefix='/api')


def _audit(conn, action, extra=None):
    try:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO AuditLog_STU001 '
            '(table_name, action, new_values, user_name) VALUES (%s,%s,%s,%s)',
            ('Users_STU001', action, str(extra or ''), session.get('username', 'SYSTEM'))
        )
        cur.close()
    except Exception:
        pass


@bp.route('/login', methods=['POST'])
@limiter.limit('20 per minute')
def api_login():
    data     = request.get_json() or {}
    username = sanitise_str(data.get('username'), 80) or ''
    password = data.get('password') or ''

    if not username or not password:
        return jsonify(ok=False, error='Username and password are required.')

    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'SELECT user_id, username, full_name, password_hash, '
                'must_change_password, is_active, role '
                'FROM Users_STU001 WHERE username = %s',
                (username,)
            )
            user = cur.fetchone()

            if not user or user['password_hash'] != hash_password(password):
                return jsonify(ok=False, error='Invalid username or password.')
            if not user['is_active']:
                return jsonify(ok=False, error='Account is inactive. Contact your administrator.')

            session.clear()
            session.permanent = True
            session['user_id']   = user['user_id']
            session['username']  = user['username']
            session['full_name'] = user['full_name']
            session['role']      = user['role']

            _audit(conn, 'LOGIN', {'username': username})

        redirect_url = '/change-password' if user['must_change_password'] else '/dashboard'
        return jsonify(ok=True, redirect=redirect_url)

    except Exception as e:
        return jsonify(ok=False, error=f'Login error: {str(e)}')


@bp.route('/logout')
@login_required
def api_logout():
    try:
        with DbCursor() as (cur, conn):
            _audit(conn, 'LOGOUT', {'username': session.get('username')})
    except Exception:
        pass
    session.clear()
    return jsonify(ok=True)


@bp.route('/session')
def api_session():
    if 'user_id' not in session:
        return jsonify(ok=False, error='Not authenticated'), 401
    return jsonify(ok=True, user={
        'user_id':   session['user_id'],
        'username':  session['username'],
        'full_name': session['full_name'],
        'role':      session['role'],
    })


@bp.route('/change-password', methods=['POST'])
@login_required
@limiter.limit('5 per minute')
def api_change_password():
    data    = request.get_json() or {}
    current = data.get('current_password', '')
    new_pw  = data.get('new_password', '')
    confirm = data.get('confirm_password', '')

    if not current or not new_pw or not confirm:
        return jsonify(ok=False, error='All fields are required.')
    if new_pw != confirm:
        return jsonify(ok=False, error='New passwords do not match.')
    err = validate_password(new_pw)
    if err:
        return jsonify(ok=False, error=err)

    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'SELECT password_hash FROM Users_STU001 WHERE user_id=%s',
                (session['user_id'],)
            )
            user = cur.fetchone()
            if not user or user['password_hash'] != hash_password(current):
                return jsonify(ok=False, error='Current password is incorrect.')
            cur.execute(
                'UPDATE Users_STU001 SET password_hash=%s, must_change_password=0 '
                'WHERE user_id=%s',
                (hash_password(new_pw), session['user_id'])
            )
        return jsonify(ok=True, message='Password updated successfully.')
    except Exception as e:
        return jsonify(ok=False, error=f'Error: {str(e)}')
