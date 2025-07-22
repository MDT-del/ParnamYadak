# ---------------------------------------------
# فایل: routes.py (profile)
# توضیح: مدیریت پروفایل کاربر و تغییر رمز عبور
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request
from flask_login import login_required, current_user
from app import db
from app.forms import ChangePasswordForm
from app.models import SessionLog, User, AuditLog

# ساخت یک نمونه از بلوپرینت
profile_bp = Blueprint('profile', __name__, template_folder='templates')


@profile_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """
    صفحه پروفایل کاربر برای تغییر رمز عبور و نمایش نشست‌ها.
    """
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('رمز عبور شما با موفقیت تغییر کرد.', 'success')
            return redirect(url_for('profile.index'))
        else:
            flash('رمز عبور فعلی شما صحیح نیست.', 'danger')

    # نمایش نشست‌ها
    if current_user.has_role('Admin'):
        # مدیر: همه نشست‌های فعال همه کاربران
        sessions = SessionLog.query.filter_by(is_active=True).order_by(
            SessionLog.login_time.desc()).all()
    else:
        # کاربر عادی: فقط نشست‌های خودش
        sessions = SessionLog.query.filter_by(
            user_id=current_user.id,
            is_active=True).order_by(SessionLog.login_time.desc()).all()

    return render_template('profile.html',
                           form=form,
                           title="پروفایل من",
                           sessions=sessions)


@profile_bp.route('/terminate_session/<int:session_id>', methods=['POST'])
@login_required
def terminate_session(session_id):
    session = SessionLog.query.get_or_404(session_id)
    # فقط مدیر یا صاحب نشست اجازه خاتمه دارد
    if current_user.has_role('Admin') or session.user_id == current_user.id:
        session.is_active = False
        session.logout_time = db.func.now()
        # ثبت لاگ خاتمه نشست
        audit = AuditLog()
        audit.user_id = current_user.id
        audit.action = 'terminate_session'
        audit.description = f'خاتمه نشست کاربر {session.user_id} توسط {current_user.username}'
        audit.ip_address = request.remote_addr
        db.session.add(audit)
        db.session.commit()
        flash('نشست با موفقیت خاتمه یافت.', 'success')
    else:
        flash('شما اجازه خاتمه این نشست را ندارید.', 'danger')
    return redirect(url_for('profile.index'))
