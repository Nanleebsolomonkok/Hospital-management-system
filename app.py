
from flask import Flask, request, session, jsonify, send_from_directory, Response
from mysql.connector import connect, Error
from functools import wraps
import hashlib
import random
import string
import os
import decimal
import datetime
import io
import csv

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production')

# ============================================
# DATABASE CONFIGURATION
# ============================================

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'kafka-3d6dfa32-nanleebsolomon.c.aivencloud.com'),
    'user':     os.environ.get('DB_USER', 'avnadmin'),
    'password': os.environ.get('DB_PASSWORD', 'AVNS_-d5hgiKbQNp9Kyqe8Fg'),
    'database': os.environ.get('DB_NAME', 'HospitalManagement_STU001'),
    'port':     int(os.environ.get('DB_PORT', 14624)),
    'autocommit': False,
}

def get_db():
    """Open and return a database connection, or None on failure."""
    try:
        return connect(**DB_CONFIG)
    except Error as exc:
        app.logger.error("DB connection error: %s", exc)
        return None

# ============================================
# DECORATORS
# ============================================

def api_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return wrapper

def api_role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get('role') not in allowed_roles:
                return jsonify({'success': False, 'message': 'Access denied'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ============================================
# UTILITIES
# ============================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8
        and any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
    )

def generate_temp_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(random.SystemRandom().choice(chars) for _ in range(length))

def log_audit(action: str, description: str) -> None:
    conn = get_db()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO AuditLog_STU001 (table_name, action, new_values, user_name) "
            "VALUES (%s, %s, %s, %s)",
            ('SYSTEM', action, description, session.get('username', 'SYSTEM'))
        )
        conn.commit()
    except Error as e:
        app.logger.error("Audit log error: %s", e)
    finally:
        conn.close()

def dictfetchall(cursor):
    """Returns all rows from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    res = []
    for row in rows:
        d = dict(zip(columns, row))
        for k, v in d.items():
            if isinstance(v, decimal.Decimal):
                d[k] = float(v)
            elif isinstance(v, (datetime.date, datetime.datetime)):
                d[k] = str(v)
            elif isinstance(v, datetime.timedelta):
                d[k] = str(v)
        res.append(d)
    return res

def dictfetchone(cursor):
    """Returns a single row from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if not row:
        return None
    d = dict(zip(columns, row))
    for k, v in d.items():
        if isinstance(v, decimal.Decimal):
            d[k] = float(v)
        elif isinstance(v, (datetime.date, datetime.datetime)):
            d[k] = str(v)
        elif isinstance(v, datetime.timedelta):
            d[k] = str(v)
    return d

# ============================================
# FRONTEND ROUTES
# ============================================

@app.route('/')
@app.route('/login.html')
def serve_login():
    return send_from_directory('static', 'login.html')

@app.route('/app')
@app.route('/index.html')
def serve_app():
    return send_from_directory('static', 'index.html')


# ============================================
# API ROUTES - AUTH
# ============================================

