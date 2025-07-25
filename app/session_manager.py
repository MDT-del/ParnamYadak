# ---------------------------------------------
# فایل: session_manager.py
# توضیح: مدیریت پیشرفته Session و امنیت نشست‌ها
# ---------------------------------------------

import datetime
import logging
from flask import session, request, redirect, url_for, flash, current_app
from flask_login import logout_user, current_user
from app.models import SessionLog
from app import db

logger = logging.getLogger(__name__)


class SessionManager:
    """
    کلاس مدیریت Session با قابلیت‌های امنیتی پیشرفته
    """
    
    # تنظیمات پیش‌فرض
    DEFAULT_SESSION_TIMEOUT = 1800  # 30 دقیقه
    MAX_INACTIVE_TIME = 900  # 15 دقیقه بی‌فعالیتی
    
    @staticmethod
    def create_session(user, ip_address=None, user_agent=None, device_id=None):
        """
        ایجاد نشست جدید برای کاربر
        
        Args:
            user: شیء کاربر
            ip_address: آدرس IP
            user_agent: اطلاعات مرورگر
            device_id: شناسه دستگاه
            
        Returns:
            SessionLog: شیء نشست ایجاد شده
        """
        try:
            # بستن نشست‌های قبلی فعال کاربر (اختیاری)
            SessionManager.close_user_sessions(user.id, exclude_current=False)
            
            # ایجاد نشست جدید
            session_log = SessionLog(
                user_id=user.id,
                ip_address=ip_address or request.remote_addr,
                user_agent=user_agent or request.headers.get('User-Agent', ''),
                device_id=device_id,
                login_time=datetime.datetime.utcnow(),
                is_active=True,
                last_activity=datetime.datetime.utcnow()
            )
            
            db.session.add(session_log)
            db.session.commit()
            
            # ذخیره شناسه نشست در session
            session['session_id'] = session_log.id
            session['user_id'] = user.id
            session['login_time'] = session_log.login_time.isoformat()
            
            logger.info(f"نشست جدید برای کاربر {user.username} ایجاد شد - Session ID: {session_log.id}")
            return session_log
            
        except Exception as e:
            logger.error(f"خطا د�� ایجاد نشست: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_activity(session_id=None):
        """
        بروزرسانی زمان آخرین فعالیت
        
        Args:
            session_id: شناسه نشست (اختیاری)
        """
        try:
            session_id = session_id or session.get('session_id')
            if not session_id:
                return False
                
            session_log = SessionLog.query.get(session_id)
            if session_log and session_log.is_active:
                session_log.last_activity = datetime.datetime.utcnow()
                db.session.commit()
                return True
                
        except Exception as e:
            logger.error(f"خطا در بروزرسانی فعالیت نشست: {e}")
            
        return False
    
    @staticmethod
    def is_session_valid(session_id=None):
        """
        بررسی اعتبار نشست
        
        Args:
            session_id: شناسه نشست
            
        Returns:
            tuple: (is_valid, reason)
        """
        try:
            session_id = session_id or session.get('session_id')
            if not session_id:
                return False, "session_id_missing"
                
            session_log = SessionLog.query.get(session_id)
            if not session_log:
                return False, "session_not_found"
                
            if not session_log.is_active:
                return False, "session_inactive"
                
            now = datetime.datetime.utcnow()
            
            # بررسی انقضای کلی نشست
            if session_log.last_activity:
                inactive_time = (now - session_log.last_activity).total_seconds()
                if inactive_time > SessionManager.MAX_INACTIVE_TIME:
                    return False, "session_expired"
                    
            # بررسی حداکثر مدت نشست
            total_time = (now - session_log.login_time).total_seconds()
            if total_time > SessionManager.DEFAULT_SESSION_TIMEOUT:
                return False, "session_timeout"
                
            return True, "valid"
            
        except Exception as e:
            logger.error(f"خطا در بررسی اعتبار نشست: {e}")
            return False, "error"
    
    @staticmethod
    def close_session(session_id=None, reason="manual"):
        """
        بستن نشست
        
        Args:
            session_id: شناسه نشست
            reason: دلیل ��ستن نشست
        """
        try:
            session_id = session_id or session.get('session_id')
            if not session_id:
                return False
                
            session_log = SessionLog.query.get(session_id)
            if session_log:
                session_log.is_active = False
                session_log.logout_time = datetime.datetime.utcnow()
                db.session.commit()
                
                logger.info(f"نشست {session_id} بسته شد - دلیل: {reason}")
                
            # پاک کردن اطلاعات session
            session.pop('session_id', None)
            session.pop('user_id', None)
            session.pop('login_time', None)
            
            return True
            
        except Exception as e:
            logger.error(f"خطا در بستن نشست: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def close_user_sessions(user_id, exclude_current=True):
        """
        بستن تمام نشست‌های فعال یک کاربر
        
        Args:
            user_id: شناسه کاربر
            exclude_current: حذف نشست فعلی یا نه
        """
        try:
            query = SessionLog.query.filter_by(user_id=user_id, is_active=True)
            
            if exclude_current:
                current_session_id = session.get('session_id')
                if current_session_id:
                    query = query.filter(SessionLog.id != current_session_id)
            
            sessions = query.all()
            for session_log in sessions:
                session_log.is_active = False
                session_log.logout_time = datetime.datetime.utcnow()
                
            db.session.commit()
            logger.info(f"تمام نشست‌های کاربر {user_id} بسته شد")
            
        except Exception as e:
            logger.error(f"خطا در بستن نشست‌های کاربر: {e}")
            db.session.rollback()
    
    @staticmethod
    def cleanup_expired_sessions():
        """
        پاک‌سازی نشست‌های منقضی شده
        """
        try:
            cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(
                seconds=SessionManager.DEFAULT_SESSION_TIMEOUT
            )
            
            expired_sessions = SessionLog.query.filter(
                SessionLog.is_active == True,
                SessionLog.last_activity < cutoff_time
            ).all()
            
            for session_log in expired_sessions:
                session_log.is_active = False
                session_log.logout_time = datetime.datetime.utcnow()
                
            db.session.commit()
            
            if expired_sessions:
                logger.info(f"{len(expired_sessions)} نشست منقضی شده پاک‌سازی شد")
                
        except Exception as e:
            logger.error(f"خطا در پاک‌سازی نشست‌های منقضی: {e}")
            db.session.rollback()


def session_required(f):
    """
    دکوراتور برای بررسی اعتبار نشست
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return f(*args, **kwargs)
            
        is_valid, reason = SessionManager.is_session_valid()
        
        if not is_valid:
            # تعیین پیام مناسب بر اساس دلیل
            messages = {
                'session_expired': 'نشست شما به دلیل عدم فعالیت منقضی شده است.',
                'session_timeout': 'مدت زمان نشست به پایان رسیده است.',
                'session_inactive': 'نشست شما توسط مدیر سیستم خاتمه یافته است.',
                'session_not_found': 'نشست معتبر یافت نشد.',
                'session_id_missing': 'اطلاعات نشست موجود نیست.'
            }
            
            message = messages.get(reason, 'نشست شما نامعتبر است.')
            
            # بستن نشست و خروج کاربر
            SessionManager.close_session(reason=reason)
            logout_user()
            
            flash(f'{message} لطفاً مجدداً وارد شوید.', 'warning')
            return redirect(url_for('auth.login'))
        
        # بروزرسانی فعالیت
        SessionManager.update_activity()
        
        return f(*args, **kwargs)
    
    return decorated_function


def init_session_manager(app):
    """
    راه‌اندازی مدیریت نشست در اپلیکیشن
    
    Args:
        app: شیء Flask app
    """
    
    @app.before_request
    def check_session_validity():
        """
        بررسی اعتبار نشست قبل از هر درخواست
        """
        # مسیرهایی که نیاز به بررسی نشست ندارند
        exempt_paths = [
            '/auth/login',
            '/auth/logout', 
            '/static/',
            '/license/',
            '/health'
        ]
        
        # بررسی مسیر فعلی
        current_path = request.path
        is_exempt = any(current_path.startswith(path) for path in exempt_paths)
        
        # اگر کاربر لاگین نیست یا مسیر معاف است، ادامه بده
        if not current_user.is_authenticated or is_exempt:
            return
            
        try:
            # بررسی اعتبار نشست
            is_valid, reason = SessionManager.is_session_valid()
            
            if not is_valid:
                # تعیین پیام مناسب
                messages = {
                    'session_expired': 'نشست شما به دلیل عدم فعالیت منقضی شده است.',
                    'session_timeout': 'مدت زمان نشست به پایان رسیده است.',
                    'session_inactive': 'نشست شما توسط مدیر سیستم خاتمه یافته است.',
                    'session_not_found': 'نشست معتبر یافت نشد.',
                    'session_id_missing': 'اطلاعات نشست موجود نیست.'
                }
                
                message = messages.get(reason, 'نشست شما نامعتبر است.')
                
                # بستن نشست و خروج کاربر
                SessionManager.close_session(reason=reason)
                logout_user()
                
                flash(f'{message} لطفاً مجدداً وارد شوید.', 'warning')
                return redirect(url_for('auth.login'))
            
            # بروزرسانی فعالیت
            SessionManager.update_activity()
            
        except Exception as e:
            logger.error(f"خطا در بررسی نشست: {e}")
            # در صورت خطا، اجازه ادامه بده
            pass
    
    # تنظیم پاک‌سازی خودکار نشست‌های منقضی
    from apscheduler.schedulers.background import BackgroundScheduler
    
    try:
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            SessionManager.cleanup_expired_sessions,
            'interval',
            minutes=30,  # هر 30 دقیقه
            id='cleanup_sessions',
            replace_existing=True
        )
        scheduler.start()
        logger.info("پاک‌سازی خودکار نشست‌ها فعال شد")
    except Exception as e:
        logger.error(f"خطا در راه‌اندازی پاک‌سازی نشست‌ها: {e}")