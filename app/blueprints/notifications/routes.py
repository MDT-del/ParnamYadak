from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Notification, Mechanic, Customer
from app import db
from app.decorators import permission_required
import logging
from flask_socketio import emit
from flask import current_app

notifications_bp = Blueprint('notifications', __name__, template_folder='templates')


@notifications_bp.route('/')
@login_required
def index():
    """
    صفحه اصلی اعلان‌ها
    """
    try:
        # دریافت اعلان‌های خوانده نشده کاربر
        unread_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        # دریافت اعلان‌های نقش کاربر
        role_notifications = Notification.query.filter_by(
            role_id=current_user.roles[0].id if current_user.roles else None,
            is_read=False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        # لیست ترکیبی اعلان‌ها (کاربر و نقش)
        notifications = list(unread_notifications) + list(role_notifications)
        # حذف اعلان‌های تکراری (بر اساس id)
        notifications = {n.id: n for n in notifications}.values()
        notifications = sorted(notifications, key=lambda n: n.created_at, reverse=True)
        
        # تعداد کل اعلان‌ها
        total_notifications = Notification.query.filter(
            (Notification.user_id == current_user.id) |
            (Notification.role_id == (current_user.roles[0].id if current_user.roles else None))
        ).count()
        
        return render_template(
            'notifications/index.html',
            notifications=notifications,
            total_notifications=total_notifications,
            unread_notifications=len(unread_notifications)
        )
    except Exception as e:
        logging.error(f"Error in notifications index: {str(e)}")
        flash('خطا در بارگذاری اعلان‌ها', 'error')
        return redirect(url_for('dashboard.index'))


@notifications_bp.route('/api/count')
@login_required
def get_notifications_count():
    """
    دریافت تعداد اعلان‌های خوانده نشده به تفکیک نوع (سفارش جدید، مکانیک جدید و ...)
    """
    try:
        # اعلان‌های کاربر
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).all()
        # اعلان‌های نقش
        role_notifications = []
        if current_user.roles:
            role_notifications = Notification.query.filter_by(
                role_id=current_user.roles[0].id,
                is_read=False
            ).all()
        # ترکیب و حذف تکراری‌ها
        all_notifications = {n.id: n for n in (list(user_notifications) + list(role_notifications))}.values()
        # شمارش بر اساس نوع پیام
        new_orders = 0
        new_mechanics = 0
        task_notifications = 0
        for notif in all_notifications:
            msg = notif.message or ''
            if 'سفارش جدید' in msg or 'سفارش ربات' in msg:
                new_orders += 1
            elif 'مکانیک جدید' in msg:
                new_mechanics += 1
            elif 'وظیفه جدید' in msg or 'ارجاع داده شده' in msg:
                task_notifications += 1
        total_notifications = len(all_notifications)
        return jsonify({
            'success': True,
            'data': {
                'new_orders': new_orders,
                'new_mechanics': new_mechanics,
                'task_notifications': task_notifications,
                'total_notifications': total_notifications
            }
        })
    except Exception as e:
        logging.error(f"Error getting notifications count: {str(e)}")
        return jsonify({
            'success': False,
            'data': {
                'new_orders': 0,
                'new_mechanics': 0,
                'task_notifications': 0,
                'total_notifications': 0
            },
            'error': str(e)
        })


