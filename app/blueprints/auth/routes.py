# ---------------------------------------------
# فایل: routes.py (auth)
# توضیح: مدیریت احراز هویت کاربران (ورود و خروج)
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request, session
from flask_login import login_user, logout_user, current_user
from app.forms import LoginForm
from app.models import User, Notification, Role, SessionLog, AuditLog
import datetime
from app import db

# ساخت یک نمونه از بلوپرینت
auth_bp = Blueprint('auth', __name__, template_folder='../../templates')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    ویو ورود کاربران به سیستم
    اگر کاربر لاگین باشد، به داشبورد هدایت می‌شود.
    در غیر این صورت، فرم ورود نمایش داده می‌شود و اعتبارسنجی انجام می‌گردد.
    """
    # اگر کاربر از قبل لاگین کرده بود، او را به صفحه اصلی بفرست
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        admin_role = Role.query.filter_by(name='Admin').first()

        # اگر کاربر وجود نداشت یا رمز عبور اشتباه بود
        if user is None or not user.check_password(form.password.data):
            if user:
                # اگر حساب به طور دائمی قفل شده باشد
                if user.permanently_locked:
                    flash(
                        'حساب شما قفل شده است. لطفا با مدیر سیستم تماس بگیرید.',
                        'danger')
                    return redirect(url_for('auth.login'))
                # اگر حساب به طور موقت قفل شده باشد
                if user.temp_locked_until and user.temp_locked_until > datetime.datetime.utcnow(
                ):
                    flash(
                        'حساب شما به مدت ۱۰ دقیقه قفل است. لطفا بعدا تلاش کنید.',
                        'danger')
                    return redirect(url_for('auth.login'))
                # افزایش شمارش تلاش ناموفق
                user.failed_login_attempts += 1
                # اگر ۳ تلاش ناموفق شد و هنوز قفل موقت نشده
                if user.failed_login_attempts == 3:
                    user.temp_locked_until = datetime.datetime.utcnow(
                    ) + datetime.timedelta(minutes=10)
                    db.session.commit()
                    flash(
                        'به دلیل ۳ بار تلاش ناموفق، حساب شما به مدت ۱۰ دقیقه قفل می‌شود.',
                        'warning')
                    # اعلان به مدیران
                    if admin_role:
                        notification = Notification()
                        notification.message = f'حساب کاربری {user.username} به مدت ۱۰ دقیقه قفل شد.'
                        notification.role_id = admin_role.id
                        db.session.add(notification)
                    # ثبت لاگ قفل موقت
                    audit = AuditLog()
                    audit.user_id = user.id
                    audit.action = 'temp_lock'
                    audit.description = 'قفل موقت حساب به مدت ۱۰ دقیقه'
                    audit.ip_address = request.remote_addr
                    db.session.add(audit)
                    db.session.commit()
                    return redirect(url_for('auth.login'))
                # اگر بعد از قفل موقت، دوباره ۳ تلاش ناموفق دیگر انجام شد
                if user.failed_login_attempts >= 6:
                    user.permanently_locked = True
                    db.session.commit()
                    flash('حساب شما قفل شد. لطفا با مدیر سیستم تماس بگیرید.',
                          'danger')
                    # اعلان به مدیران
                    if admin_role:
                        notification = Notification()
                        notification.message = f'حساب کاربری {user.username} به طور دائمی قفل شد.'
                        notification.role_id = admin_role.id
                        db.session.add(notification)
                    # ثبت لاگ قفل دائمی
                    audit = AuditLog()
                    audit.user_id = user.id
                    audit.action = 'perm_lock'
                    audit.description = 'قفل دائمی حساب کاربر'
                    audit.ip_address = request.remote_addr
                    db.session.add(audit)
                    db.session.commit()
                    return redirect(url_for('auth.login'))
                db.session.commit()
            flash('نام کاربری یا رمز عبور اشتباه است.', 'danger')
            return redirect(url_for('auth.login'))

        # اگر حساب به طور دائمی قفل شده باشد
        if user.permanently_locked:
            flash('حساب شما قفل شده است. لطفا با مدیر سیستم تماس بگیرید.',
                  'danger')
            return redirect(url_for('auth.login'))
        # اگر حساب به طور موقت قفل شده باشد
        if user.temp_locked_until and user.temp_locked_until > datetime.datetime.utcnow(
        ):
            flash('حساب شما به مدت ۱۰ دقیقه قفل است. لطفا بعدا تلاش کنید.',
                  'danger')
            return redirect(url_for('auth.login'))
        # ورود موفق: ریست شمارش تلاش ناموفق و قفل‌ها
        user.failed_login_attempts = 0
        user.temp_locked_until = None
        user.permanently_locked = False
        db.session.commit()
        login_user(user, remember=form.remember_me.data)
        # --- محدودیت حداکثر دو نشست فعال ---
        active_sessions = SessionLog.query.filter_by(user_id=user.id, is_active=True).order_by(SessionLog.login_time.asc()).all()
        if len(active_sessions) >= 2:
            # خاتمه قدیمی‌ترین نشست فعال
            oldest_session = active_sessions[0]
            oldest_session.logout_time = datetime.datetime.utcnow()
            oldest_session.is_active = False
            db.session.commit()
        # ثبت نشست جدید
        session_log = SessionLog()
        session_log.user_id = user.id
        session_log.ip_address = request.remote_addr
        session_log.user_agent = request.headers.get('User-Agent')
        session_log.device_id = request.cookies.get('device_id')
        db.session.add(session_log)
        db.session.commit()
        session['session_id'] = session_log.id
        # ثبت لاگ ورود موفق
        audit = AuditLog()
        audit.user_id = user.id
        audit.action = 'login'
        audit.description = 'ورود موفق کاربر'
        audit.ip_address = request.remote_addr
        db.session.add(audit)
        db.session.commit()
        return redirect(url_for('dashboard.index'))

    return render_template('login.html', form=form, title="ورود")


@auth_bp.route('/logout')
def logout():
    """
    ویو خروج کاربر از سیستم و پاک کردن نشست
    """
    # غیرفعال کردن آخرین نشست فعال کاربر
    if current_user.is_authenticated:
        last_session = SessionLog.query.filter_by(
            user_id=current_user.id,
            is_active=True).order_by(SessionLog.login_time.desc()).first()
        if last_session:
            last_session.logout_time = datetime.datetime.utcnow()
            last_session.is_active = False
            db.session.commit()
        # ثبت لاگ خروج
        audit = AuditLog()
        audit.user_id = current_user.id
        audit.action = 'logout'
        audit.description = 'خروج کاربر'
        audit.ip_address = request.remote_addr
        db.session.add(audit)
        db.session.commit()
    logout_user()
    session.pop('session_id', None)
    return redirect(url_for('auth.login'))
