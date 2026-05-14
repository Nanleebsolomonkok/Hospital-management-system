from flask import Blueprint, request, session, jsonify
from app.core.db import DbCursor
from app.core.helpers import paginate, sanitise_str, require_fields
from app.core.decorators import login_required, role_required

bp = Blueprint('patients', __name__, url_prefix='/api')


@bp.route('/patients')
@login_required
def api_patients():
    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(50, int(request.args.get('per_page', 20)))
    search   = sanitise_str(request.args.get('q', ''), 100) or ''
    try:
        with DbCursor() as (cur, conn):
            base = (
                'SELECT patient_id, first_name, last_name, gender, phone, email, '
                'blood_group, TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) AS age '
                'FROM Patients_STU001 '
            )
            if search:
                like = f'%{search}%'
                cur.execute(
                    base + 'WHERE first_name LIKE %s OR last_name LIKE %s '
                    'OR phone LIKE %s OR email LIKE %s ORDER BY last_name',
                    (like, like, like, like)
                )
            else:
                cur.execute(base + 'ORDER BY last_name')
            all_rows = cur.fetchall()

        result = paginate(all_rows, page, per_page)
        return jsonify(ok=True, patients=result['items'], pagination={
            'page': result['page'], 'per_page': result['per_page'],
            'total': result['total'], 'total_pages': result['total_pages'],
            'has_prev': result['has_prev'], 'has_next': result['has_next'],
        })
    except Exception as e:
        return jsonify(ok=False, error=f'Patients error: {str(e)}')


@bp.route('/patients/<int:patient_id>')
@login_required
def api_patient_detail(patient_id):
    role = session.get('role')
    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'SELECT *, TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) AS age '
                'FROM Patients_STU001 WHERE patient_id = %s',
                (patient_id,)
            )
            patient = cur.fetchone()
            if not patient:
                return jsonify(ok=False, error='Patient not found.'), 404

            for f in ('date_of_birth', 'registration_date'):
                if patient.get(f):
                    patient[f] = str(patient[f])

            medical_history = []
            if role in ('ADMIN', 'DOCTOR'):
                cur.execute(
                    'SELECT mr.record_id, mr.diagnosis, mr.prescription, '
                    'mr.treatment_plan, mr.record_date, d.last_name AS doctor_last '
                    'FROM MedicalRecords_STU001 mr '
                    'JOIN Doctors_STU001 d ON mr.doctor_id = d.doctor_id '
                    'WHERE mr.patient_id = %s ORDER BY mr.record_date DESC',
                    (patient_id,)
                )
                medical_history = cur.fetchall()
                for r in medical_history:
                    r['record_date'] = str(r['record_date'])

            billing_history = []
            if role in ('ADMIN', 'BILLING'):
                cur.execute(
                    'SELECT bill_id, amount, tax_amount, total_amount, '
                    'payment_status, billing_date '
                    'FROM Billing_STU001 WHERE patient_id = %s '
                    'ORDER BY billing_date DESC',
                    (patient_id,)
                )
                billing_history = cur.fetchall()
                for b in billing_history:
                    b['billing_date'] = str(b['billing_date'])
                    b['amount']       = float(b['amount'])
                    b['tax_amount']   = float(b['tax_amount'])
                    b['total_amount'] = float(b['total_amount'])

        return jsonify(ok=True, patient=patient,
                       medical_history=medical_history,
                       billing_history=billing_history)
    except Exception as e:
        return jsonify(ok=False, error=f'Patient detail error: {str(e)}')


@bp.route('/patients/register', methods=['POST'])
@role_required('ADMIN', 'RECEPTIONIST')
def api_register_patient():
    data = request.get_json() or {}
    err = require_fields(data, ('first_name', 'last_name', 'date_of_birth', 'gender'))
    if err:
        return jsonify(ok=False, error=err)

    clean = {
        'first_name':      sanitise_str(data.get('first_name'), 50),
        'last_name':       sanitise_str(data.get('last_name'), 50),
        'date_of_birth':   sanitise_str(data.get('date_of_birth'), 20),
        'gender':          sanitise_str(data.get('gender'), 10),
        'email':           sanitise_str(data.get('email'), 100),
        'phone':           sanitise_str(data.get('phone'), 20),
        'address':         sanitise_str(data.get('address'), 500),
        'blood_group':     sanitise_str(data.get('blood_group'), 5),
        'emergency_name':  sanitise_str(data.get('emergency_name'), 100),
        'emergency_phone': sanitise_str(data.get('emergency_phone'), 20),
        'insurance_id':    sanitise_str(data.get('insurance_id'), 50),
    }

    try:
        with DbCursor() as (cur, conn):
            # RegisterPatient_STU001 has 11 IN + 2 OUT (patient_id, status_message)
            # OUT params are at index 11 and 12
            cur.callproc('RegisterPatient_STU001', [
                clean['first_name'], clean['last_name'], clean['date_of_birth'],
                clean['gender'], clean['email'], clean['phone'], clean['address'],
                clean['blood_group'], clean['emergency_name'], clean['emergency_phone'],
                clean['insurance_id'], 0, ''
            ])

            # Read OUT params via session variables
            cur.execute(
                'SELECT @_RegisterPatient_STU001_11 AS new_id, '
                '       @_RegisterPatient_STU001_12 AS msg'
            )
            row = cur.fetchone()
            new_id = row['new_id'] if row else None
            msg    = row['msg']    if row else ''

            if msg and 'Error' in str(msg):
                conn.rollback()
                return jsonify(ok=False, error=msg)

        return jsonify(ok=True,
                       message=f'Patient registered successfully (ID: {new_id}).',
                       patient_id=new_id)
    except Exception as e:
        return jsonify(ok=False, error=f'Registration error: {str(e)}')
