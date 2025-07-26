# ---------------------------------------------
# فایل: routes.py (customers)
# توضیح: مدیریت مشتریان و نمایش جزئیات هر مشتری
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request, jsonify
from flask_login import login_required
from app import db
from app.models import Person, InStoreOrder, Order, BotOrder
from app.decorators import permission_required
from sqlalchemy import or_
import json

customers_bp = Blueprint('customers', __name__, template_folder='templates')


@customers_bp.route('/')
@login_required
@permission_required('manage_customers')  # ⬇️ اعمال دسترسی
def index():
    """
    صفحه اصلی مدیریت مشتریان که لیست آن‌ها را نمایش می‌دهد.
    """
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 15
    filters = []
    if search_query:
        filters.append(Person.full_name.ilike(f'%{search_query}%'))
        filters.append(Person.phone_number.ilike(f'%{search_query}%'))
        customers = Person.query.filter(
            Person.person_type == 'customer',
            or_(*filters)
        ).order_by(Person.id.desc()).paginate(page=page, per_page=per_page)
    else:
        customers = Person.query.filter(
            Person.person_type == 'customer'
        ).order_by(Person.id.desc()).paginate(page=page, per_page=per_page)

    # ساخت لیست جدید با اطلاعات اولین سفارش برای هر مشتری
    customers_with_first_order = []
    for customer in customers.items:
        if hasattr(customer, 'update_first_order_info'):
            customer.update_first_order_info()
            # ذخیره تغییرات در دیتابیس
            db.session.add(customer)
        customers_with_first_order.append({
            'customer': customer,
            'first_order_date': getattr(customer, 'first_order_date', None),
            'first_order_type': getattr(customer, 'first_order_type', None)
        })

    # ذخیره همه تغییرات
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Error updating customer info: {e}")

    if request.args.get('ajax') == '1':
        # خروجی JSON برای جستجوی مشتری خاص
        customers_json = []
        for item in customers_with_first_order:
            customer = item['customer']
            customers_json.append({
                'id': customer.id,
                'full_name': customer.full_name,
                'phone_number': customer.phone_number
            })
        return {'customers': customers_json}

    return render_template('customers.html',
                           customers=customers,
                           customers_with_first_order=customers_with_first_order,
                           title="مدیریت مشتریان",
                           search_query=search_query)