@app.route('/api/session', methods=['GET'])
def get_session():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'user_id': session['user_id'],
                'username': session['username'],
                'full_name': session.get('full_name', ''),
                'role': session['role'],
                'must_change_password': session.get('must_change_password', False)
            }
        })
    return jsonify({'authenticated': False})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'})
        
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, username, password_hash, role, is_active, must_change_password, full_name
            FROM Users_STU001 WHERE username = %s
        """, (username,))
        user = dictfetchone(cur)
        
        if user and user['password_hash'] == hash_password(password):
            if not user['is_active']:
                return jsonify({'success': False, 'message': 'Account disabled'})
                
            session.clear()
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            session['must_change_password'] = bool(user['must_change_password'])
            
            log_audit('LOGIN', f"User {username} logged in via API")
            
            return jsonify({
                'success': True,
                'must_change_password': session['must_change_password']
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/logout', methods=['POST'])
def api_logout():
    username = session.get('username')
    if username:
        log_audit('LOGOUT', f"User {username} logged out")
    session.clear()
    return jsonify({'success': True})

@app.route('/api/change-password', methods=['POST'])
@api_login_required
def api_change_password():
    data = request.json
    curr_pwd = data.get('current_password')
    new_pwd = data.get('new_password')
    
    if not is_strong_password(new_pwd):
        return jsonify({'success': False, 'message': 'Password is not strong enough'})
        
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM Users_STU001 WHERE user_id = %s", (session['user_id'],))
        row = cur.fetchone()
        
        if row and row[0] == hash_password(curr_pwd):
            cur.execute("""
                UPDATE Users_STU001
                SET password_hash = %s, must_change_password = FALSE
                WHERE user_id = %s
            """, (hash_password(new_pwd), session['user_id']))
            conn.commit()
            session['must_change_password'] = False
            log_audit('UPDATE', f"User {session['username']} changed password")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Current password incorrect'})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/profile', methods=['GET', 'PUT'])
@api_login_required
def api_profile():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        if request.method == 'GET':
            cur.execute("SELECT username, email, full_name, role, profile_picture FROM Users_STU001 WHERE user_id = %s", (session['user_id'],))
            user = dictfetchone(cur)
            return jsonify({'success': True, 'profile': user})
        elif request.method == 'PUT':
            data = request.json
            full_name = data.get('full_name')
            email = data.get('email')
            cur.execute("UPDATE Users_STU001 SET full_name = %s, email = %s WHERE user_id = %s", (full_name, email, session['user_id']))
            conn.commit()
            session['full_name'] = full_name
            return jsonify({'success': True})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/profile/avatar', methods=['POST'])
@api_login_required
def api_upload_avatar():
    if 'avatar' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'})
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Use PNG, JPG, GIF, or WebP.'})
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"user_{session['user_id']}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    avatar_url = f"/static/uploads/avatars/{filename}"
    
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Users_STU001 SET profile_picture = %s WHERE user_id = %s", (avatar_url, session['user_id']))
        conn.commit()
        session['profile_picture'] = avatar_url
        return jsonify({'success': True, 'avatar_url': avatar_url})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()


# ============================================
# API ROUTES - DASHBOARD
# ============================================

@app.route('/api/dashboard/stats', methods=['GET'])
@api_login_required
def api_dashboard_stats():
    role = session.get('role')
    user_id = session.get('user_id')
    
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    stats = {}
    try:
        cur = conn.cursor()
        
        if role == 'ADMIN':
            cur.execute("SELECT COUNT(*) FROM Patients_STU001")
            stats['total_patients'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Doctors_STU001 WHERE email IN (SELECT email FROM Users_STU001 WHERE is_active=1)")
            stats['active_doctors'] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM Appointments_STU001 WHERE appointment_date = CURDATE()")
            stats['today_appointments'] = cur.fetchone()[0]
            
            cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM Billing_STU001 WHERE payment_status='Paid' AND DATE(billing_date) = CURDATE()")
            stats['total_revenue'] = float(cur.fetchone()[0])
            
            cur.execute("SELECT COUNT(*) FROM Beds_STU001 WHERE status = 'Available'")
            stats['available_beds'] = cur.fetchone()[0]
            
            # Chart data: Revenue last 7 days
            cur.execute("""
                SELECT DATE(billing_date) as day, COALESCE(SUM(total_amount), 0) as total
                FROM Billing_STU001
                WHERE payment_status = 'Paid' AND billing_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
                GROUP BY DATE(billing_date)
                ORDER BY day ASC
            """)
            revenue_rows = dictfetchall(cur)
            stats['revenue_chart'] = [{'day': str(r['day']), 'total': float(r['total'])} for r in revenue_rows]
            
            # Chart data: Bed occupancy
            cur.execute("SELECT status, COUNT(*) as cnt FROM Beds_STU001 GROUP BY status")
            bed_rows = dictfetchall(cur)
            stats['bed_occupancy'] = [{'status': r['status'], 'count': r['cnt']} for r in bed_rows]
            
        elif role == 'DOCTOR':
            cur.execute("SELECT doctor_id FROM Doctors_STU001 WHERE email = (SELECT email FROM Users_STU001 WHERE user_id = %s)", (user_id,))
            doc = cur.fetchone()
            if doc:
                doc_id = doc[0]
                cur.execute("SELECT COUNT(DISTINCT patient_id) FROM Appointments_STU001 WHERE doctor_id = %s", (doc_id,))
                stats['patient_count'] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM Lab_Results_STU001 WHERE doctor_id = %s AND status = 'Pending'", (doc_id,))
                stats['pending_labs'] = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT a.appointment_id, a.patient_id, p.first_name as patient_first, p.last_name as patient_last,
                           d.last_name as doctor_last,
                           a.appointment_date, a.appointment_time, a.status, a.reason
                    FROM Appointments_STU001 a
                    JOIN Patients_STU001 p ON a.patient_id = p.patient_id
                    JOIN Doctors_STU001 d ON a.doctor_id = d.doctor_id
                    WHERE a.doctor_id = %s AND a.appointment_date >= CURDATE()
                    ORDER BY a.appointment_date ASC, a.appointment_time ASC
                """, (doc_id,))
                stats['appointments'] = dictfetchall(cur)
            else:
                stats['patient_count'] = 0
                stats['appointments'] = []
                
        elif role == 'RECEPTIONIST':
            cur.execute("""
                SELECT a.appointment_id, p.first_name as patient_first, p.last_name as patient_last,
                       d.last_name as doctor_last, a.appointment_time, a.status
                FROM Appointments_STU001 a
                JOIN Patients_STU001 p ON a.patient_id = p.patient_id
                JOIN Doctors_STU001 d ON a.doctor_id = d.doctor_id
                WHERE a.appointment_date = CURDATE()
                ORDER BY a.appointment_time ASC
            """)
            stats['today_appointments'] = dictfetchall(cur)
            
        elif role == 'BILLING':
            cur.execute("""
                SELECT b.bill_id, p.first_name as patient_first, p.last_name as patient_last, b.total_amount
                FROM Billing_STU001 b
                JOIN Patients_STU001 p ON b.patient_id = p.patient_id
                WHERE b.payment_status = 'Pending'
                ORDER BY b.billing_date ASC
            """)
            stats['pending_bills'] = dictfetchall(cur)
            
            cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM Billing_STU001 WHERE payment_status = 'Paid' AND DATE(billing_date) = CURDATE()")
            stats['today_revenue'] = float(cur.fetchone()[0])
        
        elif role == 'PHARMACIST':
            cur.execute("SELECT COUNT(*) FROM Pharmacy_Inventory_STU001 WHERE stock_quantity < 100")
            stats['low_stock'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM Pharmacy_Inventory_STU001")
            stats['total_items'] = cur.fetchone()[0]
            
        elif role == 'LAB_TECH':
            cur.execute("SELECT COUNT(*) FROM Lab_Results_STU001 WHERE status = 'Pending'")
            stats['pending_tests'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM Lab_Results_STU001 WHERE status = 'Completed' AND DATE(result_date) = CURDATE()")
            stats['completed_today'] = cur.fetchone()[0]
            
        return jsonify({'success': True, 'stats': stats})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - PATIENTS
# ============================================

@app.route('/api/patients', methods=['GET', 'POST'])
@api_login_required
@api_role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST', 'PHARMACIST')
def api_patients():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    if request.method == 'GET':
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT patient_id, first_name, last_name, gender, date_of_birth,
                       TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) AS age,
                       phone, email, blood_group
                FROM Patients_STU001
                ORDER BY last_name ASC, first_name ASC
            """)
            patients = dictfetchall(cur)
            return jsonify({'success': True, 'patients': patients})
        except Error as e:
            return jsonify({'success': False, 'message': str(e)})
        finally:
            conn.close()
            
    elif request.method == 'POST':
        if session.get('role') not in ('ADMIN', 'RECEPTIONIST'):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
            
        data = request.json
        try:
            cur = conn.cursor()
            args = (
                data.get('first_name'), data.get('last_name'), data.get('date_of_birth'), data.get('gender'),
                data.get('email'), data.get('phone'), '', data.get('blood_group'),
                '', '', data.get('insurance_id'), 0, ''
            )
            res_args = cur.callproc('RegisterPatient_STU001', args)
            conn.commit()
            if res_args[11] == -1:
                return jsonify({'success': False, 'message': res_args[12]})
            return jsonify({'success': True})
        except Error as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)})
        finally:
            conn.close()

@app.route('/api/patients/<int:patient_id>', methods=['GET'])
@api_login_required
@api_role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST', 'BILLING')
def api_patient_detail(patient_id):
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT patient_id, first_name, last_name, gender, date_of_birth,
                   TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) AS age,
                   phone, email, address, blood_group, insurance_id
            FROM Patients_STU001 WHERE patient_id = %s
        """, (patient_id,))
        patient = dictfetchone(cur)
        
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'})
            
        medical_history = None
        billing_history = None
        
        if session.get('role') in ('ADMIN', 'DOCTOR'):
            cur.execute("""
                SELECT m.record_date, m.diagnosis, m.prescription, m.treatment_plan,
                       d.first_name as doctor_first, d.last_name as doctor_last
                FROM MedicalRecords_STU001 m
                JOIN Doctors_STU001 d ON m.doctor_id = d.doctor_id
                WHERE m.patient_id = %s
                ORDER BY m.record_date DESC
            """, (patient_id,))
            medical_history = dictfetchall(cur)
            
        if session.get('role') in ('ADMIN', 'BILLING'):
            cur.execute("""
                SELECT bill_id, total_amount, payment_status, billing_date
                FROM Billing_STU001
                WHERE patient_id = %s
                ORDER BY billing_date DESC
            """, (patient_id,))
            billing_history = dictfetchall(cur)
            
        return jsonify({
            'success': True,
            'data': {
                'patient': patient,
                'medical_history': medical_history,
                'billing_history': billing_history
            }
        })
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/patients/<int:patient_id>', methods=['PUT'])
@api_login_required
@api_role_required('ADMIN', 'RECEPTIONIST')
def api_patient_update(patient_id):
    data = request.json
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE Patients_STU001
            SET first_name=%s, last_name=%s, date_of_birth=%s, gender=%s,
                phone=%s, email=%s, address=%s, blood_group=%s, insurance_id=%s
            WHERE patient_id=%s
        """, (data.get('first_name'), data.get('last_name'), data.get('date_of_birth'),
              data.get('gender'), data.get('phone'), data.get('email'), data.get('address'),
              data.get('blood_group'), data.get('insurance_id'), patient_id))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - APPOINTMENTS
# ============================================

@app.route('/api/appointments', methods=['GET', 'POST'])
@api_login_required
@api_role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
def api_appointments():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    if request.method == 'GET':
        try:
            cur = conn.cursor()
            role = session.get('role')
            if role == 'DOCTOR':
                cur.execute("SELECT doctor_id FROM Doctors_STU001 WHERE email = (SELECT email FROM Users_STU001 WHERE user_id = %s)", (session['user_id'],))
                doc = cur.fetchone()
                doc_id = doc[0] if doc else -1
                cur.execute("""
                    SELECT a.appointment_id, a.patient_id, p.first_name as patient_first, p.last_name as patient_last,
                           d.last_name as doctor_last,
                           a.appointment_date, a.appointment_time, a.status, a.reason
                    FROM Appointments_STU001 a
                    JOIN Patients_STU001 p ON a.patient_id = p.patient_id
                    JOIN Doctors_STU001 d ON a.doctor_id = d.doctor_id
                    WHERE a.doctor_id = %s
                    ORDER BY a.appointment_date DESC, a.appointment_time ASC
                """, (doc_id,))
            else:
                cur.execute("""
                    SELECT a.appointment_id, p.first_name as patient_first, p.last_name as patient_last, p.patient_id,
                           d.first_name as doctor_first, d.last_name as doctor_last,
                           a.appointment_date, a.appointment_time, a.status, a.reason
                    FROM Appointments_STU001 a
                    JOIN Patients_STU001 p ON a.patient_id = p.patient_id
                    JOIN Doctors_STU001 d ON a.doctor_id = d.doctor_id
                    ORDER BY a.appointment_date DESC, a.appointment_time ASC
                """)
            appts = dictfetchall(cur)
            return jsonify({'success': True, 'appointments': appts})
        except Error as e:
            return jsonify({'success': False, 'message': str(e)})
        finally:
            conn.close()
            
    elif request.method == 'POST':
        if session.get('role') not in ('ADMIN', 'RECEPTIONIST'):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
            
        data = request.json
        try:
            cur = conn.cursor()
            args = (
                data.get('patient_id'), data.get('doctor_id'),
                data.get('appointment_date'), data.get('appointment_time'),
                data.get('reason'), 0, ''
            )
            res_args = cur.callproc('ScheduleAppointment_STU001', args)
            conn.commit()
            if res_args[5] == -1:
                return jsonify({'success': False, 'message': res_args[6]})
            return jsonify({'success': True})
        except Error as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)})
        finally:
            conn.close()

@app.route('/api/appointments/<int:appt_id>/status', methods=['PUT'])
@api_login_required
@api_role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
def api_appointment_status(appt_id):
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    data = request.json
    status = data.get('status')
    
    if status not in ('Scheduled', 'Completed', 'Cancelled', 'No Show'):
        return jsonify({'success': False, 'message': 'Invalid status'})
        
    try:
        cur = conn.cursor()
        cur.execute("UPDATE Appointments_STU001 SET status = %s WHERE appointment_id = %s", (status, appt_id))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - MEDICAL RECORDS
# ============================================

@app.route('/api/medical-records/form-data', methods=['GET'])
@api_login_required
@api_role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
def api_medical_form_data():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT patient_id, first_name, last_name FROM Patients_STU001 ORDER BY last_name ASC")
        patients = dictfetchall(cur)
        
        cur.execute("SELECT doctor_id, first_name, last_name, specialization FROM Doctors_STU001 ORDER BY last_name ASC")
        doctors = dictfetchall(cur)
        
        return jsonify({'success': True, 'patients': patients, 'doctors': doctors})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/medical-records', methods=['POST'])
@api_login_required
@api_role_required('ADMIN', 'DOCTOR')
def api_medical_records():
    data = request.json
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        doctor_id = data.get('doctor_id')
        if session.get('role') == 'DOCTOR' and not doctor_id:
            cur.execute("SELECT doctor_id FROM Doctors_STU001 WHERE email = (SELECT email FROM Users_STU001 WHERE user_id = %s)", (session.get('user_id'),))
            doc = cur.fetchone()
            if doc:
                doctor_id = doc[0]
                
        cur.execute("""
            INSERT INTO MedicalRecords_STU001 (patient_id, doctor_id, appointment_id, diagnosis, prescription, treatment_plan)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data.get('patient_id'), doctor_id, data.get('appointment_id'), data.get('diagnosis'),
              data.get('prescription'), data.get('treatment_plan')))
              
        lab_test_ids = data.get('lab_test_ids', [])
        for test_id in lab_test_ids:
            cur.execute("""
                INSERT INTO Lab_Results_STU001 (patient_id, doctor_id, test_id, status)
                VALUES (%s, %s, %s, 'Pending')
            """, (data.get('patient_id'), doctor_id, test_id))
            
        bill_amount = 150.00
        
        cur.execute("""
            INSERT INTO Billing_STU001 (patient_id, appointment_id, total_amount, amount, payment_status, bill_type)
            VALUES (%s, %s, %s, %s, %s, 'Consultation')
        """, (data.get('patient_id'), data.get('appointment_id'), bill_amount, bill_amount, 'Pending'))
        
        if data.get('appointment_id'):
            cur.execute("UPDATE Appointments_STU001 SET status = 'Completed' WHERE appointment_id = %s", (data.get('appointment_id'),))
            
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - BILLING
# ============================================

