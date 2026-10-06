import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Flask configuration settings for CrediGuard application."""
    # Secret key loaded from environment variable with documented local development fallback
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'crediguard-dev-secret-key-change-for-production-use'
    
    # SQLite Database configuration
    DB_DIR = os.path.join(BASE_DIR, 'database')
    os.makedirs(DB_DIR, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DB_DIR, 'credit_risk.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Machine Learning Model & Data Paths
    MODEL_DIR = os.path.join(BASE_DIR, 'models')
    os.makedirs(MODEL_DIR, exist_ok=True)
    MODEL_PATH = os.path.join(MODEL_DIR, 'credit_risk_model.pkl')
    METRICS_PATH = os.path.join(MODEL_DIR, 'model_metrics.json')

    DATA_DIR = os.path.join(BASE_DIR, 'data')
    os.makedirs(DATA_DIR, exist_ok=True)
    DATASET_PATH = os.path.join(DATA_DIR, 'credit_data.csv')

    # Model Version constant
    MODEL_VERSION = 'RandomForest-v1.1'
