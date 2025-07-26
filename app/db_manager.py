"""
مدیریت اتصالات دیتابیس
"""
import logging
from functools import wraps
from flask import g
from app import db
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabaseManager:
    """مدیریت اتصالات دیتابیس"""
    
    @staticmethod
    def ensure_connection():
        """اطمینان از وجود اتصال سالم به دیتابیس"""
        try:
            # تست اتصال
            db.session.execute(text('SELECT 1'))
            return True
        except Exception as e:
            logger.warning(f"مشکل در اتصال دیتابیس، تلاش برای reconnect: {e}")
            try:
                db.session.rollback()
                db.session.close()
                db.session.execute(text('SELECT 1'))
                return True
            except Exception as e2:
                logger.error(f"خطا در reconnect به دیتابیس: {e2}")
                return False
    
    @staticmethod
    def cleanup_connection():
        """پاک‌سازی اتصال بعد از استفاده"""
        try:
            if db.session.is_active:
                db.session.commit()
        except Exception as e:
            logger.warning(f"خطا در commit: {e}")
            db.session.rollback()
        finally:
            db.session.close()

def db_connection_required(f):
    """
    دکوراتور برای اطمینان از اتصال سالم به دیتابیس
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # بررسی اتصال قبل از اجرا
            if not DatabaseManager.ensure_connection():
                raise Exception("خطا در اتصال به دیتابیس")
            
            # اجرای تابع
            result = f(*args, **kwargs)
            
            # commit تغییرات
            db.session.commit()
            return result
            
        except Exception as e:
            # rollback در صورت خطا
            db.session.rollback()
            logger.error(f"خطا در {f.__name__}: {e}")
            raise
        finally:
            # پاک‌سازی اتصال
            DatabaseManager.cleanup_connection()
    
    return decorated_function

def safe_db_operation(operation_func, *args, **kwargs):
    """
    اجرای امن عملیات دیتابیس
    """
    try:
        if not DatabaseManager.ensure_connection():
            raise Exception("خطا در اتصال به دیتابیس")
        
        result = operation_func(*args, **kwargs)
        db.session.commit()
        return result
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"خطا در عملیات دیتابیس: {e}")
        raise
    finally:
        DatabaseManager.cleanup_connection()