@app.route('/api/billing', methods=['GET'])
@api_login_required
@api_role_required('ADMIN', 'BILLING')
def api_billing():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.bill_id, p.first_name as patient_first, p.last_name as patient_last,
                   b.total_amount, b.payment_status, b.billing_date, b.bill_type
            FROM Billing_STU001 b
            JOIN Patients_STU001 p ON b.patient_id = p.patient_id
            ORDER BY 
                CASE WHEN b.payment_status = 'Pending' THEN 1 ELSE 2 END,
                b.billing_date DESC
        """)
        bills = dictfetchall(cur)
        return jsonify({'success': True, 'bills': bills})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/billing/<int:bill_id>/pay', methods=['POST'])
@api_login_required
@api_role_required('ADMIN', 'BILLING')
def api_pay_bill(bill_id):
    data = request.json
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE Billing_STU001 
            SET payment_status = 'Paid', payment_method = %s, amount = %s
            WHERE bill_id = %s
        """, (data.get('payment_method'), data.get('paid_amount'), bill_id))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/billing/<int:bill_id>/receipt', methods=['GET'])
@api_login_required
@api_role_required('ADMIN', 'BILLING')
def api_bill_receipt(bill_id):
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.bill_id, b.billing_date, b.total_amount, b.payment_status,
                   b.payment_method, b.bill_type, b.amount,
                   p.first_name, p.last_name, p.phone, p.email
            FROM Billing_STU001 b
            JOIN Patients_STU001 p ON b.patient_id = p.patient_id
            WHERE b.bill_id = %s
        """, (bill_id,))
        receipt = dictfetchone(cur)
        if not receipt:
            return jsonify({'success': False, 'message': 'Bill not found'})
        return jsonify({'success': True, 'receipt': receipt})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/appointments/<int:appt_id>', methods=['PUT'])
@api_login_required
@api_role_required('ADMIN', 'DOCTOR', 'RECEPTIONIST')
def api_appointment_update(appt_id):
    data = request.json
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE Appointments_STU001
            SET appointment_date=%s, appointment_time=%s, reason=%s
            WHERE appointment_id=%s
        """, (data.get('appointment_date'), data.get('appointment_time'), data.get('reason'), appt_id))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/pharmacy/inventory/<int:item_id>', methods=['PUT'])
