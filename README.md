# CrediGuard – Credit Risk Monitoring & Prediction System

> **B.Tech AI & Data Science Mini Project 2**  
> A complete, beginner-friendly full-stack web application combining CRUD operations, SQLite database, Flask backend, CSRF protection, Role-Based Access Control (RBAC), interactive Chart.js dashboards, and a Machine Learning classification model (`RandomForestClassifier`).

---

## 📌 Project Overview

**CrediGuard** provides financial institutions, risk analysts, and administrators with an automated decision-support interface. It allows users to register accounts, manage applicant profiles with ownership privacy, automatically calculate Debt-to-Income (DTI) Proxy ratios, and run real-time Machine Learning risk predictions (`LOW RISK`, `MEDIUM RISK`, `HIGH RISK`).

### Key System Improvements (V1.1 Audit):
- **Role-Based Access Control (RBAC)**: Supports `User` and `Administrator` roles with strict record isolation.
- **CSRF Security**: Built-in zero-dependency CSRF token verification across all HTML forms.
- **Stale Prediction Invalidation**: Editing applicant data automatically marks prediction status as `'Re-evaluation Required'` while preserving historical audit logs.
- **Model Versioning & Metrics**: Model version `RandomForest-v1.1` stored in DB logs and metric JSON (`models/model_metrics.json`).
- **Comprehensive Test Suite**: Automated unit tests running on isolated in-memory SQLite DB (`test_app.py`).

---

## ✨ Core Features

- **Authentication & RBAC**: Account Registration, Email-based Login, and Role-based Authorization (`Administrator` vs `User`).
- **Full CRUD Management**: Add, View, Edit, and Delete applicant profiles with ownership controls.
- **Automated DTI Proxy Calculation**: Real-time Debt-to-Income calculation:
  $$\text{DTI Proxy} = \left(\frac{\text{Existing Debt}}{\text{Annual Income}}\right) \times 100$$
- **Machine Learning Risk Classification**: Random Forest Classifier pipeline (`scikit-learn 1.4.2`) trained with fixed random seed (`random_state=42`).
- **Probability Breakdown & Version Badge**: Class probability percentages (Low, Medium, High Risk) alongside model version tag (`RandomForest-v1.1`).
- **Executive Analytics Dashboard**: KPI summary cards (Total Applications, Risk counts, Stale count, Avg Income/Loan), Model Evaluation Metrics banner, and interactive Chart.js visualizations (Risk Distribution, Employment Status, and Feature Importance drivers).
- **Search & Multi-Filtering**: Instant search by applicant name and filter by Risk level and Employment type.
- **Prediction History Audit Log**: Detailed historical log of all ML inferences executed per application.
- **Error Handling & Input Validation**: Robust validation rules (age 18–100, positive income/loan, non-negative debt, email formatting) with custom error pages.
- **Automatic Safe Seed Data**: Database initializes safely on first run with 15 pre-configured realistic application records and prediction logs.

---

## 🛠️ Technology Stack

| Component | Technologies Used |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, Bootstrap 5, Vanilla JavaScript, Chart.js, FontAwesome |
| **Backend** | Python 3.10+, Flask 3.0.2 |
| **Database** | SQLite, Flask-SQLAlchemy 3.1.1 ORM |
| **Machine Learning** | Scikit-Learn 1.4.2 (`RandomForestClassifier`), Pandas 2.2.2, NumPy 1.26.4, Joblib 1.4.0 |
| **Testing** | Pytest 8.1.1 / Standard Python Unittest |

---

## 📂 Project Folder Structure

