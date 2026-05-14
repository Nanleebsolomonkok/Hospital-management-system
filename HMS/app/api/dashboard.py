from flask import Blueprint, session, jsonify
from mysql.connector import Error
from app.core.db import DbCursor
from app.core.decorators import role_required

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@bp.route('/stats')
@role_required('ADMIN')
def api_dashboard_stats():
    try:
        with DbCursor() as (cur, conn):
            cur.execute('SELECT COUNT(*) AS v FROM Patients_STU001')
            total_patients = cur.fetchone()['v']

            # Doctors_STU001 uses status ENUM('Active','On Leave','Terminated')
            cur.execute("SELECT COUNT(*) AS v FROM Doctors_STU001 WHERE status='Active'")
            active_doctors = cur.fetchone()['v']

            cur.execute(
                'SELECT COUNT(*) AS v FROM Appointments_STU001 '
                'WHERE appointment_date = CURDATE()'
            )
            today_appointments = cur.fetchone()['v']

            cur.execute(
                "SELECT COALESCE(SUM(total_amount), 0) AS v "
                "FROM Billing_STU001 WHERE payment_status = 'Paid'"
            )
            total_revenue = float(cur.fetchone()['v'])

            cur.execute(
                "SELECT COUNT(*) AS v FROM Billing_STU001 "
                "WHERE payment_status = 'Pending'"
            )
            pending_bills = cur.fetchone()['v']

        return jsonify(ok=True, stats={
            'total_patients':     total_patients,
            'active_doctors':     active_doctors,
            'today_appointments': today_appointments,
            'total_revenue':      total_revenue,
            'pending_bills':      pending_bills,
        })
    except Exception as e:
        return jsonify(ok=False, error=f'Stats error: {str(e)}')


@bp.route('/doctor')
@role_required('DOCTOR')
def api_dashboard_doctor():
    try:
        with DbCursor() as (cur, conn):
            # Doctors_STU001 has no user_id — match by full_name split from session
            full_name = session.get('full_name', '')
            # Remove "Dr." prefix if present
            clean_name = full_name.replace('Dr. ', '').replace('Dr.', '').strip()
            parts = clean_name.split(' ', 1)
            first = parts[0] if parts else ''
            last  = parts[1] if len(parts) > 1 else ''

            cur.execute(
                'SELECT doctor_id FROM Doctors_STU001 '
                'WHERE first_name = %s AND last_name = %s',
                (first, last)
            )
            doc = cur.fetchone()
            if not doc:
                # Try just last name match as fallback
                cur.execute(
                    'SELECT doctor_id FROM Doctors_STU001 WHERE last_name = %s',
                    (last,)
                )
                doc = cur.fetchone()

            if not doc:
                return jsonify(ok=True, patient_count=0, appointments=[])

            did = doc['doctor_id']

            cur.execute(
                'SELECT COUNT(DISTINCT patient_id) AS v '
                'FROM MedicalRecords_STU001 WHERE doctor_id = %s',
                (did,)
            )
            patient_count = cur.fetchone()['v']

            cur.execute(
                'SELECT a.appointment_id, a.appointment_date, a.appointment_time, '
                'a.reason, a.status, a.patient_id, '
                'p.first_name AS patient_first, p.last_name AS patient_last '
                'FROM Appointments_STU001 a '
                'JOIN Patients_STU001 p ON a.patient_id = p.patient_id '
                "WHERE a.doctor_id = %s AND a.appointment_date >= CURDATE() "
                "AND a.status = 'Scheduled' "
                'ORDER BY a.appointment_date, a.appointment_time LIMIT 20',
                (did,)
            )
            appts = cur.fetchall()
            for a in appts:
                a['appointment_date'] = str(a['appointment_date'])
                a['appointment_time'] = str(a['appointment_time'])

        return jsonify(ok=True, patient_count=patient_count, appointments=appts)
    except Exception as e:
        return jsonify(ok=False, error=f'Doctor dashboard error: {str(e)}')


@bp.route('/receptionist')
@role_required('RECEPTIONIST')
def api_dashboard_receptionist():
    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'SELECT a.appointment_id, a.appointment_time, a.status, '
                'p.first_name AS patient_first, p.last_name AS patient_last, '
                'd.last_name AS doctor_last '
                'FROM Appointments_STU001 a '
                'JOIN Patients_STU001 p ON a.patient_id = p.patient_id '
                'JOIN Doctors_STU001  d ON a.doctor_id  = d.doctor_id '
                'WHERE a.appointment_date = CURDATE() '
                'ORDER BY a.appointment_time'
            )
            appts = cur.fetchall()
            for a in appts:
                a['appointment_time'] = str(a['appointment_time'])

        return jsonify(ok=True, today_appointments=appts)
    except Exception as e:
        return jsonify(ok=False, error=f'Receptionist dashboard error: {str(e)}')


@bp.route('/billing')
@role_required('BILLING')
def api_dashboard_billing():
    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'SELECT b.bill_id, b.total_amount, '
                'p.first_name AS patient_first, p.last_name AS patient_last '
                'FROM Billing_STU001 b '
                'JOIN Patients_STU001 p ON b.patient_id = p.patient_id '
                "WHERE b.payment_status = 'Pending' "
                'ORDER BY b.bill_id DESC'
            )
            pending = cur.fetchall()
            for b in pending:
                b['total_amount'] = float(b['total_amount'])

            # Billing_STU001 has billing_date (TIMESTAMP), no payment_date column
            cur.execute(
                "SELECT COALESCE(SUM(total_amount), 0) AS v "
                "FROM Billing_STU001 "
                "WHERE payment_status = 'Paid' AND DATE(billing_date) = CURDATE()"
            )
            today_revenue = float(cur.fetchone()['v'])

        return jsonify(ok=True, pending_bills=pending, today_revenue=today_revenue)
    except Exception as e:
        return jsonify(ok=False, error=f'Billing dashboard error: {str(e)}')
