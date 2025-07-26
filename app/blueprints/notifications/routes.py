# ---------------------------------------------
# فایل: routes.py (notifications)
# توضیح: مدیریت اعلان‌های سیستم
# ---------------------------------------------

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Notification, Person
from app import db
from app.decorators import permission_required
import logging

notifications_bp = Blueprint('notifications', __name__, template_folder='templates')


@notifications_bp.route('/')
@login_required
def index():
    """
    صفحه اصلی اعلان‌ها
    """
    try:
        unread_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        role_notifications = Notification.query.filter_by(
            role_id=current_user.roles[0].id if current_user.roles else None,
            is_read=False
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        notifications = list(unread_notifications) + list(role_notifications)
        notifications = {n.id: n for n in notifications}.values()
        notifications = sorted(notifications, key=lambda n: n.created_at, reverse=True)
        
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
    دریافت تعداد اعلان‌های خوانده نشده به تفکیک نوع (سفارش جدید�� مکانیک جدید و ...)
    """
    try:
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).all()
        role_notifications = []
        if current_user.roles:
            role_notifications = Notification.query.filter_by(
                role_id=current_user.roles[0].id,
                is_read=False
            ).all()
        all_notifications = {n.id: n for n in (list(user_notifications) + list(role_notifications))}.values()
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
        
        user_notifications = Notification.query.filter_by(
            user_id=current_user.id
        ).order_by(Notification.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        role_notifications = []
        if current_user.roles:
            role_notifications = Notification.query.filter_by(
                role_id=current_user.roles[0].id
            ).order_by(Notification.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        notifications = []
        
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
        role_ids = [role.id for role in current_user.roles] if current_user.roles else []
        if mark_all:
            notifications = Notification.query.filter(
                ((Notification.user_id == current_user.id) |
                 (Notification.role_id.in_(role_ids) if role_ids else False)),
                Notification.is_read == False
            ).all()
        else:
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
        user_deleted = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=True
        ).delete()
        
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
        role_ids = [role.id for role in current_user.roles] if current_user.roles else []
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
        person_id = data.get('person_id')
        telegram_id = data.get('telegram_id')
        full_name = data.get('full_name', '')
        # پشتیبانی از فرمت قدیمی
        if not full_name:
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip()
        
        phone_number = data.get('phone_number', '')
        
        if not person_id:
            return jsonify({'success': False, 'message': 'شناسه شخص الزامی است'}), 400
        
        person = Person.query.get(person_id)
        if not person:
            return jsonify({'success': False, 'message': 'شخص یافت نشد'}), 404
        
        from app.models import Role
        all_roles = Role.query.all()
        notifications = []
        for role in all_roles:
            notification = Notification(
                message=f"مکانیک جدید {full_name} (تلگرام: {telegram_id}) ثبت‌نام کرده است",
                role_id=role.id,
                user_id=None
            )
            db.session.add(notification)
            notifications.append((notification, role.id))
        db.session.commit()
        logging.info(f"نوتیفیکیشن برای مکانیک جدید {full_name} برای همه نقش‌ها ایجاد شد")
        
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
        person_id = data.get('person_id')
        telegram_id = data.get('telegram_id')
        full_name = data.get('full_name', '')
        # پشتیبانی از فرمت قدیمی
        if not full_name:
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip()
        
        phone_number = data.get('phone_number', '')
        
        if not person_id:
            return jsonify({'success': False, 'message': 'شناسه شخص الزامی است'}), 400
        
        person = Person.query.get(person_id)
        if not person:
            return jsonify({'success': False, 'message': 'شخص یافت نشد'}), 404
        
        from app.models import Role
        admin_role = Role.query.filter_by(name='admin').first()
        
        if admin_role:
            notification = Notification(
                message=f"مشتری جدید {full_name} (تلگرام: {telegram_id}) ثبت‌نام کرده است",
                role_id=admin_role.id,
                user_id=None
            )
            db.session.add(notification)
            db.session.commit()
            logging.info(f"نوتیفیکیشن برای مشتری جدید {full_name} ایجاد شد")
        
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
        
        from app.models import Role
        all_roles = Role.query.all()
        notifications = []
        for role in all_roles:
            notification = Notification(
                message=f"سفارش جدید ربات ثبت شد توسط {customer_name}",
                role_id=role.id,
                user_id=None
            )
            db.session.add(notification)
            notifications.append((notification, role.id))
        db.session.commit()
        logging.info(f"نوتیفیکیشن سفارش جدید ربات برای همه نقش‌ها ایجاد شد")
        
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


@notifications_bp.route('/api/notify_order_created', methods=['POST'])
def api_notify_order_created():
    """
    دریافت اعلان ثبت سفارش جدید از ربات و ثبت نوتیفیکیشن برای ادمین‌ها
    """
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        telegram_id = data.get('telegram_id')
        role = data.get('role')
        if not order_id or not telegram_id:
            return jsonify({'success': False, 'message': 'اطلاعات ناقص'}), 400
        from app.models import Notification
        notif = Notification(
            message=f'سفارش جدید از ربات تو��ط {role or "کاربر"} (تلگرام آیدی: {telegram_id}) ثبت شد. شناسه سفارش: {order_id}',
            user_id=None
        )
        from app import db
        db.session.add(notif)
        db.session.commit()
        return jsonify({'success': True, 'message': 'اعلان سفارش جدید ثبت شد'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطا: {e}'})


@notifications_bp.route('/api/notifications/check', methods=['GET'])
@login_required
def check_notifications():
    """
    API برای بررسی اعلان‌های جدید (جایگزین SocketIO)
    """
    try:
        from datetime import datetime, timedelta

        # بررسی اعلان‌های 5 دقیقه اخیر
        five_minutes_ago = datetime.now() - timedelta(minutes=5)

        # شمارش اعلان‌های جدید
        new_notifications = Notification.query.filter(
            Notification.user_id == current_user.id,
            Notification.created_at >= five_minutes_ago,
            Notification.is_read == False
        ).count()

        # دریافت آخرین اعلان
        latest_notification = Notification.query.filter(
            Notification.user_id == current_user.id,
            Notification.created_at >= five_minutes_ago,
            Notification.is_read == False
        ).order_by(Notification.created_at.desc()).first()

        return jsonify({
            'has_new_notifications': new_notifications > 0,
            'count': new_notifications,
            'latest_message': latest_notification.message if latest_notification else None
        })

    except Exception as e:
        return jsonify({
            'has_new_notifications': False,
            'count': 0,
            'latest_message': None
        })