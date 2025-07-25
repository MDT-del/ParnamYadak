# config.py
# Configuration file for ParnamYadak project

import os
import secrets
import warnings

# Base directory path
basedir = os.path.abspath(os.path.dirname(__file__))


def get_secure_secret_key():
    """
    Generate or get secure secret key
    """
    secret_key = os.environ.get('SECRET_KEY')
    
    if not secret_key:
        # Security warning if SECRET_KEY is not set
        warnings.warn(
            "SECRET_KEY environment variable is not set! "
            "This is a security risk in production. "
            "Please set a strong SECRET_KEY in your environment variables.",
            UserWarning,
            stacklevel=2
        )
        
        # Generate stronger key for development
        secret_key = secrets.token_urlsafe(64)  # 64 bytes = 512 bits
        
        # Save to temporary file for consistency in development
        secret_file = os.path.join(basedir, '.secret_key')
        if os.path.exists(secret_file):
            with open(secret_file, 'r') as f:
                secret_key = f.read().strip()
        else:
            with open(secret_file, 'w') as f:
                f.write(secret_key)
    
    return secret_key


class Config:
    """
    Main application configuration class
    """
    # Security key for forms and sessions protection
    SECRET_KEY = get_secure_secret_key()

    # Advanced CSRF security settings
    WTF_CSRF_TIME_LIMIT = 1800  # 30 minutes (reduced from 1 hour)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SSL_STRICT = True
    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Session security settings
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes (reduced from 1 hour)
    
    # Additional security settings
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload size

    # SQLAlchemy settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')

    # Database security settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Rate Limiter settings
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL')

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}