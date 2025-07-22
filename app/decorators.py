# ---------------------------------------------
# فایل: decorators.py
# توضیح: این فایل شامل دکوراتورهای دسترسی و لایسنس برای کنترل مجوزها و نقش‌ها است.
# ---------------------------------------------

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user, login_required
from .utils import is_license_active


def permission_required(permission):
    """
    دکوراتور برای بررسی مجوز خاص (permission) برای دسترسی به یک ویو
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # اگر کاربر لاگین نکرده باشد، به صفحه ورود هدایت می‌شود
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            # اگر مجوز لازم را نداشته باشد، پیام خطا و بازگشت به داشبورد
            if not current_user.can(permission):
                flash('شما مجوز لازم برای این عملیات را ندارید', 'error')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def license_required(f):
    """دکوراتور برای بررسی فعال بودن لایسنس"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_license_active():
            flash('لطفاً ابتدا لایسنس سیستم را فعال کنید', 'warning')
            return redirect(url_for('license.activate'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """دکوراتور برای بررسی دسترسی ادمین"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.has_role('Admin'):
            flash('شما دسترسی لازم برای این بخش را ندارید', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function
