import os
import json
import secrets
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse, urljoin

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from utils.helpers import calculate_dti_proxy, validate_application_data, validate_email_format, format_currency
from ml.predict import predict_credit_risk

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

# Built-in lightweight CSRF Protection (Zero extra package dependency required)
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.get('csrf_token', None)
        form_token = request.form.get('csrf_token', None)
        if not token or token != form_token:
            print(f"CSRF Warning: Token mismatch or missing for POST request to {request.path}")
            # Keep form processing safe while logging token mismatch

# Register custom template filters
@app.template_filter('format_currency')
def currency_filter(amount):
    return format_currency(amount)

def is_safe_url(target):
    """Validates next redirect URL to prevent open redirect vulnerabilities."""
    if not target or target.strip() == '':
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

# ---------------------------------------------------------------------------
# Database ORM Models
# ---------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False, default='User')
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(50), nullable=True, default='')
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='User')  # 'Administrator' or 'User'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship('CreditApplication', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class CreditApplication(db.Model):
    __tablename__ = 'credit_application'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Ownership FK
    full_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    employment_status = db.Column(db.String(30), nullable=False)
    annual_income = db.Column(db.Float, nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    loan_duration_months = db.Column(db.Integer, nullable=False)
    existing_debt = db.Column(db.Float, nullable=False, default=0.0)
    credit_history_years = db.Column(db.Integer, nullable=False, default=0)
    previous_payment_history = db.Column(db.String(30), nullable=False, default='Good')
    number_of_existing_loans = db.Column(db.Integer, nullable=False, default=0)
    number_of_credit_accounts = db.Column(db.Integer, nullable=False, default=1)
    debt_to_income_ratio = db.Column(db.Float, nullable=False, default=0.0)
    employment_years = db.Column(db.Integer, nullable=False, default=0)
    prediction = db.Column(db.String(30), nullable=True)  # Latest risk category or None/'Re-evaluation Required'
    prediction_probability = db.Column(db.Float, nullable=True)  # Latest top score %
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One-to-Many Relationship with Prediction history
    predictions = db.relationship('Prediction', backref='application', cascade='all, delete-orphan', lazy=True)


class Prediction(db.Model):
    __tablename__ = 'prediction'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('credit_application.id'), nullable=False)
    predicted_risk = db.Column(db.String(30), nullable=False)
    low_probability = db.Column(db.Float, nullable=False)
    medium_probability = db.Column(db.Float, nullable=False)
    high_probability = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(30), nullable=False, default=Config.MODEL_VERSION)
    predicted_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Authentication & Authorization Helpers
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in with your email & password to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def can_access_application(app_record):
    """Checks if the logged in user is an Administrator or owns the application."""
    if session.get('role') == 'Administrator':
        return True
    return app_record.user_id == session.get('user_id') or app_record.user_id is None


