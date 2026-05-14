from flask import Blueprint, request, session, jsonify
from app.core.db import DbCursor
from app.core.helpers import paginate, sanitise_str, require_fields
from app.core.decorators import login_required, role_required

bp = Blueprint('appointments', __name__, url_prefix='/api')

_BASE = (
    'SELECT a.appointment_id, a.appointment_date, a.appointment_time, '
    'a.reason, a.status, a.patient_id, '
    'p.first_name AS patient_first, p.last_name AS patient_last, '
    'd.last_name AS doctor_last '
    'FROM Appointments_STU001 a '
    'JOIN Patients_STU001 p ON a.patient_id = p.patient_id '
    'JOIN Doctors_STU001  d ON a.doctor_id  = d.doctor_id '
)


def _serialise(appts):
    for a in appts:
        a['appointment_date'] = str(a['appointment_date'])
        a['appointment_time'] = str(a['appointment_time'])
    return appts


@bp.route('/appointments')
@login_required
def api_appointments():
    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(50, int(request.args.get('per_page', 20)))
    role     = session.get('role')

    try:
        with DbCursor() as (cur, conn):
            if role == 'DOCTOR':
                full  = session.get('full_name', '').replace('Dr. ', '').strip()
                parts = full.split(' ', 1)
                first, last = parts[0], (parts[1] if len(parts) > 1 else '')
                cur.execute(
                    _BASE +
                    "WHERE a.appointment_date >= CURDATE() AND a.status = 'Scheduled' "
                    'AND d.first_name = %s AND d.last_name = %s '
                    'ORDER BY a.appointment_date, a.appointment_time',
                    (first, last)
                )
            elif role == 'RECEPTIONIST':
                cur.execute(
                    _BASE + 'WHERE a.appointment_date = CURDATE() '
                    'ORDER BY a.appointment_time'
                )
            else:
                cur.execute(
                    _BASE +
                    'ORDER BY a.appointment_date DESC, a.appointment_time DESC '
                    'LIMIT 500'
                )
            all_appts = _serialise(cur.fetchall())

        result = paginate(all_appts, page, per_page)
        return jsonify(ok=True, appointments=result['items'], pagination={
            'page': result['page'], 'per_page': result['per_page'],
            'total': result['total'], 'total_pages': result['total_pages'],
            'has_prev': result['has_prev'], 'has_next': result['has_next'],
        })
    except Exception as e:
        return jsonify(ok=False, error=f'Appointments error: {str(e)}')


@bp.route('/appointments/schedule', methods=['POST'])
@role_required('ADMIN', 'RECEPTIONIST')
def api_schedule_appointment():
    data = request.get_json() or {}
    err = require_fields(data, ('patient_id', 'doctor_id', 'appointment_date',
                                'appointment_time', 'reason'))
    if err:
        return jsonify(ok=False, error=err)

    try:
        with DbCursor() as (cur, conn):
            # ScheduleAppointment_STU001 has 5 IN + 2 OUT (appointment_id, status_message)
            # OUT params are at index 5 and 6
            cur.callproc('ScheduleAppointment_STU001', [
                int(data['patient_id']),
                int(data['doctor_id']),
                sanitise_str(data['appointment_date'], 20),
                sanitise_str(data['appointment_time'], 10),
                sanitise_str(data['reason'], 500),
                0, ''
            ])

            # Read OUT params via session variables
            cur.execute(
                'SELECT @_ScheduleAppointment_STU001_5 AS new_id, '
                '       @_ScheduleAppointment_STU001_6 AS msg'
            )
            row    = cur.fetchone()
            new_id = row['new_id'] if row else None
            msg    = row['msg']    if row else ''

            if msg and 'Error' in str(msg):
                conn.rollback()
                return jsonify(ok=False, error=msg)

        return jsonify(ok=True,
                       message='Appointment scheduled successfully.',
                       appointment_id=new_id)
    except Exception as e:
        return jsonify(ok=False, error=f'Schedule error: {str(e)}')