@customers_bp.route('/view/<int:customer_id>')
@login_required
@permission_required('manage_customers')  # ⬇️ اعمال دسترسی
def view_customer(customer_id):
    """
    نمایش جزئیات کامل یک مشتری خاص و سفارش‌های او.
    """
    customer = db.session.get(Person, customer_id)
    if not customer or customer.person_type != 'customer':
        flash('مشتری مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('customers.index'))

    # گرفتن سفارش‌های مشتری (تلگرام)
    customer_orders = Order.query.filter_by(person_id=customer.id).order_by(Order.order_date.desc()).all()
    # گرفتن سفارش‌های حضوری
    instore_orders = InStoreOrder.query.filter_by(person_id=customer.id).order_by(InStoreOrder.created_at.desc()).all()
    # گرفتن سفارش‌های ربات (بر اساس شماره تلفن)
    bot_orders = BotOrder.query.filter_by(person_id=customer.id).order_by(BotOrder.created_at.desc()).all()
    
    # ترکیب و مرتب‌سازی همه سفارشات
    all_orders = []
    for o in customer_orders:
        all_orders.append({
            'id': o.id,
            'date': o.order_date,
            'total_price': o.total_price,
            'status': o.status,
            'type': 'تلگرام',
            'view_url': url_for('orders.view_order', order_id=o.id)
        })
    for i in instore_orders:
        all_orders.append({
            'id': i.id,
            'date': i.created_at,
            'total_price': i.total_price,
            'status': i.status,
            'type': 'حضوری',
            'view_url': None
        })
    for b in bot_orders:
        all_orders.append({
            'id': b.id,
            'date': b.created_at,
            'total_price': b.total_amount,
            'status': b.status,
            'type': 'ربات',
            'view_url': url_for('bot_orders.detail', order_id=b.id)
        })
    all_orders.sort(key=lambda x: x['date'], reverse=True)
    return render_template('view_customer.html',
                           customer=customer,
                           orders=all_orders,
                           title=f"جزئیات مشتری: {customer.full_name}")


@customers_bp.route('/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_customers')
def edit_customer(customer_id):
    customer = db.session.get(Person, customer_id)
    if not customer or customer.person_type != 'customer':
        flash('مشتری مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('customers.index'))
    if request.method == 'POST':
        from app.utils import fa_to_en_digits
        customer.full_name = request.form.get('full_name', '').strip()
        customer.username = request.form.get('username', '').strip()
        customer.phone_number = fa_to_en_digits(request.form.get('phone_number', '').strip())
        customer.address = request.form.get('address', '').strip()
        customer.city = request.form.get('city', '').strip()
        customer.province = request.form.get('province', '').strip()
        customer.postal_code = request.form.get('postal_code', '').strip()
        db.session.commit()
        flash('اطلاعات مشتری با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('customers.view_customer', customer_id=customer.id))
    return render_template('edit_customer.html', customer=customer, title='ویرایش مشتری')


@customers_bp.route('/api/register', methods=['POST'])
def api_register_customer():
    """
    API برای ثبت مشتری جدید (برای ربات یا سایر کلاینت‌ها)
    ورودی: full_name, phone_number, address, telegram_id, username
    """
    from app.models import Notification, Role, db
    data = request.get_json()
    full_name = data.get('full_name', '').strip()
    phone_number = data.get('phone_number', '').strip()
    address = data.get('address', '').strip()
    telegram_id = data.get('telegram_id')
    username = data.get('username', '').strip()
    
    if not full_name or not phone_number:
        return {'success': False, 'message': 'نام و شماره تلفن الزامی است.'}, 400
    
    # بررسی تکراری نبودن شماره تلفن
    existing = Person.query.filter_by(phone_number=phone_number, person_type='customer').first()
    if existing:
        # اگر شماره تلفن قبلاً ثبت شده، telegram_id را به آن اضافه کن (در صورت نبود)
        if telegram_id and not existing.telegram_id:
            existing.telegram_id = telegram_id
            db.session.commit()
            return {'success': True, 'message': 'مشتری با موفقیت به‌روزرسانی شد', 'customer_id': existing.id}, 200
        else:
            return {'success': False, 'message': 'این شماره قبلاً ثبت شده است.'}, 400
    
    # بررسی تکراری نبودن telegram_id
    if telegram_id:
        existing_telegram = Person.query.filter_by(telegram_id=telegram_id, person_type='customer').first()
        if existing_telegram:
            return {'success': False, 'message': 'این کاربر قبلاً ثبت شده است.'}, 400
    
    province = data.get('province', '').strip()
    city = data.get('city', '').strip()
    postal_code = data.get('postal_code', '').strip()
    customer = Person(
        telegram_id=telegram_id,
        full_name=full_name,
        phone_number=phone_number,
        address=address,
        username=username,
        province=province,
        city=city,
        postal_code=postal_code,
        person_type='customer'
    )
    db.session.add(customer)
    db.session.commit()
    
    # بروزرسانی اطلاعات اولین سفارش
    if hasattr(customer, 'update_first_order_info'):
        customer.update_first_order_info()
        db.session.add(customer)
        db.session.commit()

    # ارسال نوتیفیکیشن ثبت‌نام مشتری به صورت داخلی
    try:
        import requests
        from flask import url_for
        notify_url = url_for('notifications.customer_registered_notification', _external=True)
        payload = {
            'person_id': customer.id,
            'telegram_id': customer.telegram_id,
            'full_name': customer.full_name,
            'phone_number': customer.phone_number
        }
        # ارسال درخواست داخلی (localhost)
        requests.post(notify_url, json=payload, timeout=3)
    except Exception as notif_err:
        import logging
        logging.error(f"[CUSTOMER_REGISTER] Notification error: {notif_err}")

    return {'success': True, 'message': 'مشتری با موفقیت ثبت شد.'}


@customers_bp.route('/api/update-all-types', methods=['POST'])
@login_required
@permission_required('manage_customers')
def update_all_customer_types():
    """
    به‌روزرسانی نوع همه مشتریان بر اساس اولین سفارش آن‌ها
    """
    try:
        customers = Person.query.filter_by(person_type='customer').all()
        updated_count = 0

        for customer in customers:
            if hasattr(customer, 'update_first_order_info'):
                customer.update_first_order_info()
                db.session.add(customer)
                updated_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{updated_count} مشتری به‌روزرسانی شد',
            'updated_count': updated_count
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Error updating all customer types: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در به‌روزرسانی مشتریان',
            'error': str(e)
        }), 500


@customers_bp.route('/api/fix-bot-orders', methods=['POST'])
@login_required
@permission_required('manage_customers')
def fix_bot_orders():
    """
    اصلاح ارتباط سفارشات ربات با مشتریان
    """
    try:
        from app.models import BotOrder

        # پیدا کردن سفارشات ربات بدون person_id
        orphan_orders = BotOrder.query.filter(BotOrder.person_id.is_(None)).all()
        fixed_count = 0

        for order in orphan_orders:
            customer = None

            # ابتدا بر اساس telegram_id جستجو کن
            if order.telegram_id:
                customer = Person.query.filter_by(
                    telegram_id=order.telegram_id,
                    person_type='customer'
                ).first()

            # اگر پیدا نشد، بر اساس شماره تلفن جستجو کن
            if not customer and order.customer_phone:
                customer = Person.query.filter_by(
                    phone_number=order.customer_phone,
                    person_type='customer'
                ).first()

            # اگر هنوز پیدا نشد، مشتری جدید ایجاد کن
            if not customer and order.customer_phone:
                customer = Person(
                    full_name=order.customer_name or 'نامشخص',
                    phone_number=order.customer_phone,
                    telegram_id=order.telegram_id,
                    person_type='customer',
                    address=order.customer_address
                )
                db.session.add(customer)
                db.session.flush()  # برای گرفتن ID

            if customer:
                order.person_id = customer.id
                fixed_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{fixed_count} سفارش ربات اصلاح شد',
            'fixed_count': fixed_count
        })

    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Error fixing bot orders: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در اصلاح سفارشات ربات',
            'error': str(e)
        }), 500


