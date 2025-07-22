# ---------------------------------------------
# فایل: routes.py (tasks)
# توضیح: مسیرهای مدیریت وظایف
# ---------------------------------------------

from flask import render_template, Blueprint, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Task, Role, Notification
from app.decorators import permission_required
import json
from datetime import datetime, timedelta
import logging
import traceback

tasks_bp = Blueprint('tasks', __name__, template_folder='templates')


@tasks_bp.route('/')
@login_required
@permission_required('manage_tasks')
def index():
    """
    صفحه اصلی کارتابل
    """
    # واکشی لیست وظایف با صفحه‌بندی
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', None)
    query = Task.query

    valid_statuses = ['جدید', 'در حال انجام', 'انجام شده', 'لغو شده']
    if status in valid_statuses:
        query = query.filter_by(status=status)

    tasks = query.order_by(Task.created_at.desc()).paginate(page=page, per_page=20, error_out=False)

    # آمار
    total_tasks = Task.query.count()
    new_tasks = Task.query.filter_by(status='جدید').count()
    in_progress_tasks = Task.query.filter_by(status='در حال انجام').count()
    completed_tasks = Task.query.filter_by(status='انجام شده').count()

    return render_template(
        'tasks/index.html',
        tasks=tasks,
        total_tasks=total_tasks,
        new_tasks=new_tasks,
        in_progress_tasks=in_progress_tasks,
        completed_tasks=completed_tasks
    )


@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('manage_tasks')
def create():
    """
    ایجاد وظیفه جدید
    """
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = request.form.get('due_date')
        role_id = request.form.get('role_id', type=int)
        assigned_user_id = request.form.get('assigned_user_id', type=int)

        if not title:
            flash('عنوان وظیفه الزامی است', 'error')
            return redirect(url_for('tasks.create'))

        try:
            task = Task(
                title=title,
                description=description,
                due_date=due_date,
                role_id=role_id,
                assigned_user_id=assigned_user_id,
                created_by=current_user.id
            )
            db.session.add(task)
            db.session.commit()
            # اعلان برای کاربر هدف یا نقش هدف
            if assigned_user_id:
                notif = Notification(
                    message=f"یک وظیفه جدید به شما ارجاع داده شد: {title}",
                    user_id=assigned_user_id
                )
                db.session.add(notif)
                db.session.commit()
            elif role_id:
                notif = Notification(
                    message=f"یک وظیفه جدید به نقش شما ارجاع داده شد: {title}",
                    role_id=role_id
                )
                db.session.add(notif)
                db.session.commit()
            flash('وظیفه با موفقیت ایجاد شد', 'success')
            return redirect(url_for('tasks.index'))
        except Exception as e:
            db.session.rollback()
            flash('خطا در ایجاد وظیفه', 'error')
            return redirect(url_for('tasks.create'))

    roles = Role.query.all()
    statuses = ['جدید', 'در حال انجام', 'انجام شده', 'لغو شده']
    return render_template('tasks/create.html', roles=roles, statuses=statuses)


@tasks_bp.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_tasks')
def edit(task_id):
    """
    ویرایش وظیفه
    """
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.due_date = request.form.get('due_date')
        task.status = request.form.get('status')
        task.role_id = request.form.get('role_id', type=int)
        task.assigned_user_id = request.form.get('assigned_user_id', type=int)
        
        try:
            db.session.commit()
            flash('وظیفه با موفقیت بروزرسانی شد', 'success')
            return redirect(url_for('tasks.index'))
        except Exception as e:
            db.session.rollback()
            flash('خطا در بروزرسانی وظیفه', 'error')
    
    roles = Role.query.all()
    return render_template('tasks/edit.html', task=task, roles=roles)


@tasks_bp.route('/<int:task_id>')
@login_required
@permission_required('manage_tasks')
def show(task_id):
    """
    نمایش جزئیات وظیفه
    """
    task = Task.query.get_or_404(task_id)
    return render_template('tasks/show.html', task=task)


@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
@permission_required('manage_tasks')
def delete(task_id):
    """
    حذف وظیفه
    """
    task = Task.query.get_or_404(task_id)
    
    try:
        db.session.delete(task)
        db.session.commit()
        flash('وظیفه با موفقیت حذف شد', 'success')
    except Exception as e:
        db.session.rollback()
        flash('خطا در حذف وظیفه', 'error')
    
    return redirect(url_for('tasks.index'))
