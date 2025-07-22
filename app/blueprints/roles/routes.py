# ---------------------------------------------
# فایل: routes.py (roles)
# توضیح: مدیریت نقش‌ها و مجوزها (ساخت، ویرایش، حذف نقش)
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint
from flask_login import login_required
from app import db
from app.models import Role, Permission
from app.forms import RoleForm
from app.decorators import permission_required  # ⬇️ ایمپورت صحیح

# ایمپورت اشتباه قبلی حذف شد

# ساخت یک نمونه از بلوپرینت
roles_bp = Blueprint('roles', __name__, template_folder='templates')


@roles_bp.route('/')
@login_required
@permission_required('manage_roles')  # ⬇️ استفاده از دکوراتور صحیح
def index():
    """
    صفحه اصلی که لیست تمام نقش‌ها را نمایش می‌دهد.
    """
    roles = Role.query.order_by(Role.id).all()
    return render_template('roles.html', roles=roles, title="مدیریت نقش‌ها")


@roles_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('manage_roles')  # ⬇️ استفاده از دکوراتور صحیح
def create_role():
    """
    صفحه ساخت نقش جدید.
    """
    form = RoleForm()
    if form.validate_on_submit():
        new_role = Role(name=form.name.data, description=form.description.data)
        new_role.permissions = form.permissions.data
        db.session.add(new_role)
        db.session.commit()
        flash('نقش جدید با موفقیت ساخته شد.', 'success')
        return redirect(url_for('roles.index'))
    return render_template('create_role.html',
                           form=form,
                           title="ساخت نقش جدید")


@roles_bp.route('/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_roles')  # ⬇️ استفاده از دکوراتور صحیح
def edit_role(role_id):
    """
    صفحه ویرایش نقش.
    """
    role = db.session.get(Role, role_id)
    if not role:
        flash('نقش یافت نشد.', 'danger')
        return redirect(url_for('roles.index'))

    if role.name == 'Admin':
        flash('نقش مدیر کل قابل ویرایش نیست.', 'warning')
        return redirect(url_for('roles.index'))

    form = RoleForm(obj=role)
    if form.validate_on_submit():
        role.name = form.name.data
        role.description = form.description.data
        role.permissions = form.permissions.data
        db.session.commit()
        flash('نقش با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('roles.index'))

    # Pre-select checkboxes for editing
    form.permissions.data = role.permissions
    return render_template('edit_role.html',
                           form=form,
                           role=role,
                           title="ویرایش نقش")


@roles_bp.route('/delete/<int:role_id>', methods=['POST'])
@login_required
@permission_required('manage_roles')  # ⬇️ استفاده از دکوراتور صحیح
def delete_role(role_id):
    """
    منطق حذف نقش.
    """
    role = db.session.get(Role, role_id)
    if role and role.name != 'Admin':
        db.session.delete(role)
        db.session.commit()
        flash('نقش با موفقیت حذف شد.', 'success')
    elif role.name == 'Admin':
        flash('نقش مدیر کل قابل حذف نیست.', 'danger')
    else:
        flash('نقش یافت نشد.', 'danger')
    return redirect(url_for('roles.index'))
