from flask import Blueprint, request, jsonify
from app.core.db import DbCursor
from app.core.helpers import paginate, sanitise_str
from app.core.decorators import role_required

bp = Blueprint('billing', __name__, url_prefix='/api')


@bp.route('/billing')
@role_required('ADMIN', 'BILLING')
def api_billing_list():
    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(50, int(request.args.get('per_page', 20)))
    try:
        with DbCursor() as (cur, conn):
            cur.execute(
                'SELECT b.bill_id, b.amount, b.tax_amount, b.total_amount, '
                'b.payment_status, b.billing_date, '
                'p.first_name AS patient_first, p.last_name AS patient_last '
                'FROM Billing_STU001 b '
                'JOIN Patients_STU001 p ON b.patient_id = p.patient_id '
                'ORDER BY b.bill_id DESC'
            )
            bills = cur.fetchall()
            for b in bills:
                b['amount']       = float(b['amount'])
                b['tax_amount']   = float(b['tax_amount'])
                b['total_amount'] = float(b['total_amount'])
                b['billing_date'] = str(b['billing_date'])
        result = paginate(bills, page, per_page)
        return jsonify(ok=True, bills=result['items'], pagination={
            'page': result['page'], 'per_page': result['per_page'],
            'total': result['total'], 'total_pages': result['total_pages'],
            'has_prev': result['has_prev'], 'has_next': result['has_next'],
        })
    except Exception as e:
        return jsonify(ok=False, error=f'Billing error: {str(e)}')


@bp.route('/billing/process/<int:bill_id>', methods=['POST'])
@role_required('ADMIN', 'BILLING')
def api_process_payment(bill_id):
    data           = request.get_json() or {}
    payment_method = sanitise_str(data.get('payment_method', 'Cash'), 50)
    paid_amount    = float(data.get('paid_amount', 0))
    try:
        with DbCursor() as (cur, conn):

            # First verify the bill exists and is payable
            cur.execute(
                'SELECT total_amount, payment_status '
                'FROM Billing_STU001 WHERE bill_id = %s',
                (bill_id,)
            )
            bill = cur.fetchone()
            if not bill:
                return jsonify(ok=False, error='Bill not found.')
            if bill['payment_status'] == 'Paid':
                return jsonify(ok=False, error='This bill has already been paid.')
            if bill['payment_status'] == 'Cancelled':
                return jsonify(ok=False, error='This bill has been cancelled.')
            if paid_amount < float(bill['total_amount']):
                return jsonify(ok=False,
                               error=f'Amount paid (${paid_amount:.2f}) is less than '
                                     f'total due (${float(bill["total_amount"]):.2f}).')

            # Try stored procedure first
            try:
                cur.callproc('ProcessPayment_STU001',
                             [bill_id, payment_method, paid_amount, ''])
                cur.execute('SELECT @_ProcessPayment_STU001_3 AS msg')
                row = cur.fetchone()
                msg = (row.get('msg') or '') if row else ''
                if msg and 'Error' in str(msg):
                    conn.rollback()
                    return jsonify(ok=False, error=msg)

            except Exception as proc_err:
                # Stored procedure missing or failed — fall back to direct UPDATE
                if '1305' in str(proc_err) or 'does not exist' in str(proc_err):
                    cur.execute(
                        "UPDATE Billing_STU001 "
                        "SET payment_status='Paid', payment_method=%s "
                        "WHERE bill_id=%s",
                        (payment_method, bill_id)
                    )
                else:
                    raise proc_err

        return jsonify(ok=True, message='Payment processed successfully.')
    except Exception as e:
        return jsonify(ok=False, error=f'Payment error: {str(e)}')


@bp.route('/billing/create', methods=['POST'])
@role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
def api_create_bill():
    data           = request.get_json() or {}
    patient_id     = data.get('patient_id')
    appointment_id = data.get('appointment_id')
    amount         = float(data.get('amount', 0))

    if not patient_id or amount <= 0:
        return jsonify(ok=False, error='Patient and amount are required.')

    tax_amount   = round(amount * 0.10, 2)
    total_amount = round(amount + tax_amount, 2)

    try:
        with DbCursor() as (cur, conn):
            if appointment_id:
                cur.execute(
                    'SELECT bill_id FROM Billing_STU001 WHERE appointment_id = %s',
                    (appointment_id,)
                )
                if cur.fetchone():
                    return jsonify(ok=False,
                                   error='A bill already exists for this appointment.')

            cur.execute(
                'INSERT INTO Billing_STU001 '
                '(patient_id, appointment_id, amount, tax_amount, '
                ' total_amount, payment_status) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (int(patient_id),
                 int(appointment_id) if appointment_id else None,
                 amount, tax_amount, total_amount, 'Pending')
            )
            new_id = cur.lastrowid

        return jsonify(ok=True,
                       message=f'Bill created (ID: {new_id}). Total: ${total_amount:.2f}',
                       bill_id=new_id,
                       total_amount=total_amount)
    except Exception as e:
        return jsonify(ok=False, error=f'Create bill error: {str(e)}')