@api_login_required
@api_role_required('ADMIN', 'PHARMACIST')
def api_pharmacy_inventory_update(item_id):
    data = request.json
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE Pharmacy_Inventory_STU001
            SET item_name=%s, category=%s, stock_quantity=%s, unit_price=%s, expiry_date=%s, supplier=%s
            WHERE item_id=%s
        """, (data.get('item_name'), data.get('category'), data.get('stock_quantity'),
              data.get('unit_price'), data.get('expiry_date'), data.get('supplier'), item_id))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()



@app.route('/api/admin/users', methods=['GET'])
@api_login_required
@api_role_required('ADMIN')
def api_admin_users():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, full_name, role, email, is_active, must_change_password FROM Users_STU001")
        users = dictfetchall(cur)
        return jsonify({'success': True, 'users': users})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@api_login_required
@api_role_required('ADMIN')
def api_reset_password(user_id):
    temp_pwd = generate_temp_password()
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE Users_STU001 
            SET password_hash = %s, must_change_password = TRUE 
            WHERE user_id = %s
        """, (hash_password(temp_pwd), user_id))
        conn.commit()
        return jsonify({'success': True, 'temp_password': temp_pwd})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/admin/audit', methods=['GET'])
@api_login_required
@api_role_required('ADMIN')
def api_admin_audit():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT log_id, table_name, action, new_values, user_name, action_timestamp 
            FROM AuditLog_STU001 
            ORDER BY action_timestamp DESC 
            LIMIT 100
        """)
        logs = dictfetchall(cur)
        return jsonify({'success': True, 'logs': logs})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - PHARMACY
# ============================================

@app.route('/api/pharmacy/inventory', methods=['GET'])
@api_login_required
def api_pharmacy_inventory():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("SELECT item_id, item_name, category, stock_quantity, unit_price, expiry_date, supplier FROM Pharmacy_Inventory_STU001 ORDER BY item_name ASC")
        items = dictfetchall(cur)
        return jsonify({'success': True, 'inventory': items})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - WARDS
# ============================================

@app.route('/api/wards', methods=['GET'])
@api_login_required
def api_wards():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("SELECT ward_id, ward_name, ward_type, capacity FROM Wards_STU001")
        wards = dictfetchall(cur)
        
        cur.execute("""
            SELECT b.bed_id, b.ward_id, b.bed_number, b.status, 
                   a.patient_id, p.first_name, p.last_name
            FROM Beds_STU001 b
            LEFT JOIN Admissions_STU001 a ON b.bed_id = a.bed_id AND a.status = 'Admitted'
            LEFT JOIN Patients_STU001 p ON a.patient_id = p.patient_id
        """)
        beds = dictfetchall(cur)
        
        return jsonify({'success': True, 'wards': wards, 'beds': beds})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - LAB
# ============================================

@app.route('/api/lab/tests', methods=['GET'])
@api_login_required
def api_lab_tests():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("SELECT test_id, test_name, test_type, cost FROM Lab_Tests_STU001")
        tests = dictfetchall(cur)
        return jsonify({'success': True, 'tests': tests})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/lab/results', methods=['GET'])
@api_login_required
def api_lab_results():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        role = session.get('role')
        if role == 'DOCTOR':
            cur.execute("SELECT doctor_id FROM Doctors_STU001 WHERE email = (SELECT email FROM Users_STU001 WHERE user_id = %s)", (session.get('user_id'),))
            doc = cur.fetchone()
            doc_id = doc[0] if doc else -1
            cur.execute("""
                SELECT r.result_id, p.first_name as patient_first, p.last_name as patient_last,
                       t.test_name, r.order_date, r.status, r.result_data,
                       b.payment_status, r.bill_id
                FROM Lab_Results_STU001 r
                JOIN Patients_STU001 p ON r.patient_id = p.patient_id
                JOIN Lab_Tests_STU001 t ON r.test_id = t.test_id
                LEFT JOIN Billing_STU001 b ON r.bill_id = b.bill_id
                WHERE r.doctor_id = %s
                ORDER BY r.order_date DESC
            """, (doc_id,))
        else:
            cur.execute("""
                SELECT r.result_id, p.first_name as patient_first, p.last_name as patient_last,
                       d.last_name as doctor_last, t.test_name, r.order_date, r.status, r.result_data,
                       b.payment_status, r.bill_id
                FROM Lab_Results_STU001 r
                JOIN Patients_STU001 p ON r.patient_id = p.patient_id
                JOIN Lab_Tests_STU001 t ON r.test_id = t.test_id
                JOIN Doctors_STU001 d ON r.doctor_id = d.doctor_id
                LEFT JOIN Billing_STU001 b ON r.bill_id = b.bill_id
                ORDER BY r.order_date DESC
            """)
        results = dictfetchall(cur)
        return jsonify({'success': True, 'results': results})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/pharmacy/inventory/<int:item_id>/dispense', methods=['POST'])
@api_login_required
@api_role_required('ADMIN', 'PHARMACIST', 'DOCTOR')
def api_pharmacy_dispense(item_id):
    data = request.json
    qty = data.get('quantity', 1)
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("SELECT stock_quantity FROM Pharmacy_Inventory_STU001 WHERE item_id = %s", (item_id,))
        row = cur.fetchone()
        if not row or row[0] < qty:
            return jsonify({'success': False, 'message': 'Insufficient stock'})
        cur.execute("UPDATE Pharmacy_Inventory_STU001 SET stock_quantity = stock_quantity - %s WHERE item_id = %s", (qty, item_id))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/pharmacy/inventory', methods=['POST'])
@api_login_required
@api_role_required('ADMIN', 'PHARMACIST')
def api_pharmacy_add():
    data = request.json
    item_name = data.get('item_name')
    category = data.get('category')
    stock_quantity = data.get('stock_quantity')
    unit_price = data.get('unit_price')
    expiry_date = data.get('expiry_date')
    
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Pharmacy_Inventory_STU001 (item_name, category, stock_quantity, unit_price, expiry_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (item_name, category, stock_quantity, unit_price, expiry_date))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/lab/results/<int:result_id>', methods=['PUT'])
@api_login_required
@api_role_required('ADMIN', 'LAB_TECH', 'DOCTOR')
def api_update_lab_result(result_id):
    data = request.json
    result_data = data.get('result_data', '')
    status = data.get('status', 'Completed')
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.payment_status
            FROM Lab_Results_STU001 r
            LEFT JOIN Billing_STU001 b ON r.bill_id = b.bill_id
            WHERE r.result_id = %s
        """, (result_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Result not found'})
        if status == 'Completed' and row[0] != 'Paid':
            return jsonify({'success': False, 'message': 'Cannot complete: Bill is not paid'})

        cur.execute("""
            UPDATE Lab_Results_STU001 
            SET result_data = %s, status = %s
            WHERE result_id = %s
        """, (result_data, status, result_id))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - WARD ADMISSION / DISCHARGE
# ============================================

@app.route('/api/wards/admit', methods=['POST'])
@api_login_required
@api_role_required('ADMIN', 'RECEPTIONIST', 'DOCTOR')
def api_ward_admit():
    data = request.json
    patient_id = data.get('patient_id')
    bed_id = data.get('bed_id')
    doctor_id = data.get('doctor_id', 1)  # Default to doctor 1 for demo purposes
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM Beds_STU001 WHERE bed_id = %s", (bed_id,))
        bed = cur.fetchone()
        if not bed or bed[0] != 'Available':
            return jsonify({'success': False, 'message': 'Bed is not available'})
        
        cur.execute("""
            INSERT INTO Admissions_STU001 (patient_id, bed_id, doctor_id, admission_date, status)
            VALUES (%s, %s, %s, NOW(), 'Admitted')
        """, (patient_id, bed_id, doctor_id))
        cur.execute("UPDATE Beds_STU001 SET status = 'Occupied' WHERE bed_id = %s", (bed_id,))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/wards/discharge/<int:bed_id>', methods=['POST'])
@api_login_required
@api_role_required('ADMIN', 'RECEPTIONIST', 'DOCTOR')
def api_ward_discharge(bed_id):
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE Admissions_STU001 SET status = 'Discharged', discharge_date = NOW()
            WHERE bed_id = %s AND status = 'Admitted'
        """, (bed_id,))
        cur.execute("UPDATE Beds_STU001 SET status = 'Available' WHERE bed_id = %s", (bed_id,))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - PATIENT TIMELINE
# ============================================

@app.route('/api/patients/<int:patient_id>/timeline', methods=['GET'])
@api_login_required
@api_role_required('ADMIN', 'DOCTOR', 'BILLING')
def api_patient_timeline(patient_id):
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        events = []
        
        cur.execute("""
            SELECT a.appointment_date as event_date, 'Appointment' as event_type,
                   CONCAT('Appointment with Dr. ', d.last_name, ' - ', a.status) as description
            FROM Appointments_STU001 a
            JOIN Doctors_STU001 d ON a.doctor_id = d.doctor_id
            WHERE a.patient_id = %s
        """, (patient_id,))
        for row in dictfetchall(cur):
            events.append({'date': str(row['event_date']), 'type': row['event_type'], 'description': row['description']})
        
        cur.execute("""
            SELECT m.record_date as event_date, 'Diagnosis' as event_type,
                   CONCAT(m.diagnosis, ' (Dr. ', d.last_name, ')') as description
            FROM MedicalRecords_STU001 m
            JOIN Doctors_STU001 d ON m.doctor_id = d.doctor_id
            WHERE m.patient_id = %s
        """, (patient_id,))
        for row in dictfetchall(cur):
            events.append({'date': str(row['event_date']), 'type': row['event_type'], 'description': row['description']})
        
        cur.execute("""
            SELECT r.order_date as event_date, 'Lab Test' as event_type,
                   CONCAT(t.test_name, ' - ', r.status) as description
            FROM Lab_Results_STU001 r
            JOIN Lab_Tests_STU001 t ON r.test_id = t.test_id
            WHERE r.patient_id = %s
        """, (patient_id,))
        for row in dictfetchall(cur):
            events.append({'date': str(row['event_date']), 'type': row['event_type'], 'description': row['description']})
        
        cur.execute("""
            SELECT b.billing_date as event_date, 'Billing' as event_type,
                   CONCAT('$', b.total_amount, ' - ', b.payment_status) as description
            FROM Billing_STU001 b
            WHERE b.patient_id = %s
        """, (patient_id,))
        for row in dictfetchall(cur):
            events.append({'date': str(row['event_date']), 'type': row['event_type'], 'description': row['description']})
        
        events.sort(key=lambda x: x['date'], reverse=True)
        return jsonify({'success': True, 'events': events})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - PHARMACY ORDERS (PHASE 3)
# ============================================
# API ROUTES - PHARMACY PRESCIPTIONS
# ============================================

@app.route('/api/pharmacy/prescriptions', methods=['GET'])
@api_login_required
@api_role_required('ADMIN', 'PHARMACIST')
def api_pharmacy_prescriptions():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT m.record_id, m.patient_id, p.first_name, p.last_name, 
                   m.prescription, m.record_date, d.last_name as doctor_last
            FROM MedicalRecords_STU001 m
            JOIN Patients_STU001 p ON m.patient_id = p.patient_id
            JOIN Doctors_STU001 d ON m.doctor_id = d.doctor_id
            WHERE m.prescription IS NOT NULL AND m.prescription != ''
            ORDER BY m.record_date DESC
            LIMIT 50
        """)
        prescriptions = dictfetchall(cur)
        return jsonify({'success': True, 'prescriptions': prescriptions})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()



