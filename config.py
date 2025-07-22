# ---------------------------------------------
# فایل: config.py
# توضیح: این فایل شامل تنظیمات و پیکربندی اصلی اپلیکیشن است.
# ---------------------------------------------

import os
import secrets

# مسیر اصلی پروژه را پیدا می‌کند
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    کلاس تنظیمات اصلی اپلیکیشن
    """
    # کلید امنیتی برای محافظت از فرم‌ها و سشن‌ها
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # تنظیمات امنیتی اضافی
    WTF_CSRF_TIME_LIMIT = 3600  # محدودیت زمانی CSRF (1 ساعت)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # مدت زمان نشست (1 ساعت)

    # تنظیمات امنیتی Flask
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SSL_STRICT = True

    # این گزینه برای جلوگیری از هشدارهای غیرضروری SQLAlchemy است
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # اینجا مهم است:
    # به صورت پیش‌فرض از دیتابیس SQLite به نام app.db استفاده می‌کند.
    # اما اگر بعداً متغیر DATABASE_URL را (مثلاً برای سرور نهایی) تعریف کنید،
    # به صورت خودکار از آن استفاده خواهد کرد.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')

    # تنظیمات امنیتی دیتابیس
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # استفاده از دیتابیس در حافظه
    WTF_CSRF_ENABLED = False  # غیرفعال کردن CSRF برای تست فرم‌ها
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    # تنظیمات برای محیط نهایی
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True

    # تنظیمات logging برای production
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')

    # تنظیمات امنیتی اضافی برای production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
