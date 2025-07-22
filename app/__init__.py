# ---------------------------------------------
# فایل: __init__.py
# توضیح: راه‌اندازی و پیکربندی اپلیکیشن، ثبت بلوپرینت‌ها، مدیریت نشست و لایسنس
# ---------------------------------------------

from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config, config
import jdatetime
import logging
from logging.handlers import RotatingFileHandler
import os
from app.utils import create_database_backup
from apscheduler.schedulers.background import BackgroundScheduler
from persiantools.jdatetime import JalaliDateTime
from app.utils import register_jinja_filters
import datetime
import traceback
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from app.utils import digits_to_persian
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# Load environment variables from env_local file
from dotenv import load_dotenv
load_dotenv('env_local')

# --- Sentry integration for error tracking ---
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN)

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "برای دسترسی به این صفحه، لطفاً ابتدا وارد شوید."
login_manager.login_message_category = "info"
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def to_jalali_datetime(value):
    if not value:
        return "-"
    try:
        return JalaliDateTime(value).strftime("%Y/%m/%d %H:%M")
    except Exception:
        return str(value)


def payment_method_fa(method):
    mapping = {
        'bank_transfer': 'انتقال بانکی',
        'cash': 'نقدی',
        'check': 'چک',
        'other': 'سایر',
        None: '-',
        '': '-',
    }
    return mapping.get(method, method)


def format_price_fa(value):
    try:
        value = int(float(value))
        return '{:,}'.format(value)
    except Exception:
        return value