@app.route('/api/pharmacy/orders', methods=['GET', 'POST'])
@api_login_required
@api_role_required('ADMIN', 'PHARMACIST')
def api_pharmacy_orders():
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
        
    try:
        cur = conn.cursor()
        if request.method == 'GET':
            cur.execute("""
                SELECT o.order_id, p.first_name, p.last_name, i.item_name, o.quantity, o.status, o.order_date, b.payment_status, b.bill_id
                FROM Pharmacy_Orders_STU001 o
                JOIN Patients_STU001 p ON o.patient_id = p.patient_id
                JOIN Pharmacy_Inventory_STU001 i ON o.item_id = i.item_id
                LEFT JOIN Billing_STU001 b ON o.bill_id = b.bill_id
                ORDER BY o.order_date DESC
            """)
            orders = dictfetchall(cur)
            return jsonify({'success': True, 'orders': orders})
            
        elif request.method == 'POST':
            data = request.json
            patient_id = data.get('patient_id')
            item_id = data.get('item_id')
            quantity = int(data.get('quantity', 1))
            
            cur.execute("SELECT unit_price FROM Pharmacy_Inventory_STU001 WHERE item_id = %s", (item_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'success': False, 'message': 'Item not found'})
            total_price = float(row[0]) * quantity
            
            cur.execute("""
                INSERT INTO Billing_STU001 (patient_id, total_amount, amount, payment_status, bill_type)
                VALUES (%s, %s, %s, 'Pending', 'Pharmacy')
            """, (patient_id, total_price, total_price))
            bill_id = cur.lastrowid
            
            cur.execute("""
                INSERT INTO Pharmacy_Orders_STU001 (patient_id, item_id, quantity, bill_id, status)
                VALUES (%s, %s, %s, %s, 'Pending Payment')
            """, (patient_id, item_id, quantity, bill_id))
            conn.commit()
            return jsonify({'success': True})
            
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/pharmacy/orders/<int:order_id>/dispense', methods=['POST'])
@api_login_required
@api_role_required('ADMIN', 'PHARMACIST')
def api_pharmacy_orders_dispense(order_id):
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT o.item_id, o.quantity, b.payment_status 
            FROM Pharmacy_Orders_STU001 o
            LEFT JOIN Billing_STU001 b ON o.bill_id = b.bill_id
            WHERE o.order_id = %s
        """, (order_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        item_id, quantity, payment_status = row
        if payment_status != 'Paid':
            return jsonify({'success': False, 'message': 'Cannot dispense: Bill is not paid'})
            
        cur.execute("UPDATE Pharmacy_Inventory_STU001 SET stock_quantity = stock_quantity - %s WHERE item_id = %s", (quantity, item_id))
        cur.execute("UPDATE Pharmacy_Orders_STU001 SET status = 'Dispensed' WHERE order_id = %s", (order_id,))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/api/lab/results/<int:result_id>/charge', methods=['POST'])
@api_login_required
@api_role_required('ADMIN', 'LAB_TECH')
def api_lab_results_charge(result_id):
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.patient_id, t.cost 
            FROM Lab_Results_STU001 r
            JOIN Lab_Tests_STU001 t ON r.test_id = t.test_id
            WHERE r.result_id = %s AND r.bill_id IS NULL
        """, (result_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Test already billed or not found'})
            
        patient_id, cost = row
        cur.execute("""
            INSERT INTO Billing_STU001 (patient_id, total_amount, amount, payment_status, bill_type)
            VALUES (%s, %s, %s, 'Pending', 'Lab Test')
        """, (patient_id, cost, cost))
        bill_id = cur.lastrowid
        
        cur.execute("UPDATE Lab_Results_STU001 SET bill_id = %s WHERE result_id = %s", (bill_id, result_id))
        conn.commit()
        return jsonify({'success': True})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# API ROUTES - REPORTS
# ============================================

@app.route('/api/reports/<report_type>', methods=['GET'])
@api_login_required
@api_role_required('ADMIN')
def api_generate_report(report_type):
    conn = get_db()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'})
    
    try:
        cur = conn.cursor()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if report_type == 'patients':
            cur.execute("""
                SELECT patient_id, first_name, last_name, gender, date_of_birth, blood_group, phone, email, insurance_id
                FROM Patients_STU001
                ORDER BY patient_id ASC
            """)
            rows = cur.fetchall()
            writer.writerow(['Patient ID', 'First Name', 'Last Name', 'Gender', 'DOB', 'Blood Group', 'Phone', 'Email', 'Insurance ID'])
            writer.writerows(rows)
            filename = f"patients_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
            
        elif report_type == 'appointments':
            cur.execute("""
                SELECT a.appointment_id, p.first_name, p.last_name, d.first_name, d.last_name, a.appointment_date, a.appointment_time, a.status, a.reason
                FROM Appointments_STU001 a
                JOIN Patients_STU001 p ON a.patient_id = p.patient_id
                JOIN Doctors_STU001 d ON a.doctor_id = d.doctor_id
                ORDER BY a.appointment_date DESC
            """)
            rows = cur.fetchall()
            writer.writerow(['Appt ID', 'Patient First Name', 'Patient Last Name', 'Doctor First Name', 'Doctor Last Name', 'Date', 'Time', 'Status', 'Reason'])
            writer.writerows(rows)
            filename = f"appointments_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
            
        elif report_type == 'billing':
            cur.execute("""
                SELECT b.bill_id, p.first_name, p.last_name, b.total_amount, b.amount, b.payment_status, b.payment_method, b.billing_date
                FROM Billing_STU001 b
                JOIN Patients_STU001 p ON b.patient_id = p.patient_id
                ORDER BY b.billing_date DESC
            """)
            rows = cur.fetchall()
            writer.writerow(['Bill ID', 'Patient First Name', 'Patient Last Name', 'Total Amount', 'Amount Paid', 'Status', 'Method', 'Billing Date'])
            writer.writerows(rows)
            filename = f"billing_report_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
            
        else:
            return jsonify({'success': False, 'message': 'Invalid report type'})
            
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )
        
    except Error as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    app.run(debug=True)
