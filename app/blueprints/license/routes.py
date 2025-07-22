# ---------------------------------------------
# فایل: routes.py (license)
# توضیح: مدیریت لایسنس سیستم و فعال‌سازی آن
# ---------------------------------------------

import hashlib
import hmac
import json
import os
import secrets
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from app import db
from app.models import License, User, Role, Permission
from app.utils import is_license_active, get_license_info

license_bp = Blueprint('license', __name__)

# کلید امنیتی (در محیط واقعی باید در فایل .env باشد)
SECRET_KEY = os.environ.get('LICENSE_SECRET_KEY', 'your-super-secret-license-key-2024')

def generate_secure_license_key(prefix="NIKADEK", license_type="PRO"):
    """
    تولید کد لایسنس امن با پیشوند و نوع مشخص
    """
    # تولید بخش تصادفی
    random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    year = datetime.now().year
    
    # ساخت کد لایسنس
    license_key = f"{prefix}-{year}-{license_type}-{random_part}"
    
    return license_key

def generate_license_hash(license_key):
    """
    تولید هش امن برای لایسنس
    """
    return hmac.new(
        SECRET_KEY.encode('utf-8'),
        license_key.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def verify_license_key(license_key):
    """
    تایید کد لایسنس
    """
    # کدهای لایسنس معتبر (در محیط واقعی باید در دیتابیس یا فایل امن باشد)
    valid_licenses = {
        'NIKADEK-2024-PRO': {
            'customer_name': 'Nikadek Pro',
            'max_users': 10,
            'expiry_days': 365,
            'features': ['all']
        },
        'NIKADEK-2024-ENTERPRISE': {
            'customer_name': 'Nikadek Enterprise',
            'max_users': 50,
            'expiry_days': 365,
            'features': ['all', 'advanced_analytics', 'api_access']
        }
    }
    
    return valid_licenses.get(license_key)

def is_first_time_setup():
    """
    بررسی اینکه آیا این اولین اجرای سیستم است
    """
    # بررسی وجود لایسنس فعال
    if is_license_active():
        return False
    
    # بررسی وجود لایسنس غیرفعال
    inactive_license = License.query.filter_by(is_active=False).first()
    return inactive_license is None

def send_email_notification(license_key):
    """
    ارسال اعلان ایمیل به توسعه‌دهنده
    """
    try:
        # ایمیل توسعه‌دهنده (در محیط واقعی باید در فایل .env باشد)
        developer_email = os.environ.get('DEVELOPER_EMAIL', 'developer@example.com')
        
        # اینجا می‌توانید از Flask-Mail استفاده کنید
        # فعلاً فقط لاگ می‌کنیم
        current_app.logger.info(f"کد لایسنس برای توسعه‌دهنده {developer_email}: {license_key}")
        
        # نمایش کد در کنسول فقط برای توسعه‌دهنده (در محیط توسعه)
        if current_app.debug:
            print(f"\n🔐 کد لایسنس تولید شده: {license_key}")
            print(f"📧 این کد به {developer_email} ارسال خواهد شد")
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"خطا در ارسال ایمیل: {e}")
        return False

def create_admin_user():
    """
    ایجاد کاربر ادمین پیش‌فرض
    """
    try:
        # بررسی وجود کاربر ادمین
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            return admin_user
        
        # ایجاد کاربر ادمین
        admin_user = User()
        admin_user.username = 'admin'
        admin_user.name = 'مدیر سیستم'
        admin_user.set_password('admin')
        
        # پیدا کردن نقش ادمین
        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role:
            # اطمینان از اینکه همه Permissionها به نقش Admin داده شده
            all_perms = Permission.query.all()
            for perm in all_perms:
                if perm not in admin_role.permissions:
                    admin_role.permissions.append(perm)
            db.session.commit()
            admin_user.roles.append(admin_role)
        
        db.session.add(admin_user)
        db.session.commit()
        
        current_app.logger.info("کاربر ادمین با موفقیت ایجاد شد")
        return admin_user
        
    except Exception as e:
        current_app.logger.error(f"خطا در ایجاد کاربر ادمین: {e}")
        db.session.rollback()
        return None

@license_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """
    صفحه راه‌اندازی اولیه سیستم
    """
    if not is_first_time_setup():
        return redirect(url_for('license.activate'))
    
    if request.method == 'POST':
        # تولید کد لایسنس جدید
        license_key = generate_secure_license_key("NIKADEK", "PRO")
        license_hash = generate_license_hash(license_key)
        
        # ایجاد لایسنس در دیتابیس
        new_license = License()
        new_license.license_key = license_key
        new_license.license_hash = license_hash
        new_license.customer_name = 'Nikadek Pro'
        new_license.max_users = 10
        new_license.features = json.dumps(['all'])
        new_license.expiry_date = datetime.utcnow() + timedelta(days=365)
        new_license.is_active = False
        new_license.created_at = datetime.utcnow()
        
        try:
            db.session.add(new_license)
            db.session.commit()
            
            # ارسال اعلان ایمیل به توسعه‌دهنده
            notification_sent = send_email_notification(license_key)
            
            if notification_sent:
                flash('کد لایسنس با موفقیت تولید و به ایمیل توسعه‌دهنده ارسال شد. لطفاً منتظر دریافت کد باشید.', 'success')
            else:
                flash('کد لایسنس تولید شد اما خطا در ارسال ایمیل. لطفاً با توسعه‌دهنده تماس بگیرید.', 'warning')
            
            return redirect(url_for('license.activate'))
            
        except Exception as e:
            db.session.rollback()
            flash('خطا در تولید کد لایسنس', 'error')
            current_app.logger.error(f"خطا در تولید لایسنس: {e}")
    
    return render_template('license/setup.html')

@license_bp.route('/activate', methods=['GET', 'POST'])
def activate():
    """
    صفحه فعال‌سازی لایسنس
    """
    # اگر لایسنس فعال است، به داشبورد هدایت کن
    if is_license_active():
        return redirect(url_for('dashboard.index'))
    
    # اگر اولین اجرا است، به صفحه راه‌اندازی هدایت کن
    if is_first_time_setup():
        return redirect(url_for('license.setup'))
    
    if request.method == 'POST':
        license_key = request.form.get('license_key', '').strip()
        
        if not license_key:
            flash('لطفاً کد لایسنس را وارد کنید', 'error')
            return render_template('license/activate.html')
        
        # بررسی وجود لایسنس در دیتابیس
        existing_license = License.query.filter_by(license_key=license_key).first()
        
        if not existing_license:
            flash('کد لایسنس نامعتبر است', 'error')
            return render_template('license/activate.html')
        
        if existing_license.is_active:
            flash('این لایسنس قبلاً فعال شده است', 'error')
            return render_template('license/activate.html')
        
        # فعال‌سازی لایسنس
        existing_license.is_active = True
        existing_license.activation_date = datetime.utcnow()
        
        try:
            db.session.commit()
            
            # ایجاد کاربر ادمین در اولین فعال‌سازی
            create_admin_user()
            
            flash('لایسنس با موفقیت فعال شد!', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('خطا در فعال‌سازی لایسنس', 'error')
            current_app.logger.error(f"خطا در فعال‌سازی لایسنس: {e}")
    
    return render_template('license/activate.html')

@license_bp.route('/status')
@login_required
def status():
    """نمایش وضعیت لایسنس"""
    license = License.query.filter_by(is_active=True).first()
    return render_template('license/status.html', license=license) 