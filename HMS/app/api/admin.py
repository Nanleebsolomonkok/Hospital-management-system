from flask import Blueprint, request, session, jsonify
from app.core.db import DbCursor
from app.core.helpers import hash_password, generate_temp_password, paginate
from app.core.decorators import role_required

bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@bp.route('/users')
@role_required('ADMIN')
def api_admin_users():
    try:
        with DbCursor() as (cur, conn):
            # Users_STU001: role stored directly as column, no Roles table join
            cur.execute(
                'SELECT user_id, username, full_name, email, '
                'is_active, must_change_password, role '
                'FROM Users_STU001 ORDER BY user_id'
            )
            users = cur.fetchall()
        return jsonify(ok=True, users=users)
    except Exception as e:
        return jsonify(ok=False, error=f'Users error: {str(e)}')

@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@role_required('ADMIN')
def api_admin_reset_password(user_id):
    temp_pw = generate_temp_password()
    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'UPDATE Users_STU001 SET password_hash=%s, must_change_password=1 '
                'WHERE user_id=%s',
                (hash_password(temp_pw), user_id)
            )
        return jsonify(ok=True,
                       message=f'Password reset. Temporary password: {temp_pw}',
                       temp_password=temp_pw)
    except Exception as e:
        return jsonify(ok=False, error=f'Reset error: {str(e)}')

@bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@role_required('ADMIN')
def api_toggle_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify(ok=False, error='You cannot deactivate your own account.')
    try:
        with DbCursor() as (cur, conn):
            cur.execute('SELECT is_active FROM Users_STU001 WHERE user_id=%s', (user_id,))
            row = cur.fetchone()
            if not row:
                return jsonify(ok=False, error='User not found.')
            new_state = 0 if row['is_active'] else 1
            cur.execute(
                'UPDATE Users_STU001 SET is_active=%s WHERE user_id=%s',
                (new_state, user_id)
            )
        label = 'activated' if new_state else 'deactivated'
        return jsonify(ok=True, is_active=bool(new_state),
                       message=f'User {label} successfully.')
    except Exception as e:
        return jsonify(ok=False, error=f'Toggle error: {str(e)}')

@bp.route('/audit-log')
@role_required('ADMIN')
def api_audit_log():
    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(50, int(request.args.get('per_page', 25)))
    try:
        with DbCursor() as (cur, conn):
            # AuditLog_STU001 columns: log_id, table_name, action, record_id,
            # old_values, new_values, user_name, action_timestamp, ip_address
            cur.execute(
                'SELECT log_id, table_name, action, record_id, '
                'new_values, user_name, action_timestamp '
                'FROM AuditLog_STU001 '
                'ORDER BY action_timestamp DESC LIMIT 500'
            )
            logs = cur.fetchall()
            for log in logs:
                log['action_timestamp'] = str(log['action_timestamp'])
        result = paginate(logs, page, per_page)
        return jsonify(ok=True, logs=result['items'], pagination={
            'page': result['page'], 'per_page': result['per_page'],
            'total': result['total'], 'total_pages': result['total_pages'],
            'has_prev': result['has_prev'], 'has_next': result['has_next'],
        })
    except Exception as e:
        return jsonify(ok=False, error=f'Audit log error: {str(e)}')