@customers_bp.route('/api/status', methods=['GET'])
def customer_status():
    """
    دریافت وضعیت مشتری بر اساس telegram_id
    ورودی: ?telegram_id=...
    خروجی: {"success": true/false, ...}
    """
    telegram_id = request.args.get('telegram_id', type=int)
    if not telegram_id:
        return jsonify({'success': False, 'message': 'telegram_id الزامی است'}), 400
    
    customer = Person.query.filter_by(telegram_id=telegram_id, person_type='customer').first()
    if not customer:
        return jsonify({'success': False, 'message': 'مشتری یافت نشد'}), 404
    
    return jsonify({
        'success': True,
        'status': 'approved',  # مشتریان به طور خودکار تایید شده هستند
        'customer_id': customer.id,
        'full_name': customer.full_name,
        'phone_number': customer.phone_number
    })


@customers_bp.route('/api/create', methods=['POST'])
def api_create_customer():
    """
    API برای ایجاد مشتری جدید از ربات تلگرام
    ورودی: full_name, phone_number, address, telegram_id, username
    """
    try:
        data = request.get_json()

        telegram_id = data.get('telegram_id')
        full_name = data.get('full_name', '').strip()
        username = data.get('username', '').strip()
        phone_number = data.get('phone_number', '').strip()
        province = data.get('province', '').strip()
        city = data.get('city', '').strip()
        postal_code = data.get('postal_code', '').strip()

        if not telegram_id:
            return jsonify({'error': 'telegram_id الزامی است'}), 400
        # بررسی تکراری نبودن telegram_id
        existing_telegram = Person.query.filter_by(telegram_id=telegram_id, person_type='customer').first()
        if existing_telegram:
            return jsonify({
                'success': True,
                'message': 'تری قبلاً در سیستم ثبت شده است',
                'customer_id': existing_telegram.id
            })

        # بررسی تکراری نبودن شماره تلفن (اگر ارائه شده)
        if phone_number:
            existing_phone = Person.query.filter_by(phone_number=phone_number, person_type='customer').first()
            if existing_phone:
                # اگر شماره تلفن قبلاً ثبت شده، telegram_id را به آن اضافه کن
                existing_phone.telegram_id = telegram_id
                existing_phone.username = username
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'مشتری با موفقیت به‌روزرسانی شد',
                    'customer_id': existing_phone.id
                })

        # ایجاد مشتری جدید
        customer = Person(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            phone_number=phone_number,
            province=province,
            city=city,
            postal_code=postal_code,
            person_type='customer'
        )

        db.session.add(customer)
        db.session.commit()

        # ارسال منوی جدید به مشتری
        if telegram_id:
            import os
            from dotenv import load_dotenv
            load_dotenv(os.path.join(os.path.dirname(__file__), '../../../bot/bot_config.env'))
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if bot_token:
                import requests
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                text = "🛒 منوی مشتری\n\nلطفاً گزینه مورد نظر را انتخاب کنید:"
                payload = {
                    "chat_id": int(telegram_id),
                    "text": text,
                    "reply_markup": {
                        "keyboard": [
                            [{"text": "🛍️ خرید محصول"}],
                            [{"text": "📋 سفارشات من"}],
                            [{"text": "📞 پشتیبانی"}],
                            [{"text": "ℹ️ راهنما"}]
                        ],
                        "resize_keyboard": True,
                        "one_time_keyboard": False
                    }
                }
                try:
                    resp = requests.post(url, json=payload, timeout=5)
                    if resp.status_code == 200:
                        import logging
                        logging.info(f"✅ منوی جدید به مشتری {telegram_id} ارسال شد")
                    else:
                        import logging
                        logging.error(f'❌ Telegram menu API error: {resp.status_code} - {resp.text}')
                except Exception as e:
                    import logging
                    logging.error(f"❌ خطا در ارسال منوی تلگرام: {e}")

        return jsonify({
            'success': True,
            'message': 'مشتری با موفقیت ایجاد شد',
            'customer_id': customer.id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@customers_bp.route('/delete/<int:customer_id>', methods=['DELETE'])
@login_required
@permission_required('manage_customers')
def delete_customer(customer_id):
    """
    حذف مشتری
    """
    try:
        customer = db.session.get(Person, customer_id)
        if not customer or customer.person_type != 'customer':
            return jsonify({
                'success': False,
                'message': 'مشتری مورد نظر یافت نشد.'
            }), 404

        # بررسی وجود سفارشات مرتبط
        from app.models import Order, InStoreOrder, BotOrder

        # شمارش سفارشات
        telegram_orders = Order.query.filter_by(customer_id=customer.id).count()
        instore_orders = InStoreOrder.query.filter_by(person_id=customer.id).count()
        bot_orders = BotOrder.query.filter_by(customer_phone=customer.phone_number).count()

        total_orders = telegram_orders + instore_orders + bot_orders

        if total_orders > 0:
            return jsonify({
                'success': False,
                'message': f'این مشتری دارای {total_orders} سفارش است و قابل حذف نیست. ابتدا سفارشات را حذف کنید.'
            }), 400

        # حذف مشتری
        customer_name = customer.full_name
        db.session.delete(customer)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'مشتری "{customer_name}" با موفقیت حذف شد.'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'خطا در حذف مشتری: {str(e)}'
        }), 500
