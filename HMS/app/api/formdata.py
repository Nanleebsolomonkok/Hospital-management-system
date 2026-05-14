from flask import Blueprint, jsonify
from app.core.db import DbCursor
from app.core.decorators import login_required, role_required

bp = Blueprint('formdata', __name__, url_prefix='/api/form-data')

@bp.route('/appointments')
@login_required
def api_form_appointments():
    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'SELECT patient_id, first_name, last_name '
                'FROM Patients_STU001 ORDER BY last_name'
            )
            patients = cur.fetchall()
            # Doctors_STU001 status ENUM: 'Active', 'On Leave', 'Terminated'
            cur.execute(
                "SELECT doctor_id, first_name, last_name, specialization "
                "FROM Doctors_STU001 WHERE status = 'Active' ORDER BY last_name"
            )
            doctors = cur.fetchall()
        return jsonify(ok=True, patients=patients, doctors=doctors)
    except Exception as e:
        return jsonify(ok=False, error=f'Form data error: {str(e)}')

@bp.route('/medical-records')
@role_required('ADMIN', 'DOCTOR')
def api_form_medical():
    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'SELECT patient_id, first_name, last_name '
                'FROM Patients_STU001 ORDER BY last_name'
            )
            patients = cur.fetchall()
            cur.execute(
                "SELECT doctor_id, first_name, last_name, specialization "
                "FROM Doctors_STU001 WHERE status = 'Active' ORDER BY last_name"
            )
            doctors = cur.fetchall()
        return jsonify(ok=True, patients=patients, doctors=doctors)
    except Exception as e:
        return jsonify(ok=False, error=f'Form data error: {str(e)}')
