# ---------------------------------------------
# فایل: routes.py (admin_management)
# توضیح: مدیریت کاربران ادمین (ساخت، ویرایش، حذف)
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request, send_file, abort
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, AuditLog, BackupFile
from app.forms import CreateUserForm, EditUserForm
from app.decorators import permission_required
from functools import wraps
import os

admin_bp = Blueprint('admin_management', __name__, template_folder='templates')


# --- دکوراتور برای محدود کردن دسترسی به مدیر کل ---
def admin_required(f):
    """
    دکوراتور برای اطمینان از اینکه فقط مدیر کل به ویو دسترسی دارد
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_role(
                'Admin'):
            flash('شما اجازه دسترسی به این صفحه را ندارید.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/')
@login_required
@permission_required('manage_admins')
def index():
    """
    صفحه اصلی که لیست تمام کاربران پنل را نمایش می‌دهد.
    """
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('users.html', users=users, title="مدیریت ادمین‌ها")


@admin_bp.route('/create_user', methods=['GET', 'POST'])
@login_required
@permission_required('manage_admins')
def create_user():
    """
    صفحه ساخت کاربر جدید.
    """
    form = CreateUserForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, name=form.name.data)
            user.set_password(form.password.data)
            user.roles = form.roles.data
            db.session.add(user)
            db.session.commit()
            flash('کاربر جدید با موفقیت ساخته شد.', 'success')
            return redirect(url_for('admin_management.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در ایجاد کاربر: {str(e)}', 'error')
    elif form.errors:
        flash('لطفاً خطاهای فرم را برطرف کنید.', 'error')

    return render_template('create_user.html',
                           form=form,
                           title="ساخت کاربر جدید")


@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_admins')
def edit_user(user_id):
    """
    صفحه ویرایش کاربر.
    """
    user = db.session.get(User, user_id)
    if not user:
        flash('کاربر یافت نشد.', 'danger')
        return redirect(url_for('admin_management.index'))
    form = EditUserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.name = form.name.data
        user.roles = form.roles.data
        # فقط در صورتی که فیلد رمز عبور جدید پر شده باشد، آن را تغییر می‌دهیم
        if form.password.data:
            user.set_password(form.password.data)
        # اگر دکمه آنلاک زده شده باشد
        if 'unlock_account' in form.data and form.data['unlock_account']:
            user.failed_login_attempts = 0
            user.temp_locked_until = None
            user.permanently_locked = False
            # ثبت لاگ آنلاک حساب
            audit = AuditLog()
            audit.user_id = current_user.id
            audit.action = 'unlock_account'
            audit.description = f'آنلاک حساب کاربری {user.username} توسط مدیر'
            audit.ip_address = request.remote_addr
            db.session.add(audit)
            flash('حساب کاربر با موفقیت آنلاک شد.', 'success')
        db.session.commit()
        flash('اطلاعات کاربر با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('admin_management.index'))
    return render_template('edit_user.html',
                           form=form,
                           user=user,
                           title="ویرایش کاربر")


@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@permission_required('manage_admins')
def delete_user(user_id):
    """
    منطق حذف کاربر.
    """
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('کاربر با موفقیت حذف شد.', 'success')
    else:
        flash('کاربر یافت نشد.', 'danger')
    return redirect(url_for('admin_management.index'))


@admin_bp.route('/audit_logs')
@login_required
@permission_required('manage_admins')
def audit_logs():
    """
    نمایش لاگ‌های امنیتی سیستم برای مدیر با فیلتر و جستجو
    """
    query = AuditLog.query
    username = request.args.get('username', '').strip()
    action = request.args.get('action', '').strip()
    ip = request.args.get('ip', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    if username:
        query = query.join(User).filter(User.username.ilike(f'%{username}%'))
    if action:
        query = query.filter(AuditLog.action.ilike(f'%{action}%'))
    if ip:
        query = query.filter(AuditLog.ip_address.ilike(f'%{ip}%'))
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AuditLog.created_at >= date_from_obj)
        except:
            pass
    if date_to:
        try:
            from datetime import datetime, timedelta
            date_to_obj = datetime.strptime(date_to,
                                            '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AuditLog.created_at < date_to_obj)
        except:
            pass

    logs = query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template('audit_logs.html',
                           logs=logs,
                           title='لاگ‌های امنیتی',
                           username=username,
                           action=action,
                           ip=ip,
                           date_from=date_from,
                           date_to=date_to)


@admin_bp.route('/backups')
@login_required
@permission_required('manage_admins')
def backups():
    backups = BackupFile.query.order_by(BackupFile.created_at.desc()).all()
    return render_template('backups.html',
                           backups=backups,
                           title='بک‌آپ‌های دیتابیس')


@admin_bp.route('/download_backup/<int:backup_id>')
@login_required
@permission_required('manage_admins')
def download_backup(backup_id):
    backup = BackupFile.query.get_or_404(backup_id)
    if not os.path.exists(backup.filepath):
        abort(404)
    # ثبت دانلود
    backup.is_downloaded = True
    backup.downloaded_by = current_user.id
    backup.downloaded_at = db.func.now()
    db.session.commit()
    # ثبت لاگ دانلود
    audit = AuditLog()
    audit.user_id = current_user.id
    audit.action = 'download_backup'
    audit.description = f'دانلود بک‌آپ {backup.filename}'
    audit.ip_address = request.remote_addr
    db.session.add(audit)
    db.session.commit()
    # حذف بک‌آپ قدیمی اگر بیش از یک بک‌آپ دانلود شده وجود داشته باشد
    downloaded_backups = BackupFile.query.filter_by(
        is_downloaded=True).order_by(BackupFile.created_at).all()
    if len(downloaded_backups) > 1:
        to_delete = downloaded_backups[0]
        try:
            if os.path.exists(to_delete.filepath):
                os.remove(to_delete.filepath)
            db.session.delete(to_delete)
            db.session.commit()
            # ثبت لاگ حذف
            audit = AuditLog()
            audit.user_id = current_user.id
            audit.action = 'delete_backup'
            audit.description = f'حذف بک‌آپ {to_delete.filename} پس از دانلود دومین بک‌آپ'
            audit.ip_address = request.remote_addr
            db.session.add(audit)
            db.session.commit()
        except Exception as e:
            pass
    return send_file(backup.filepath,
                     as_attachment=True,
                     download_name=backup.filename)
