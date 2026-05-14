from flask import Blueprint, request, session, jsonify
from app.core.db import DbCursor
from app.core.helpers import sanitise_str, require_fields
from app.core.decorators import role_required

bp = Blueprint('medical', __name__, url_prefix='/api')

@bp.route('/medical-records/add', methods=['POST'])
@role_required('ADMIN', 'DOCTOR')
def api_add_medical_record():
    data = request.get_json() or {}
    err = require_fields(data, ('patient_id', 'doctor_id', 'diagnosis'))
    if err:
        return jsonify(ok=False, error=err)
    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'INSERT INTO MedicalRecords_STU001 '
                '(patient_id, doctor_id, diagnosis, prescription, treatment_plan) '
                'VALUES (%s, %s, %s, %s, %s)',
                (
                    int(data['patient_id']),
                    int(data['doctor_id']),
                    sanitise_str(data.get('diagnosis'), 2000),
                    sanitise_str(data.get('prescription'), 2000),
                    sanitise_str(data.get('treatment_plan'), 2000),
                )
            )
            new_id = cur.lastrowid
        return jsonify(ok=True, message='Medical record saved successfully.', record_id=new_id)
    except Exception as e:
        return jsonify(ok=False, error=f'Medical record error: {str(e)}')
