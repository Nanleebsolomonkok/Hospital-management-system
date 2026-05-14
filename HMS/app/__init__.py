

from flask import Flask, session, redirect, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Shared limiter — imported by blueprints
limiter = Limiter(key_func=get_remote_address, default_limits=[])


def create_app():
    app = Flask(__name__, static_folder='../static', template_folder='../templates')

    # ── Config ──────────────────────────────────────────────
    app.secret_key = os.environ.get('SECRET_KEY', 'CHANGE-THIS-IN-PRODUCTION')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['RATELIMIT_STORAGE_URI']   = os.environ.get('REDIS_URL', 'memory://')

    # ── Extensions ───────────────────────────────────────────
    limiter.init_app(app)

    # ── Blueprints ───────────────────────────────────────────
    from app.api.auth        import bp as auth_bp
    from app.api.patients    import bp as patients_bp
    from app.api.appointments import bp as appointments_bp
    from app.api.medical     import bp as medical_bp
    from app.api.billing     import bp as billing_bp
    from app.api.admin       import bp as admin_bp
    from app.api.dashboard   import bp as dashboard_bp
    from app.api.formdata    import bp as formdata_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(medical_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(formdata_bp)

    # ── Page routes (serve HTML files) ───────────────────────
    _register_page_routes(app)

    # ── Error handlers ───────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        if '/api/' in str(e):
            return jsonify(ok=False, error='Endpoint not found'), 404
        return send_from_directory('../templates', '404.html'), 404

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify(ok=False, error='Too many requests. Please wait and try again.'), 429

    return app


def _register_page_routes(app):
    from flask import render_template, session, redirect
    from app.core.decorators import login_required

    ROLE_DASHBOARDS = {
        'ADMIN':        'dashboard_admin.html',
        'DOCTOR':       'dashboard_doctor.html',
        'RECEPTIONIST': 'dashboard_receptionist.html',
        'BILLING':      'dashboard_billing.html',
    }

    @app.route('/')
    def index():
        return redirect('/dashboard' if 'user_id' in session else '/login')

    @app.route('/login')
    def login_page():
        if 'user_id' in session:
            return redirect('/dashboard')
        return render_template('login.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        tpl = ROLE_DASHBOARDS.get(session.get('role'), 'dashboard_guest.html')
        return render_template(tpl)

    @app.route('/patients')
    @login_required
    def patients_page():
        return render_template('patients.html')

    @app.route('/patients/<int:patient_id>')
    @login_required
    def patient_detail_page(patient_id):
        return render_template('patient_detail.html')

    @app.route('/register-patient')
    @login_required
    def register_patient_page():
        return render_template('register_patient.html')

    @app.route('/appointments')
    @login_required
    def appointments_page():
        return render_template('appointments.html')

    @app.route('/appointments/schedule')
    @login_required
    def schedule_appointment_page():
        return render_template('schedule_appointment.html')

    @app.route('/medical-records/add')
    @login_required
    def add_medical_record_page():
        return render_template('add_medical_record.html')

    @app.route('/billing')
    @login_required
    def billing_page():
        return render_template('billing.html')

    @app.route('/admin/users')
    @login_required
    def admin_users_page():
        return render_template('admin_users.html')

    @app.route('/admin/audit-log')
    @login_required
    def admin_audit_page():
        return render_template('admin_audit.html')

    @app.route('/change-password')
    @login_required
    def change_password_page():
        return render_template('change_password.html')