@notifications_bp.route('/api/list')
@login_required
def get_notifications_list():
    """
    دریافت لیست اعلان‌ها
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # اعلان‌های کاربر
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # اعلان‌های نقش
        role_notifications = []
        if current_user.roles:
            role_notifications = Notification.query.filter_by(
                role_id=current_user.roles[0].id
            ).order_by(Notification.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        notifications = []
        
        # ترکیب اعلان‌ها
        for notification in user_notifications.items:
            notifications.append({
                'id': notification.id,
                'message': notification.message,
                'is_read': notification.is_read,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'user'
            })
        
        for notification in role_notifications.items:
            notifications.append({
                'id': notification.id,
                'message': notification.message,
                'is_read': notification.is_read,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'role'
            })
        
        # مرتب‌سازی بر اساس تاریخ
        notifications.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'total': len(notifications)
        })
        
    except Exception as e:
        logging.error(f"Error getting notifications list: {str(e)}")
        return jsonify({
            'success': False,
            'notifications': [],
            'error': str(e)
        })


@notifications_bp.route('/api/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """
    علامت‌گذاری اعلان‌ها به عنوان خوانده شده (همه اعلان‌های نقش‌های کاربر و user_id)
    """
    try:
        data = request.get_json()
        notification_ids = data.get('notification_ids', [])
        mark_all = data.get('type') == 'all'
        # همه نقش‌های کاربر
        role_ids = [role.id for role in current_user.roles] if current_user.roles else []
        if mark_all:
            # همه اعلان‌های خوانده‌نشده کاربر و نقش‌هایش
            notifications = Notification.query.filter(
                ((Notification.user_id == current_user.id) |
                 (Notification.role_id.in_(role_ids) if role_ids else False)),
                Notification.is_read == False
            ).all()
        else:
            # فقط اعلان‌های انتخاب شده
            notifications = Notification.query.filter(
                Notification.id.in_(notification_ids),
                ((Notification.user_id == current_user.id) |
                 (Notification.role_id.in_(role_ids) if role_ids else False))
            ).all()
        for notification in notifications:
            notification.is_read = True
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'اعلان‌ها به عنوان خوانده شده علامت‌گذاری شدند'
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error marking notifications read: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطا در علامت‌گذاری اعلان‌ها',
            'error': str(e)
        }), 500


@notifications_bp.route('/api/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_single_notification_read(notification_id):
    """
    علامت‌گذاری یک اعلان به عنوان خوانده شده
    """
    try:
        notification = Notification.query.get(notification_id)
        
        if not notification:
            return jsonify({
                'success': False,
                'message': 'اعلان یافت نشد'
            }), 404
        
        # بررسی دسترسی
        if notification.user_id != current_user.id and notification.role_id != (current_user.roles[0].id if current_user.roles else None):
            return jsonify({
                'success': False,
                'message': 'دسترسی غیرمجاز'
            }), 403
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'اعلان به عنوان خوانده شده علامت‌گذاری شد'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error marking notification read: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطا در علامت‌گذاری اعلان',
            'error': str(e)
        }), 500


@notifications_bp.route('/api/delete-read', methods=['POST'])
@login_required
def delete_read_notifications():
    """
    حذف اعلان‌های خوانده شده
    """
    try:
        # حذف اعلان‌های خوانده شده کاربر
        user_deleted = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=True
        ).delete()
        
        # حذف اعلان‌های خوانده شده نقش
        role_deleted = 0
        if current_user.roles:
            role_deleted = Notification.query.filter_by(
                role_id=current_user.roles[0].id,
                is_read=True
            ).delete()
        
        db.session.commit()
        
        total_deleted = user_deleted + role_deleted
        
        return jsonify({
            'success': True,
            'message': f'{total_deleted} اعلان خوانده شده حذف شد',
            'deleted_count': total_deleted
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting read notifications: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطا در حذف اعلان‌ها',
            'error': str(e)
        }), 500


@notifications_bp.route('/all')
@login_required
def all_notifications():
    """
    صفحه تمام اعلان‌ها (همه نقش‌های کاربر + user_id)
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        # همه نقش‌های کاربر
        role_ids = [role.id for role in current_user.roles] if current_user.roles else []
        # همه اعلان‌های کاربر و نقش‌هایش
        notifications_query = Notification.query.filter(
            (Notification.user_id == current_user.id) |
            (Notification.role_id.in_(role_ids) if role_ids else False)
        ).order_by(Notification.created_at.desc())
        notifications = notifications_query.paginate(page=page, per_page=per_page, error_out=False)
        return render_template(
            'notifications/all.html',
            notifications=notifications
        )
    except Exception as e:
        logging.error(f"Error in all notifications: {str(e)}")
        flash('خطا در بارگذاری اعلان‌ها', 'error')
        return redirect(url_for('notifications.index'))


