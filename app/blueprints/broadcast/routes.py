# ---------------------------------------------
# فایل: routes.py (broadcast)
# توضیح: مدیریت پیام‌های همگانی و ارسال به مشتریان
# ---------------------------------------------

from flask import render_template, Blueprint, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from app import db
from app.models import BroadcastMessage, Customer, CustomerSegment
from app.forms import BroadcastMessageForm
from app.decorators import permission_required
import json
import datetime
from datetime import timedelta
import requests
import os

broadcast_bp = Blueprint('broadcast', __name__, template_folder='templates')


@broadcast_bp.route('/')
@login_required
@permission_required('manage_broadcasts')
def index():
    """
    صفحه اصلی پیام‌های همگانی
    """
    messages = BroadcastMessage.query.order_by(
        desc(BroadcastMessage.created_at)).all()
    # افزودن نام ارسال‌کننده و هدف قابل نمایش
    display_messages = []
    from app.models import User, Customer, Mechanic
    import json
    for msg in messages:
        # نام ارسال‌کننده
        sender = msg.created_by_user.name if msg.created_by_user and msg.created_by_user.name else (msg.created_by_user.username if msg.created_by_user else '---')
        # هدف ارسال
        if msg.target_type == 'all':
            target_display = 'همه مشتریان'
        elif msg.target_type == 'mechanic_all':
            target_display = 'همه مکانیک‌ها'
        elif msg.target_type == 'specific' and msg.target_customers:
            try:
                ids = json.loads(msg.target_customers)
                customers = Customer.query.filter(Customer.id.in_(ids)).all()
                target_display = '، '.join([
                    (f"{c.first_name} {c.last_name}".strip() if c.first_name or c.last_name else c.phone_number)
                    for c in customers
                ]) if customers else 'مشتری خاص'
            except Exception:
                target_display = 'مشتری خاص'
        elif msg.target_type == 'mechanic_specific' and msg.target_customers:
            try:
                ids = json.loads(msg.target_customers)
                mechanics = Mechanic.query.filter(Mechanic.id.in_(ids)).all()
                target_display = '، '.join([
                    (f"{m.first_name} {m.last_name}".strip() if m.first_name or m.last_name else m.phone_number)
                    for m in mechanics
                ]) if mechanics else 'مکانیک خاص'
            except Exception:
                target_display = 'مکانیک خاص'
        else:
            target_display = '---'
        display_messages.append({'msg': msg, 'sender': sender, 'target_display': target_display})
    return render_template('broadcast.html',
                           title="پیام‌های همگانی",
                           messages=display_messages)


@broadcast_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('manage_broadcasts')
def create_message():
    """
    ایجاد پیام همگانی جدید
    """
    form = BroadcastMessageForm()

    if form.validate_on_submit():
        # اطمینان از اینکه فقط پیش‌نویس موقع ثبت پیام مجاز است و scheduled_at پردازش نشود
        message = BroadcastMessage(title=form.title.data,
                                   message=form.message.data,
                                   message_type=form.message_type.data,
                                   target_type=form.target_type.data,
                                   target_customers=form.target_customers.data,
                                   status='draft', # فقط پیش‌نویس مجاز است
                                   created_by=current_user.id)

        db.session.add(message)
        db.session.commit()

        flash('پیام همگانی با موفقیت ایجاد شد.', 'success')
        return redirect(url_for('broadcast.index'))

    return render_template('create.html',
                           title="ایجاد پیام همگانی",
                           form=form)