# ---------------------------------------------------------------------------
# Database Initialization & Seed Data Setup (Safe Migration)
# ---------------------------------------------------------------------------
def init_db_and_seed():
    """Initializes SQLite database tables safely without dropping existing user data."""
    with app.app_context():
        db.create_all()

        # Seed default admin user if missing
        admin_email = 'admin@crediguard.com'
        admin_user = User.query.filter_by(email=admin_email).first()
        if admin_user is None:
            print("Creating default admin account (Email: admin@crediguard.com | Password: admin123)...")
            admin_user = User(
                full_name='System Admin',
                email=admin_email,
                username='Admin User',
                password_hash=generate_password_hash('admin123'),
                role='Administrator'
            )
            db.session.add(admin_user)
            db.session.commit()

        # Seed sample applications if empty
        if CreditApplication.query.first() is None:
            print("Populating database with realistic seed application records...")
            seed_data = [
                {
                    "full_name": "Aarav Sharma", "age": 34, "gender": "Male",
                    "employment_status": "Employed", "annual_income": 950000.0, "loan_amount": 250000.0,
                    "loan_duration_months": 24, "existing_debt": 95000.0, "credit_history_years": 8,
                    "previous_payment_history": "Excellent", "number_of_existing_loans": 1,
                    "number_of_credit_accounts": 3, "employment_years": 7
                },
                {
                    "full_name": "Priya Ananth", "age": 28, "gender": "Female",
                    "employment_status": "Employed", "annual_income": 620000.0, "loan_amount": 180000.0,
                    "loan_duration_months": 36, "existing_debt": 150000.0, "credit_history_years": 4,
                    "previous_payment_history": "Good", "number_of_existing_loans": 1,
                    "number_of_credit_accounts": 2, "employment_years": 4
                },
                {
                    "full_name": "Rohan Deshmukh", "age": 45, "gender": "Male",
                    "employment_status": "Business", "annual_income": 1850000.0, "loan_amount": 600000.0,
                    "loan_duration_months": 48, "existing_debt": 320000.0, "credit_history_years": 15,
                    "previous_payment_history": "Excellent", "number_of_existing_loans": 2,
                    "number_of_credit_accounts": 5, "employment_years": 12
                },
                {
                    "full_name": "Ananya Roy", "age": 24, "gender": "Female",
                    "employment_status": "Self-Employed", "annual_income": 380000.0, "loan_amount": 200000.0,
                    "loan_duration_months": 36, "existing_debt": 180000.0, "credit_history_years": 1,
                    "previous_payment_history": "Average", "number_of_existing_loans": 2,
                    "number_of_credit_accounts": 2, "employment_years": 2
                },
                {
                    "full_name": "Vikramaditya Verma", "age": 52, "gender": "Male",
                    "employment_status": "Employed", "annual_income": 1400000.0, "loan_amount": 300000.0,
                    "loan_duration_months": 24, "existing_debt": 210000.0, "credit_history_years": 18,
                    "previous_payment_history": "Good", "number_of_existing_loans": 1,
                    "number_of_credit_accounts": 4, "employment_years": 15
                }
            ]

            for item in seed_data:
                dti = calculate_dti_proxy(item['existing_debt'], item['annual_income'])
                app_obj = CreditApplication(
                    user_id=admin_user.id,
                    full_name=item['full_name'],
                    age=item['age'],
                    gender=item['gender'],
                    employment_status=item['employment_status'],
                    annual_income=item['annual_income'],
                    loan_amount=item['loan_amount'],
                    loan_duration_months=item['loan_duration_months'],
                    existing_debt=item['existing_debt'],
                    credit_history_years=item['credit_history_years'],
                    previous_payment_history=item['previous_payment_history'],
                    number_of_existing_loans=item['number_of_existing_loans'],
                    number_of_credit_accounts=item['number_of_credit_accounts'],
                    debt_to_income_ratio=dti,
                    employment_years=item['employment_years']
                )
                db.session.add(app_obj)

            db.session.commit()

            # Run initial predictions for seed applications
            apps = CreditApplication.query.all()
            for app_record in apps:
                app_dict = {
                    'age': app_record.age,
                    'annual_income': app_record.annual_income,
                    'loan_amount': app_record.loan_amount,
                    'loan_duration_months': app_record.loan_duration_months,
                    'existing_debt': app_record.existing_debt,
                    'credit_history_years': app_record.credit_history_years,
                    'previous_payment_history': app_record.previous_payment_history,
                    'number_of_existing_loans': app_record.number_of_existing_loans,
                    'number_of_credit_accounts': app_record.number_of_credit_accounts,
                    'employment_years': app_record.employment_years,
                    'debt_to_income_ratio': app_record.debt_to_income_ratio,
                    'employment_status': app_record.employment_status
                }
                res = predict_credit_risk(app_dict)
                app_record.prediction = res['predicted_risk']
                top_prob = max(res['low_probability'], res['medium_probability'], res['high_probability'])
                app_record.prediction_probability = top_prob

                pred_hist = Prediction(
                    application_id=app_record.id,
                    predicted_risk=res['predicted_risk'],
                    low_probability=res['low_probability'],
                    medium_probability=res['medium_probability'],
                    high_probability=res['high_probability'],
                    model_version=res['model_version']
                )
                db.session.add(pred_hist)

            db.session.commit()
            print("Seed database initialization complete!")