def create_app(config_name='default'):
    """
    تابع ساخت و پیکربندی اپلیکیشن Flask.
    این تابع تمام بلوپرینت‌ها را ثبت و تنظیمات اولیه را انجام می‌دهد.
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # --- امنیت کوکی سشن ---
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    limiter.init_app(app)
    Talisman(app, content_security_policy=None)

    # --- SocketIO event handlers ---
    @socketio.on('connect')
    def handle_connect():
        pass  # اتصال برقرار شد

    @socketio.on('join')
    def on_join(data):
        # data باید شامل user_id یا role_id باشد
        from flask_socketio import join_room
        user_id = data.get('user_id')
        role_id = data.get('role_id')
        if user_id:
            join_room(f'user_{user_id}')
        if role_id:
            join_room(f'role_{role_id}')

    # تنظیم logging برای ثبت لاگ‌ها در حالت production
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/nikaydek.log',
                                           maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('نیکایدک startup')

    @app.template_filter('to_shamsi')
    def to_shamsi(gregorian_date, fmt='%Y/%m/%d'):
        """
        تبدیل تاریخ میلادی به شمسی برای نمایش در قالب‌ها
        پارامتر fmt برای تعیین فرمت خروجی (پیش‌فرض فقط تاریخ، اگر ساعت هم خواستیم باید '%Y/%m/%d - %H:%M' بدهیم)
        همیشه ساعت را به وقت تهران نمایش می‌دهد.
        """
        import pytz
        if gregorian_date is None:
            return ""
        try:
            # اگر datetime باشد، هم تاریخ و هم ساعت را تبدیل کن
            if hasattr(gregorian_date, 'date'):
                # اگر timezone-aware نیست، فرض کن UTC است
                if getattr(gregorian_date, 'tzinfo', None) is None:
                    gregorian_date = gregorian_date.replace(tzinfo=pytz.UTC)
                # تبدیل به تهران
                tehran_tz = pytz.timezone('Asia/Tehran')
                gregorian_date = gregorian_date.astimezone(tehran_tz)
                shamsi_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
            else:
                shamsi_date = jdatetime.date.fromgregorian(date=gregorian_date)
            return shamsi_date.strftime(fmt)
        except Exception as e:
            app.logger.error(f"Error converting date to Shamsi: {e}")
            return str(gregorian_date)

    @app.template_filter('from_json')
    def from_json(json_string):
        """
        تبدیل رشته JSON به آبجکت برای نمایش در قالب‌ها
        """
        if json_string is None:
            return None
        try:
            import json
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError) as e:
            app.logger.error(f"Error parsing JSON: {e}")
            return None

    @app.template_filter('loads')
    def loads_filter(s):
        """
        تبدیل رشته JSON به لیست برای استفاده در قالب‌ها (رفع خطای No filter named 'loads')
        """
        import json
        try:
            return json.loads(s)
        except Exception as e:
            app.logger.error(f"Error in loads filter: {e}")
            return []

    # هندلرهای خطا برای صفحات ۴۰۴، ۵۰۰ و ۴۰۳
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 error: {request.url}")
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 error: {error}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.warning(f"403 error: {request.url}")
        return render_template('errors/403.html'), 403

    @app.errorhandler(400)
    def bad_request_error(error):
        app.logger.warning(f"400 error: {request.url}")
        return render_template('errors/400.html'), 400

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        app.logger.warning(f"HTTP error {error.code}: {request.url}")
        return render_template('errors/generic.html', error=error), error.code

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        app.logger.error(f"Database error: {error}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def handle_generic_error(error):
        app.logger.error(f"Unhandled exception: {error}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return render_template('errors/500.html'), 500

    with app.app_context():
        from . import models

        @login_manager.user_loader
        def load_user(user_id):
            """
            بارگذاری کاربر بر اساس شناسه برای مدیریت نشست
            """
            try:
                return db.session.get(models.User, int(user_id))
            except Exception as e:
                app.logger.error(f"Error loading user {user_id}: {e}")
                return None

        # ثبت تمام بلوپرینت‌های بخش‌های مختلف سیستم
        from .blueprints.auth.routes import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        from .blueprints.dashboard.routes import dashboard_bp
        app.register_blueprint(dashboard_bp, url_prefix='/')
        from .blueprints.inventory import inventory_bp
        app.register_blueprint(inventory_bp, url_prefix='/inventory')
        from .blueprints.orders.routes import orders_bp
        app.register_blueprint(orders_bp, url_prefix='/orders')
        from .blueprints.customers.routes import customers_bp
        app.register_blueprint(customers_bp, url_prefix='/customers')
        from .blueprints.admin_management.routes import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/admins')
        from .blueprints.roles.routes import roles_bp
        app.register_blueprint(roles_bp, url_prefix='/roles')
        from .blueprints.profile.routes import profile_bp
        app.register_blueprint(profile_bp, url_prefix='/profile')
        from .blueprints.instore_orders.routes import instore_orders_bp
        app.register_blueprint(instore_orders_bp, url_prefix='/instore-orders')

        # ثبت Blueprint های جدید
        from .blueprints.financial_reports.routes import financial_reports_bp
        app.register_blueprint(financial_reports_bp,
                               url_prefix='/financial-reports')
        from .blueprints.broadcast.routes import broadcast_bp
        app.register_blueprint(broadcast_bp, url_prefix='/broadcast')
        from .blueprints.mechanics import mechanics_bp
        app.register_blueprint(mechanics_bp, url_prefix='/mechanics')
        from .blueprints.bot_orders import bot_orders_bp
        app.register_blueprint(bot_orders_bp, url_prefix='/bot-orders')
        # از اینجا support_bp را حذف می‌کنم:
        # from .blueprints.support.routes import support_bp
        # app.register_blueprint(support_bp, url_prefix='/support')

        # ثبت Blueprint کارتابل
        from .blueprints.tasks.routes import tasks_bp
        app.register_blueprint(tasks_bp, url_prefix='/tasks')

        # ثبت Blueprint اعلان‌ها
        from .blueprints.notifications.routes import notifications_bp
        app.register_blueprint(notifications_bp, url_prefix='/notifications')

        # ثبت Blueprint لایسنس
        from .blueprints.license.routes import license_bp
        app.register_blueprint(license_bp, url_prefix='/license')

        # ثبت Blueprint ربات تلگرام
        from .blueprints.telegram_bot.routes import telegram_bot_bp
        app.register_blueprint(telegram_bot_bp, url_prefix='/telegram-bot')
        
        # ثبت Blueprint تنظیمات ربات
        from .blueprints.admin_management.bot_settings import bot_settings_bp
        app.register_blueprint(bot_settings_bp, url_prefix='/admin')
        
        # از اینجا bot_messages_bp را حذف می‌کنم:
        # from .blueprints.admin_management.bot_messages import bot_messages_bp
        # app.register_blueprint(bot_messages_bp, url_prefix='/admin')

        # ثبت Blueprint API جدید
        from .blueprints.api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')

        # --- Middleware برای بررسی لایسنس ---
        @app.before_request
        def check_license():
            """
            بررسی فعال بودن لایسنس قبل از هر درخواست (به جز مسیرهای معاف)
            اگر لایسنس فعال نباشد، کاربر به صفحه فعال‌سازی هدایت می‌شود.
            """
            try:
                from .utils import is_license_active

                # مسیرهایی که نیاز به لایسنس ندارند
                exempt_paths = [
                    '/license/activate',
                    '/license/setup',
                    '/static/',
                    '/auth/login',
                    '/auth/logout'
                ]

                # بررسی مسیر فعلی
                current_path = request.path
                is_exempt = any(current_path.startswith(path) for path in exempt_paths)

                # اگر مسیر معاف نیست و لایسنس فعال نیست، به صفحه فعال‌سازی هدایت کن
                if not is_exempt and not is_license_active():
                    return redirect(url_for('license.activate'))
            except Exception as e:
                app.logger.error(f"Error in license check: {e}")
                # در صورت خطا، اجازه دسترسی بده
                pass

        # --- Middleware برای بررسی فعال بودن نشست کاربر ---
        from flask_login import logout_user, current_user
        from app.models import SessionLog
        from flask import session, flash

        @app.before_request
        def check_active_session():
            try:
                # فقط اگر کاربر لاگین است و مسیرهای خاص نباشد
                if current_user.is_authenticated:
                    session_id = session.get('session_id')
                    if session_id:
                        session_log = SessionLog.query.get(session_id)
                        now = datetime.datetime.utcnow()
                        if session_log:
                            # بررسی اتمام خودکار نشست بعد از ۱۵ دقیقه بی‌فعالیتی
                            if session_log.last_activity and (now - session_log.last_activity).total_seconds() > 900:
                                session_log.is_active = False
                                session_log.logout_time = now
                                db.session.commit()
                                logout_user()
                                session.pop('session_id', None)
                                flash('به دلیل عدم فعالیت، نشست شما به پایان رسید. لطفاً مجدداً وارد شوید.', 'warning')
                                return redirect(url_for('auth.login'))
                            # اگر نشست فعال است، last_activity را به‌روزرسانی کن
                            if session_log.is_active:
                                session_log.last_activity = now
                                db.session.commit()
                        if not session_log or not session_log.is_active:
                            logout_user()
                            session.pop('session_id', None)
                            flash('نشست شما توسط مدیر سیستم خاتمه یافته است.', 'warning')
                            return redirect(url_for('auth.login'))
            except Exception as e:
                app.logger.error(f"Error in session check: {e}")
                # در صورت خطا، اجازه دسترسی بده
                pass

        # --- ایجاد مجوزهای پیش‌فرض در دیتابیس ---
        def insert_initial_data():
            """
            ایجاد مجوزها و نقش ادمین پیش‌فرض در دیتابیس در اولین اجرا
            """
            try:
                # لیست تمام مجوزهای سیستم
                permissions = {
                    'view_dashboard': 'مشاهده داشبورد',
                    'manage_products': 'مدیریت کامل محصولات',
                    'manage_categories': 'مدیریت کامل دسته‌بندی‌ها',
                    'manage_orders': 'مدیریت کامل سفارشات',
                    'manage_pre_orders': 'مدیریت کامل پیش‌سفارش‌ها',
                    'manage_customers': 'مدیریت کامل مشتریان',
                    'manage_roles': 'مدیریت کامل نقش‌ها و دسترسی‌ها',
                    'manage_admins': 'مدیریت کامل کاربران پنل',
                    'view_financial_reports': 'مشاهده گزارش‌های مالی',
                    'manage_broadcasts': 'مدیریت پیام‌های همگانی',
                    'manage_support': 'مدیریت تیکت‌های پشتیبانی',
                    'manage_tasks': 'مدیریت کارتابل و وظایف'
                }

                # نقش ادمین را پیدا یا ایجاد کن
                admin_role = models.Role.query.filter_by(name='Admin').first()
                if not admin_role:
                    admin_role = models.Role(
                        name='Admin', description='دسترسی کامل به تمام بخش‌ها')
                    db.session.add(admin_role)

                # چک کردن و اضافه کردن مجوزها
                for perm_name, perm_desc in permissions.items():
                    permission = models.Permission.query.filter_by(
                        name=perm_name).first()
                    if not permission:
                        permission = models.Permission(name=perm_name,
                                                       description=perm_desc)
                        db.session.add(permission)
                    # افزودن تمام مجوزها به نقش ادمین
                    if permission not in admin_role.permissions:
                        admin_role.permissions.append(permission)
                db.session.commit()
                app.logger.info("Initial data inserted successfully")
            except Exception as e:
                app.logger.error(f"Error inserting initial data: {e}")
                db.session.rollback()

        # زمان‌بندی بک‌آپ خودکار دیتابیس هر ۲۴ ساعت با APScheduler
        def schedule_backup():
            try:
                scheduler = BackgroundScheduler()
                scheduler.add_job(create_database_backup, 'interval', hours=24, id='db_backup_job', replace_existing=True)
                scheduler.start()
                app.logger.info("Database backup scheduler started")
            except Exception as e:
                app.logger.error(f"Error starting backup scheduler: {e}")

        # schedule_backup() را فقط یکبار اجرا کن (مثلاً اگر محیط production است)
        # این دستور باید در محیط production اجرا شود
        # اگر محیط development یا testing است، این دستور باید غیرفعال شود
        # برای مثال، اگر محیط production است:
        # if app.config['PRODUCTION']:
        #     schedule_backup()

        app.jinja_env.filters['to_jalali_datetime'] = to_jalali_datetime
        register_jinja_filters(app)
        app.jinja_env.filters['digits_to_persian'] = digits_to_persian
        app.jinja_env.filters['payment_method_fa'] = payment_method_fa
        app.jinja_env.filters['format_price_fa'] = format_price_fa

        @app.route('/health')
        def health_check():
            """بررسی سلامت پنل"""
            return jsonify({'status': 'healthy', 'service': 'panel_api'})

        @app.route('/')
        def index():
            return redirect(url_for('dashboard.index'))

        return app