```text
credit-risk-predictor/
│
├── app.py                     # Main Flask application, routes, RBAC & DB initialization
├── config.py                  # Environment, metrics path & model version configuration
├── test_app.py                # Automated comprehensive test suite (In-memory SQLite DB)
├── requirements.txt           # Explicitly pinned Python dependencies
├── README.md                  # Complete documentation & Viva Q&A guide
│
├── data/
│   └── credit_data.csv        # Synthetic training dataset (1000 records)
│
├── database/
│   └── credit_risk.db         # SQLite database (auto-created on app start)
│
├── ml/
│   ├── train_model.py         # ML model training & metrics JSON exporter script
│   └── predict.py             # Inference helper loading trained model .pkl
│
├── models/
│   ├── credit_risk_model.pkl  # Serialized Scikit-Learn Random Forest pipeline
│   └── model_metrics.json     # Model evaluation metrics & feature importances
│
├── utils/
│   └── helpers.py             # DTI calculator, email validation & form validation rules
│
├── templates/
│   ├── base.html              # Base layout, dynamic navbar & alert messages
│   ├── login.html             # Secure Email/Password Login view
│   ├── register.html          # User Account Registration view
│   ├── dashboard.html         # Executive overview with KPI cards, metrics banner & Chart.js graphs
│   ├── applications.html      # CRUD list table with search & multi-filters
│   ├── add_application.html   # Form for creating new credit application
│   ├── edit_application.html  # Pre-filled edit form
│   ├── application_details.html # Detailed profile cards & history
│   ├── prediction.html        # ML Risk Prediction execution view
│   ├── prediction_history.html # Full prediction audit logs table with model versioning
│   ├── about.html             # System explanation & viva guide
│   ├── 404.html               # Custom 404 Not Found error page
│   └── 500.html               # Custom 500 Internal Error page
│
└── static/
    ├── css/
    │   └── style.css          # Custom styling, dark navbar & risk badges
    └── js/
        └── script.js          # DTI auto-calculator, delete dialogs & Chart.js code
```

---

## 🚀 Installation & Setup Guide (Windows)

Follow these exact commands in Command Prompt (`cmd`) or PowerShell:

### 1. Open Terminal & Navigate to Project Folder
```cmd
cd C:\Users\LENOVO\.gemini\antigravity\scratch\credit-risk-predictor
```

### 2. Create Virtual Environment
```cmd
python -m venv venv
```

### 3. Activate Virtual Environment
```cmd
venv\Scripts\activate
```

### 4. Install Pinned Dependencies
```cmd
pip install -r requirements.txt
```

### 5. Train Machine Learning Model & Generate Metrics
```cmd
python ml\train_model.py
```
*Outputs accuracy, precision, recall, F1 score and saves `models/credit_risk_model.pkl` and `models/model_metrics.json`.*

### 6. Run Automated Test Suite
```cmd
python test_app.py
```
*Executes all test cases on an isolated in-memory database to verify Auth, RBAC, Validation, and ML inference.*

### 7. Start Flask Web Application
```cmd
python app.py
```

### 8. Access Website
Open your browser and visit:
```text
http://127.0.0.1:5050
```
- **Default Administrator Credentials**: `email: admin@crediguard.com` | `password: admin123`

---

## 🗄️ Database Schema Explanation

### 1. `User` Table
- `id` (INTEGER, Primary Key, Auto-increment)
- `full_name` (VARCHAR, Default: 'User')
- `email` (VARCHAR, Unique, Nullable=False)
- `username` (VARCHAR, Nullable=True)
- `password_hash` (VARCHAR, Encrypted via Werkzeug werkzeug.security)
- `role` (VARCHAR, 'Administrator' or 'User')
- `created_at` (DATETIME)

### 2. `CreditApplication` Table
- `id` (INTEGER, Primary Key, Auto-increment)
- `user_id` (INTEGER, Foreign Key -> `user.id`, Ownership isolation)
- `full_name` (VARCHAR)
- `age` (INTEGER, 18–100)
- `gender` (VARCHAR: Male, Female, Other)
- `employment_status` (VARCHAR: Employed, Self-Employed, Business, Student, Unemployed)
- `annual_income` (FLOAT, > 0)
- `loan_amount` (FLOAT, > 0)
- `loan_duration_months` (INTEGER, > 0)
- `existing_debt` (FLOAT, >= 0)
- `credit_history_years` (INTEGER, >= 0)
- `previous_payment_history` (VARCHAR: Excellent, Good, Average, Poor)
- `number_of_existing_loans` (INTEGER, >= 0)
- `number_of_credit_accounts` (INTEGER, >= 0)
- `debt_to_income_ratio` (FLOAT, Calculated DTI Proxy %)
- `employment_years` (INTEGER, >= 0)
- `prediction` (VARCHAR: Low Risk, Medium Risk, High Risk, or 'Re-evaluation Required')
- `prediction_probability` (FLOAT: Top score %)
- `created_at` / `updated_at` (DATETIME)