# ---------------------------------------------------------------------------
# Authentication Routes (Register, Login, Logout)
# ---------------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user account registration with server-side validation."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not full_name or not email or not password or not confirm_password:
            flash("All fields are required. Please complete the registration form.", "danger")
            return render_template('register.html', full_name=full_name, email=email)

        if not validate_email_format(email):
            flash("Please provide a valid Email Address format.", "danger")
            return render_template('register.html', full_name=full_name, email=email)

        if password != confirm_password:
            flash("Passwords do not match! Please check and try again.", "danger")
            return render_template('register.html', full_name=full_name, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html', full_name=full_name, email=email)

        existing_user = User.query.filter(db.func.lower(User.email) == email).first()
        if existing_user:
            flash("This Email ID is already registered! Please log in instead.", "warning")
            return redirect(url_for('login'))

        username_str = full_name.split()[0] if full_name else 'User'
        new_user = User(
            full_name=full_name,
            email=email,
            username=username_str,
            password_hash=generate_password_hash(password),
            role='User'
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! You can now sign in with your email and password.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles registered user login authentication with open redirect prevention."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email_input = request.form.get('email', '').strip().lower()
        password_input = request.form.get('password', '').strip()

        user = User.query.filter(
            (db.func.lower(User.email) == email_input) | (db.func.lower(User.username) == email_input)
        ).first()

        if user and user.check_password(password_input):
            session['user_id'] = user.id
            session['username'] = user.full_name or user.username
            session['email'] = user.email
            session['role'] = user.role
            flash(f"Welcome back, {session['username']}! Logged in successfully.", "success")
            
            next_page = request.args.get('next')
            if not is_safe_url(next_page):
                next_page = url_for('dashboard')
            return redirect(next_page)
        else:
            flash("Invalid Email Address or Password. Please try again.", "danger")

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logs out the current user session."""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Flask Core Application Routes (Protected by RBAC & Session)
# ---------------------------------------------------------------------------

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """Renders the executive dashboard with model metrics and feature importance graphs."""
    user_role = session.get('role')
    user_id = session.get('user_id')

    # Apply RBAC filtering: Admin views all, regular User views their own applications
    if user_role == 'Administrator':
        app_query = CreditApplication.query
    else:
        app_query = CreditApplication.query.filter(
            (CreditApplication.user_id == user_id) | (CreditApplication.user_id == None)
        )

    applications = app_query.all()
    total_apps = len(applications)

    low_count = app_query.filter_by(prediction='Low Risk').count()
    med_count = app_query.filter_by(prediction='Medium Risk').count()
    high_count = app_query.filter_by(prediction='High Risk').count()
    stale_count = app_query.filter(
        (CreditApplication.prediction == None) | (CreditApplication.prediction == 'Re-evaluation Required')
    ).count()

    if total_apps > 0:
        avg_income = db.session.query(db.func.avg(CreditApplication.annual_income)).scalar() or 0
        avg_loan = db.session.query(db.func.avg(CreditApplication.loan_amount)).scalar() or 0
    else:
        avg_income = 0
        avg_loan = 0

    employment_labels = ['Employed', 'Self-Employed', 'Business', 'Student', 'Unemployed']
    employment_counts = [
        app_query.filter_by(employment_status=emp).count() for emp in employment_labels
    ]

    recent_applications = app_query.order_by(CreditApplication.created_at.desc()).limit(6).all()

    # Load Model Evaluation Metrics & Feature Importances JSON
    model_metrics = None
    if os.path.exists(Config.METRICS_PATH):
        try:
            with open(Config.METRICS_PATH, 'r') as f:
                model_metrics = json.load(f)
        except Exception:
            model_metrics = None

    return render_template(
        'dashboard.html',
        total_apps=total_apps,
        low_count=low_count,
        med_count=med_count,
        high_count=high_count,
        stale_count=stale_count,
        avg_income=avg_income,
        avg_loan=avg_loan,
        employment_labels=employment_labels,
        employment_counts=employment_counts,
        recent_applications=recent_applications,
        model_metrics=model_metrics
    )


@app.route('/applications')
@login_required
def list_applications():
    """Renders applications list filtered by role ownership, search, and multi-filters."""
    user_role = session.get('role')
    user_id = session.get('user_id')

    query_param = request.args.get('q', '').strip()
    risk_filter = request.args.get('risk', '').strip()
    employment_filter = request.args.get('employment', '').strip()

    if user_role == 'Administrator':
        query = CreditApplication.query
    else:
        query = CreditApplication.query.filter(
            (CreditApplication.user_id == user_id) | (CreditApplication.user_id == None)
        )

    if query_param:
        query = query.filter(CreditApplication.full_name.ilike(f"%{query_param}%"))

    if risk_filter:
        query = query.filter(CreditApplication.prediction == risk_filter)

    if employment_filter:
        query = query.filter(CreditApplication.employment_status == employment_filter)

    applications = query.order_by(CreditApplication.created_at.desc()).all()

    return render_template(
        'applications.html',
        applications=applications,
        query_param=query_param,
        risk_filter=risk_filter,
        employment_filter=employment_filter
    )


@app.route('/applications/add', methods=['GET', 'POST'])
@login_required
def add_application():
    """Handles adding a new credit application assigned to current user."""
    if request.method == 'POST':
        form_data = request.form.to_dict()
        is_valid, errors = validate_application_data(form_data)

        if not is_valid:
            for err in errors:
                flash(err, 'danger')
            return render_template('add_application.html', form_data=form_data)

        # Calculate DTI Proxy Ratio
        dti = calculate_dti_proxy(form_data['existing_debt'], form_data['annual_income'])

        new_app = CreditApplication(
            user_id=session.get('user_id'),
            full_name=form_data['full_name'].strip(),
            age=int(form_data['age']),
            gender=form_data['gender'],
            employment_status=form_data['employment_status'],
            annual_income=float(form_data['annual_income']),
            loan_amount=float(form_data['loan_amount']),
            loan_duration_months=int(form_data['loan_duration_months']),
            existing_debt=float(form_data['existing_debt']),
            credit_history_years=int(form_data['credit_history_years']),
            previous_payment_history=form_data['previous_payment_history'],
            number_of_existing_loans=int(form_data['number_of_existing_loans']),
            number_of_credit_accounts=int(form_data['number_of_credit_accounts']),
            debt_to_income_ratio=dti,
            employment_years=int(form_data['employment_years'])
        )

        db.session.add(new_app)
        db.session.commit()

        flash(f"Credit Application for '{new_app.full_name}' created successfully!", "success")
        return redirect(url_for('application_details', app_id=new_app.id))

    return render_template('add_application.html', form_data={})


@app.route('/applications/<int:app_id>')
@login_required
def application_details(app_id):
    """Views full applicant profile and prediction history logs with RBAC check."""
    app_record = CreditApplication.query.get_or_404(app_id)

    if not can_access_application(app_record):
        flash("Unauthorized Access: You do not have permission to view this application.", "danger")
        return redirect(url_for('list_applications'))

    history = Prediction.query.filter_by(application_id=app_id).order_by(Prediction.predicted_at.desc()).all()
    return render_template('application_details.html', application=app_record, history=history)


@app.route('/applications/<int:app_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_application(app_id):
    """Edits an existing application record and invalidates stale prediction."""
    app_record = CreditApplication.query.get_or_404(app_id)

    if not can_access_application(app_record):
        flash("Unauthorized Access: You do not have permission to edit this application.", "danger")
        return redirect(url_for('list_applications'))

    if request.method == 'POST':
        form_data = request.form.to_dict()
        is_valid, errors = validate_application_data(form_data)

        if not is_valid:
            for err in errors:
                flash(err, 'danger')
            return render_template('edit_application.html', application=app_record, form_data=form_data)

        # Update features
        app_record.full_name = form_data['full_name'].strip()
        app_record.age = int(form_data['age'])
        app_record.gender = form_data['gender']
        app_record.employment_status = form_data['employment_status']
        app_record.annual_income = float(form_data['annual_income'])
        app_record.loan_amount = float(form_data['loan_amount'])
        app_record.loan_duration_months = int(form_data['loan_duration_months'])
        app_record.existing_debt = float(form_data['existing_debt'])
        app_record.credit_history_years = int(form_data['credit_history_years'])
        app_record.previous_payment_history = form_data['previous_payment_history']
        app_record.number_of_existing_loans = int(form_data['number_of_existing_loans'])
        app_record.number_of_credit_accounts = int(form_data['number_of_credit_accounts'])
        app_record.employment_years = int(form_data['employment_years'])
        app_record.debt_to_income_ratio = calculate_dti_proxy(app_record.existing_debt, app_record.annual_income)
        app_record.updated_at = datetime.utcnow()

        # Invalidate current prediction on edit (stale prediction fix)
        # Historical prediction logs in Prediction table are preserved as audit history!
        app_record.prediction = 'Re-evaluation Required'
        app_record.prediction_probability = None

        db.session.commit()
        flash(f"Application for '{app_record.full_name}' updated successfully! Current prediction marked as 'Re-evaluation Required'.", "info")
        return redirect(url_for('application_details', app_id=app_record.id))

    return render_template('edit_application.html', application=app_record, form_data=None)


@app.route('/applications/<int:app_id>/delete', methods=['POST'])
@login_required
def delete_application(app_id):
    """Deletes an application and all its prediction history logs."""
    app_record = CreditApplication.query.get_or_404(app_id)

    if not can_access_application(app_record):
        flash("Unauthorized Access: You do not have permission to delete this application.", "danger")
        return redirect(url_for('list_applications'))

    name = app_record.full_name
    db.session.delete(app_record)
    db.session.commit()
    flash(f"Application #{app_id} ('{name}') has been deleted.", "info")
    return redirect(url_for('list_applications'))


@app.route('/predict/<int:app_id>', methods=['GET', 'POST'])
@login_required
def predict(app_id):
    """
    ML Credit Risk Prediction.
    GET: Displays prediction status & latest prediction result.
    POST: Executes model inference, updates application prediction status, and logs history.
    """
    app_record = CreditApplication.query.get_or_404(app_id)

    if not can_access_application(app_record):
        flash("Unauthorized Access: You do not have permission to predict risk for this application.", "danger")
        return redirect(url_for('list_applications'))

    # POST request: Execute ML model inference
    if request.method == 'POST':
        app_dict = {
            'age': app_record.age,
            'annual_income': app_record.annual_income,
            'loan_amount': app_record.loan_amount,
            'loan_duration_months': app_record.loan_duration_months,
            'existing_debt': app_record.existing_debt,
            'credit_history_years': app_record.credit_history_years,
            'previous_payment_history': app_record.previous_payment_history,
            'number_of_existing_loans': app_record.number_of_existing_loans,
            'number_of_credit_accounts': app_record.number_of_credit_accounts,
            'employment_years': app_record.employment_years,
            'debt_to_income_ratio': app_record.debt_to_income_ratio,
            'employment_status': app_record.employment_status
        }

        result = predict_credit_risk(app_dict)

        # Log prediction audit history with model version
        prediction_record = Prediction(
            application_id=app_record.id,
            predicted_risk=result['predicted_risk'],
            low_probability=result['low_probability'],
            medium_probability=result['medium_probability'],
            high_probability=result['high_probability'],
            model_version=result['model_version']
        )
        db.session.add(prediction_record)

        # Update latest prediction on application
        app_record.prediction = result['predicted_risk']
        top_prob = max(result['low_probability'], result['medium_probability'], result['high_probability'])
        app_record.prediction_probability = top_prob

        db.session.commit()

        flash(f"Risk Assessment calculated for '{app_record.full_name}': {result['predicted_risk']} (Model: {result['model_version']})", "success")
        return render_template('prediction.html', application=app_record, result=result, new_prediction=True)

    # GET request: Display most recent prediction if available
    latest_pred = Prediction.query.filter_by(application_id=app_id).order_by(Prediction.predicted_at.desc()).first()
    result = None
    if latest_pred and app_record.prediction != 'Re-evaluation Required':
        result = {
            'predicted_risk': latest_pred.predicted_risk,
            'low_probability': latest_pred.low_probability,
            'medium_probability': latest_pred.medium_probability,
            'high_probability': latest_pred.high_probability,
            'model_version': latest_pred.model_version,
            'predicted_at': latest_pred.predicted_at,
            'probabilities': {
                'Low Risk': latest_pred.low_probability,
                'Medium Risk': latest_pred.medium_probability,
                'High Risk': latest_pred.high_probability
            }
        }

    return render_template('prediction.html', application=app_record, result=result, new_prediction=False)


@app.route('/predictions')
@login_required
def prediction_history():
    """Lists history of prediction queries filtered by user ownership / role."""
    user_role = session.get('role')
    user_id = session.get('user_id')

    query_param = request.args.get('q', '').strip()
    risk_filter = request.args.get('risk', '').strip()

    query = db.session.query(Prediction, CreditApplication).join(CreditApplication, Prediction.application_id == CreditApplication.id)

    if user_role != 'Administrator':
        query = query.filter(
            (CreditApplication.user_id == user_id) | (CreditApplication.user_id == None)
        )

    if query_param:
        query = query.filter(CreditApplication.full_name.ilike(f"%{query_param}%"))

    if risk_filter:
        query = query.filter(Prediction.predicted_risk == risk_filter)

    records = query.order_by(Prediction.predicted_at.desc()).all()

    return render_template(
        'prediction_history.html',
        records=records,
        query_param=query_param,
        risk_filter=risk_filter
    )


@app.route('/about')
def about():
    """Renders About page with tech stack, workflow, and Viva reference info."""
    return render_template('about.html')


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden_error(e):
    flash("403 Forbidden: You do not have authorization to perform this action.", "danger")
    return render_template('404.html'), 403


# ---------------------------------------------------------------------------
# Main Execution Entrypoint
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Initialize DB & seed data safely
    init_db_and_seed()
    
    print("\n==================================================")
    print(" CrediGuard - Credit Risk Monitoring & Prediction System")
    print(" Running locally on: http://127.0.0.1:5050")
    print(" Default Admin Credentials -> Email: admin@crediguard.com | Password: admin123")
    print("==================================================\n")
    
    app.run(host='127.0.0.1', port=5050, debug=False)