@broadcast_bp.route('/edit/<int:message_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_broadcasts')
def edit_message(message_id):
    """
    ویرایش پیام همگانی
    """
    message = db.session.get(BroadcastMessage, message_id)
    if not message:
        flash('پیام یافت نشد.', 'error')
        return redirect(url_for('broadcast.index'))

    form = BroadcastMessageForm(obj=message)

    if form.validate_on_submit():
        message.title = form.title.data
        message.message = form.message.data
        message.message_type = form.message_type.data
        message.target_type = form.target_type.data
        message.target_customers = form.target_customers.data
        message.status = form.status.data
        message.scheduled_at = form.scheduled_at.data

        db.session.commit()
        flash('پیام همگانی با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('broadcast.index'))

    return render_template('edit.html',
                           title="ویرایش پیام همگانی",
                           form=form,
                           message=message)


@broadcast_bp.route('/send/<int:message_id>', methods=['POST'])
@login_required
@permission_required('manage_broadcasts')
def send_message(message_id):
    """
    ارسال پیام همگانی به مشتریان یا مکانیک‌های هدف
    """
    from flask import request
    message = db.session.get(BroadcastMessage, message_id)
    if not message:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'پیام یافت نشد'}), 404
        else:
            flash('پیام یافت نشد.', 'error')
            return redirect(url_for('broadcast.index'))

    try:
        # دریافت لیست مشتریان یا مکانیک‌های هدف
        if message.target_type.startswith('mechanic'):
            targets = get_target_mechanics(message)
        else:
            targets = get_target_customers(message)

        # ارسال پیام به هر گیرنده
        success_count = 0
        skipped_count = 0
        for target in targets:
            telegram_id = getattr(target, 'telegram_id', None)
            if not telegram_id:
                print(f"[Broadcast] گیرنده {getattr(target, 'id', None)} تلگرام آیدی ندارد و پیام ارسال نشد.")
                skipped_count += 1
                continue
            if send_telegram_message(telegram_id, message):
                success_count += 1

        # بروزرسانی آمار
        message.status = 'sent'
        message.sent_at = datetime.datetime.utcnow()
        message.total_sent = len(targets)
        message.total_delivered = success_count

        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'sent_count': success_count})
        else:
            flash(f'پیام به {success_count} گیرنده ارسال شد.', 'success')
            if skipped_count:
                flash(f'{skipped_count} گیرنده تلگرام آیدی نداشتند و پیام دریافت نکردند.', 'warning')
            return redirect(url_for('broadcast.index'))

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': str(e)}), 500
        else:
            flash(f'خطا در ارسال پیام: {str(e)}', 'error')
            return redirect(url_for('broadcast.index'))


@broadcast_bp.route('/delete/<int:message_id>', methods=['POST'])
@login_required
@permission_required('manage_broadcasts')
def delete_message(message_id):
    """
    حذف پیام همگانی
    """
    message = db.session.get(BroadcastMessage, message_id)
    if not message:
        flash('پیام یافت نشد.', 'error')
        return redirect(url_for('broadcast.index'))

    db.session.delete(message)
    db.session.commit()

    flash('پیام همگانی با موفقیت حذف شد.', 'success')
    return redirect(url_for('broadcast.index'))


@broadcast_bp.route('/api/customer-segments')
@login_required
@permission_required('manage_broadcasts')
def api_customer_segments():
    """
    API برای دریافت تقسیم‌بندی مشتریان
    """
    segments = [{
        'id': 'all',
        'name': 'همه مشتریان',
        'count': Customer.query.count()
    }, {
        'id': 'new',
        'name': 'مشتریان جدید',
        'count': Customer.query.filter(
            Customer.registration_date >= datetime.datetime.now() - timedelta(days=30)).count()
    }, {
        'id': 'active',
        'name': 'مشتریان فعال',
        'count': Customer.query.filter(
            Customer.last_order_date >= datetime.datetime.now() - timedelta(days=90)).count()
    }, {
        'id': 'inactive',
        'name': 'مشتریان غیرفعال',
        'count': Customer.query.filter(
            Customer.last_order_date < datetime.datetime.now() - timedelta(days=90)).count()
    }]

    return jsonify(segments)


@broadcast_bp.route('/api/customers/<segment_id>')
@login_required
@permission_required('manage_broadcasts')
def api_customers_by_segment(segment_id):
    """API برای دریافت مشتریان بر اساس تقسیم‌بندی"""
    if segment_id == 'all':
        customers = Customer.query.all()
    elif segment_id == 'new':
        customers = Customer.query.filter(
            Customer.registration_date >= datetime.datetime.now() -
            timedelta(days=30)).all()
    elif segment_id == 'active':
        customers = Customer.query.filter(
            Customer.last_order_date >= datetime.datetime.now() -
            timedelta(days=90)).all()
    elif segment_id == 'inactive':
        customers = Customer.query.filter(
            Customer.last_order_date < datetime.datetime.now() -
            timedelta(days=90)).all()
    else:
        customers = []

    return jsonify([{
        'id': customer.id,
        'name': customer.full_name,
        'telegram_id': customer.telegram_id,
        'level': customer.customer_level
    } for customer in customers])