### 3. `Prediction` Table (One-to-Many Audit History)
- `id` (INTEGER, Primary Key)
- `application_id` (INTEGER, Foreign Key -> `credit_application.id`)
- `predicted_risk` (VARCHAR: Low Risk, Medium Risk, High Risk)
- `low_probability` (FLOAT)
- `medium_probability` (FLOAT)
- `high_probability` (FLOAT)
- `model_version` (VARCHAR, e.g. 'RandomForest-v1.1')
- `predicted_at` (DATETIME)

---

## 🤖 Machine Learning Workflow

```text
[Input Data] ──> [Validation & DTI Proxy] ──> [Scikit-Learn Pipeline]
                                                     │
                                                     ▼
[SQLite DB Audit Log] <── [Probability UI] <── [Random Forest (.pkl)]
```

1. **Synthetic Training Dataset**: `data/credit_data.csv` contains 1,000 synthetic records with realistic financial parameters.
2. **Reproducible Pipeline**: `ColumnTransformer` applies `OneHotEncoder` to categorical features (`employment_status`, `previous_payment_history`) while scaling/passing numerical attributes with `random_state=42`.
3. **Random Forest Classifier**: Trained with 120 decision trees (`n_estimators=120`, `max_depth=12`).
4. **Metrics Export**: Saves model accuracy, precision, recall, F1 score, and feature importances to `models/model_metrics.json`.

---

## 🎓 Viva Questions & Model Answers

### Q1: What is the main objective of CrediGuard?
**Answer:** CrediGuard is a full-stack educational credit risk decision-support web application. It combines user authentication and RBAC application management with a Random Forest classification model to estimate applicant default risk (`Low Risk`, `Medium Risk`, `High Risk`) along with probability distributions and audit logging.

### Q2: How is Role-Based Access Control (RBAC) implemented?
**Answer:** Each `CreditApplication` record maintains a `user_id` foreign key referencing the `User` table. Regular users can only view, edit, and predict risk for their own applications. Administrators have global permission to inspect all applications across the enterprise.

### Q3: Why did you pin `scikit-learn==1.4.2` in `requirements.txt`?
**Answer:** Serialized Python ML models (`.pkl` files) generated via `joblib` are sensitive to scikit-learn version differences. Pinning `scikit-learn==1.4.2` guarantees reproducible model loading across different machines without serialization errors.

### Q4: How are stale predictions handled when an applicant's financial details change?
**Answer:** When an applicant's data is updated (e.g. debt or income changes), the latest prediction status on the application is automatically set to `'Re-evaluation Required'` and top probability is reset to `None`. However, all historical records in the `Prediction` audit log remain untouched to preserve regulatory audit trails.

### Q5: How is CSRF protection implemented without adding third-party dependencies?
**Answer:** A session-based CSRF token is generated via Python's built-in `secrets` module (`generate_csrf_token()`) and injected into templates using `@app.context_processor`. An `@app.before_request` hook validates `csrf_token` on all incoming HTTP POST requests.

### Q6: What algorithm is used for credit risk prediction, and why?
**Answer:** We used **Random Forest Classifier** from `scikit-learn`. Random Forest is an ensemble learning method combining multiple decision trees. It handles mixed numerical and categorical data cleanly, prevents overfitting through bagging, and produces calibrated probability estimates.

### Q7: How is Debt-to-Income (DTI) Proxy calculated?
**Answer:** DTI Proxy is calculated as:
$$\text{DTI Proxy} = \left(\frac{\text{Existing Debt}}{\text{Annual Income}}\right) \times 100$$
Division-by-zero safeguards return `0.0%` if income is zero or negative.

### Q8: What feature drivers contribute most to the risk prediction?
**Answer:** Feature importances extracted from the trained Random Forest model highlight **Previous Payment History** (~21.5%) and **Debt-to-Income (DTI) Proxy** (~15.4%) as the strongest indicators of default risk.

### Q9: How is automated unit testing handled?
**Answer:** `test_app.py` executes unit tests against an isolated, in-memory SQLite database (`sqlite:///:memory:`). It validates User Registration, Email Login, RBAC Authorization, Form Input Validation, DTI Calculation, ML Inference, and Stale Invalidation without corrupting the production database.

### Q10: Why is an educational disclaimer required?
**Answer:** Real-world credit decisioning systems require regulatory compliance (e.g. FCRA, ECOA), credit bureau integration, and extensive validation on real borrower histories. The disclaimer clarifies that CrediGuard uses synthetic data strictly for academic demonstration.