@notifications_bp.route('/api/create', methods=['POST'])
@login_required
@permission_required('manage_notifications')
def create_notification():
    """
    ایجاد اعلان جدید
    """
    try:
        data = request.get_json()
        message = data.get('message')
        role_id = data.get('role_id')
        user_id = data.get('user_id')
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'پیام اعلان الزامی است'
            }), 400
        
        notification = Notification(
            message=message,
            role_id=role_id,
            user_id=user_id
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # پس از ذخیره اعلان جدید، اگر کاربر آنلاین است، اعلان را به صورت real-time ارسال کن
        try:
            from app import socketio
            if user_id:
                socketio.emit('notification', {
                    'message': message,
                    'user_id': user_id,
                    'role_id': role_id
                }, room=f'user_{user_id}')
            elif role_id:
                socketio.emit('notification', {
                    'message': message,
                    'user_id': None,
                    'role_id': role_id
                }, room=f'role_{role_id}')
        except Exception as e:
            current_app.logger.error(f"SocketIO emit error: {e}")
        
        return jsonify({
            'success': True,
            'message': 'اعلان با موفقیت ایجاد شد',
            'notification_id': notification.id
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating notification: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطا در ایجاد اعلان',
            'error': str(e)
        }), 500


@notifications_bp.route('/api/mechanic-registered', methods=['POST'])
def mechanic_registered_notification():
    """
    ایجاد نوتیفیکیشن برای ثبت‌نام مکانیک جدید برای همه نقش‌ها
    """
    try:
        data = request.get_json()
        mechanic_id = data.get('mechanic_id')
        telegram_id = data.get('telegram_id')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        phone_number = data.get('phone_number', '')
        
        if not mechanic_id:
            return jsonify({'success': False, 'message': 'شناسه مکانیک الزامی است'}), 400
        
        mechanic = Mechanic.query.get(mechanic_id)
        if not mechanic:
            return jsonify({'success': False, 'message': 'مکانیک یافت نشد'}), 404
        
        # ایجاد نوتیفیکیشن برای همه نقش‌ها
        from app.models import Role
        all_roles = Role.query.all()
        from app import socketio
        notifications = []
        for role in all_roles:
            notification = Notification(
                message=f"مکانیک جدید {first_name} {last_name} (تلگرام: {telegram_id}) ثبت‌نام کرده است",
                role_id=role.id,
                user_id=None
            )
            db.session.add(notification)
            notifications.append((notification, role.id))
        db.session.commit()
        logging.info(f"نوتیفیکیشن برای مکانیک جدید {first_name} {last_name} برای همه نقش‌ها ایجاد شد")
        # ارسال real-time به همه نقش‌ها
        try:
            for notification, role_id in notifications:
                socketio.emit('notification', {
                    'message': notification.message,
                    'user_id': None,
                    'role_id': role_id
                }, room=f'role_{role_id}')
        except Exception as e:
            current_app.logger.error(f"SocketIO emit error: {e}")
        
        return jsonify({
            'success': True,
            'message': 'نوتیفیکیشن برای همه نقش‌ها ایجاد شد'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating mechanic notification: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطا در ایجاد نوتیفیکیشن',
            'error': str(e)
        }), 500


@notifications_bp.route('/api/customer-registered', methods=['POST'])
def customer_registered_notification():
    """
    ایجاد نوتیفیکیشن برای ثبت‌نام مشتری جدید
    """
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        telegram_id = data.get('telegram_id')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        phone_number = data.get('phone_number', '')
        
        if not customer_id:
            return jsonify({'success': False, 'message': 'شناسه مشتری الزامی است'}), 400
        
        from app.models import Customer
        customer = Customer.query.get(customer_id)
        if not customer:
            return jsonify({'success': False, 'message': 'مشتری یافت نشد'}), 404
        
        # ایجاد نوتیفیکیشن برای نقش ادمین
        from app.models import Role
        admin_role = Role.query.filter_by(name='admin').first()
        
        if admin_role:
            notification = Notification(
                message=f"مشتری جدید {first_name} {last_name} (تلگرام: {telegram_id}) ثبت‌نام کرده است",
                role_id=admin_role.id,
                user_id=None
            )
            db.session.add(notification)
            db.session.commit()
            logging.info(f"نوتیفیکیشن برای مشتری جدید {first_name} {last_name} ایجاد شد")
        
        return jsonify({
            'success': True,
            'message': 'نوتیفیکیشن ایجاد شد'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating customer notification: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطا در ایجاد نوتیفیکیشن',
            'error': str(e)
        }), 500


@notifications_bp.route('/api/order-registered', methods=['POST'])
def order_registered_notification():
    """
    ایجاد نوتیفیکیشن برای ثبت سفارش جدید ربات برای همه نقش‌ها
    """
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        customer_name = data.get('customer_name', '')
        phone_number = data.get('phone_number', '')
        telegram_id = data.get('telegram_id', '')
        
        if not order_id:
            return jsonify({'success': False, 'message': 'شناسه سفارش الزامی است'}), 400
        
        # ایجاد نوتیفیکیشن برای همه نقش‌ها
        from app.models import Role
        all_roles = Role.query.all()
        from app import socketio
        notifications = []
        for role in all_roles:
            notification = Notification(
                message=f"سفارش جدید ربات ثبت شد توسط {customer_name} (تلفن: {phone_number}, تلگرام: {telegram_id})",
                role_id=role.id,
                user_id=None
            )
            db.session.add(notification)
            notifications.append((notification, role.id))
        db.session.commit()
        logging.info(f"نوتیفیکیشن سفارش جدید ربات برای همه نقش‌ها ایجاد شد")
        # ارسال real-time به همه نقش‌ها
        try:
            for notification, role_id in notifications:
                socketio.emit('notification', {
                    'message': notification.message,
                    'user_id': None,
                    'role_id': role_id
                }, room=f'role_{role_id}')
        except Exception as e:
            current_app.logger.error(f"SocketIO emit error: {e}")
        
        return jsonify({
            'success': True,
            'message': 'نوتیفیکیشن سفارش جدید برای همه نقش‌ها ایجاد شد'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating order notification: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'خطا در ایجاد نوتیفیکیشن سفارش',
            'error': str(e)
        }), 500 