@broadcast_bp.route('/api/mechanics')
@login_required
@permission_required('manage_broadcasts')
def api_mechanics():
    """API برای دریافت لیست مکانیک‌های تایید شده جهت انتخاب در پیام همگانی با پشتیبانی از جستجو فقط روی first_name و phone_number"""
    from app.models import Mechanic
    q = request.args.get('q', '').strip()
    query = Mechanic.query.filter_by(is_approved=True)
    if q:
        query = query.filter(
            (Mechanic.first_name.ilike(f'%{q}%')) |
            (Mechanic.phone_number.ilike(f'%{q}%'))
        )
    mechanics = query.order_by(Mechanic.first_name).limit(20).all()
    return jsonify([
        {
            'id': mechanic.id,
            'name': mechanic.full_name,
            'phone_number': mechanic.phone_number,
            'telegram_id': mechanic.telegram_id
        }
        for mechanic in mechanics
    ])


def get_target_customers(message):
    """دریافت لیست مشتریان هدف"""
    if message.target_type == 'all':
        return Customer.query.all()
    elif message.target_type == 'specific':
        if message.target_customers:
            customer_ids = json.loads(message.target_customers)
            return Customer.query.filter(Customer.id.in_(customer_ids)).all()
        return []
    else:
        return []


def get_target_mechanics(message):
    """دریافت لیست مکانیک‌های هدف"""
    from app.models import Mechanic
    if message.target_type == 'mechanic_all':
        return Mechanic.query.filter_by(is_approved=True).all()
    elif message.target_type == 'mechanic_specific':
        if message.target_customers:
            mechanic_ids = json.loads(message.target_customers)
            return Mechanic.query.filter(Mechanic.id.in_(mechanic_ids)).all()
    return []


def send_telegram_message(telegram_id, message):
    """ارسال پیام به تلگرام (واقعی)"""
    try:
        import os
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("[Broadcast] TELEGRAM_BOT_TOKEN env variable not set!")
            return False
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        data = {
            'chat_id': telegram_id,
            'text': f"{message.title}\n\n{message.message}",
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data)
        try:
            result = response.json()
        except Exception as e:
            print(f"[Broadcast] Error parsing Telegram response: {e}, text: {response.text}")
            return False
        print(f"[Broadcast] ارسال پیام به chat_id={telegram_id}، پاسخ تلگرام: {result}")
        if not result.get('ok'):
            print(f"[Broadcast] ارسال پیام به {telegram_id} ناموفق بود: error_code={result.get('error_code')}, description={result.get('description')}")
        return result.get('ok', False)
    except Exception as e:
        print(f"Error sending message to {telegram_id}: {str(e)}")
        return False


@broadcast_bp.route('/analytics')
@login_required
@permission_required('manage_broadcasts')
def analytics():
    """آمار پیام‌های همگانی"""
    # آمار کلی
    total_messages = BroadcastMessage.query.count()
    sent_messages = BroadcastMessage.query.filter(
        BroadcastMessage.status == 'sent').count()

    total_sent = db.session.query(func.sum(
        BroadcastMessage.total_sent)).scalar() or 0
    total_delivered = db.session.query(
        func.sum(BroadcastMessage.total_delivered)).scalar() or 0

    # پیام‌های اخیر
    recent_messages = BroadcastMessage.query.order_by(
        desc(BroadcastMessage.created_at)).limit(10).all()

    # آمار بر اساس نوع هدف
    target_stats = db.session.query(
        BroadcastMessage.target_type,
        func.count(BroadcastMessage.id).label('count'),
        func.sum(BroadcastMessage.total_sent).label('total_sent')).group_by(
            BroadcastMessage.target_type).all()

    return render_template('analytics.html',
                           title="آمار پیام‌های همگانی",
                           total_messages=total_messages,
                           sent_messages=sent_messages,
                           total_sent=total_sent,
                           total_delivered=total_delivered,
                           recent_messages=recent_messages,
                           target_stats=target_stats)
