from flask import jsonify, request, abort
from flask_login import login_required, current_user
from . import api_bp
from app.models import InventoryProduct, Notification, BotOrder, BotOrderItem, Person
from app import db

API_TOKEN = 'testtoken123'  # برای تست، بعداً JWT جایگزین شود

def require_api_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth or not auth.startswith('Bearer '):
            abort(401, description='Missing or invalid token')
        token = auth.split(' ')[1]
        if token != API_TOKEN:
            abort(401, description='Invalid token')
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/health', methods=['GET'])
def api_health():
    return jsonify({'status': 'ok'}), 200

# مثال endpoint محافظت‌شده
@api_bp.route('/protected', methods=['GET'])
@require_api_auth
def protected():
    return jsonify({'message': 'Access granted'}), 200

# CRUD endpoints for User, Product, Order, Customer, ... will be added here
@api_bp.route('/products', methods=['GET'])
@require_api_auth
def get_products():
    products = InventoryProduct.query.all()
    return jsonify([
        {
            'id': p.id,
            'name': p.name,
            'price': p.batches.first().purchase_price if p.batches.first() else 0,
            'stock': p.available_quantity
        } for p in products
    ])


@api_bp.route('/notifications/check', methods=['GET'])
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


@api_bp.route('/debug/orders', methods=['GET'])
@login_required
def debug_orders():
    """
    API دیباگ برای بررسی سفارشات
    """
    try:
        from app.models import BotOrder, Person

        telegram_id = request.args.get('telegram_id', type=int)
        person_id = request.args.get('person_id', type=int)

        result = {
            'telegram_id': telegram_id,
            'person_id': person_id,
            'person_info': None,
            'bot_orders': [],
            'debug_info': {}
        }

        # بررسی اطلاعات شخص
        if telegram_id:
            person = Person.query.filter_by(telegram_id=telegram_id).first()
            if person:
                result['person_info'] = {
                    'id': person.id,
                    'full_name': person.full_name,
                    'phone_number': person.phone_number,
                    'telegram_id': person.telegram_id,
                    'person_type': person.person_type
                }
                person_id = person.id

        # بررسی سفارشات ربات
        if person_id:
            bot_orders_by_person = BotOrder.query.filter_by(person_id=person_id).all()
            result['debug_info']['orders_by_person_id'] = len(bot_orders_by_person)

            for order in bot_orders_by_person:
                result['bot_orders'].append({
                    'id': order.id,
                    'person_id': order.person_id,
                    'telegram_id': order.telegram_id,
                    'customer_name': order.customer_name,
                    'customer_phone': order.customer_phone,
                    'status': order.status,
                    'total_amount': order.total_amount,
                    'created_at': str(order.created_at)
                })

        if telegram_id:
            bot_orders_by_telegram = BotOrder.query.filter_by(telegram_id=telegram_id).all()
            result['debug_info']['orders_by_telegram_id'] = len(bot_orders_by_telegram)

        # آمار کلی
        result['debug_info']['total_bot_orders'] = BotOrder.query.count()
        result['debug_info']['total_persons'] = Person.query.filter_by(person_type='customer').count()

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@api_bp.route('/create_order', methods=['POST'])
def api_create_order():
    """
    API برای ایجاد سفارش جدید (بدون احراز هویت برای ربات)
    """
    import logging
    try:
        from app.models import BotOrder, BotOrderItem, Person
        import json
        import os

        logging.info(f"[API_CREATE_ORDER] Received request with content_type: {request.content_type}")
        logging.info(f"[API_CREATE_ORDER] Form data keys: {list(request.form.keys())}")
        logging.info(f"[API_CREATE_ORDER] Files: {list(request.files.keys())}")

        data = request.form
        items_json = data.get('items')
        if not items_json:
            logging.error("[API_CREATE_ORDER] No items data provided")
            return jsonify({'success': False, 'message': 'اطلاعات آیتم‌ها ناقص'}), 400

        try:
            items = json.loads(items_json)
            logging.info(f"[API_CREATE_ORDER] Parsed {len(items)} items")
        except Exception as e:
            logging.error(f"[API_CREATE_ORDER] Error parsing items JSON: {e}")
            return jsonify({'success': False, 'message': f'خطا در خواندن آیتم‌ها: {e}'}), 400

        customer_phone = data.get('customer_phone')
        customer_name = data.get('customer_name')
        customer_address = data.get('customer_address')
        telegram_id = data.get('telegram_id')
        mechanic_id = data.get('mechanic_id')

        logging.info(f"[API_CREATE_ORDER] Customer data - phone: {customer_phone}, name: {customer_name}, telegram_id: {telegram_id}, mechanic_id: {mechanic_id}")

        # اگر مکانیک سفارش ثبت می‌کند، شماره تلفن اختیاری است
        is_mechanic_order = bool(mechanic_id)

        if not customer_phone and not is_mechanic_order:
            logging.error("[API_CREATE_ORDER] No customer phone provided for non-mechanic order")
            return jsonify({'success': False, 'message': 'شماره تلفن مشتری الزامی است'}), 400

        # پیدا کردن یا ایجاد مشتری
        customer = None
        if customer_phone:
            customer = Person.query.filter_by(phone_number=customer_phone, person_type='customer').first()

        if not customer and telegram_id:
            # اگر شماره تلفن نداریم، با telegram_id جستجو کنیم
            customer = Person.query.filter_by(telegram_id=telegram_id, person_type='customer').first()

        if not customer:
            # ایجاد مشتری جدید
            if is_mechanic_order and not customer_phone:
                # برای سفارش مکانیک بدون شماره تلفن، شماره پیش‌فرض بگذار
                customer_phone = f"mechanic_{telegram_id}"
                customer_name = customer_name or f"مشتری مکانیک {telegram_id}"

            logging.info(f"[API_CREATE_ORDER] Creating new customer: {customer_name} - {customer_phone}")
            customer = Person(
                full_name=customer_name or 'نامشخص',
                phone_number=customer_phone,
                person_type='customer',
                address=customer_address or None,
                telegram_id=telegram_id
            )
            db.session.add(customer)
            db.session.commit()
            logging.info(f"[API_CREATE_ORDER] New customer created with ID: {customer.id}")
        else:
            logging.info(f"[API_CREATE_ORDER] Found existing customer: {customer.full_name} (ID: {customer.id})")
            # به‌روزرسانی telegram_id اگر وجود نداشته باشد
            if telegram_id and not customer.telegram_id:
                customer.telegram_id = telegram_id
                db.session.commit()
                logging.info(f"[API_CREATE_ORDER] Updated customer telegram_id: {telegram_id}")

        # پردازش mechanic_id
        mechanic_person_id = None
        if mechanic_id:
            if not str(mechanic_id).isdigit() or len(str(mechanic_id)) > 6:
                mechanic = Person.query.filter_by(telegram_id=mechanic_id, person_type='mechanic').first()
                if mechanic:
                    mechanic_person_id = mechanic.id

        # ایجاد سفارش
        total_amount = sum(item.get('total_price', 0) for item in items)
        logging.info(f"[API_CREATE_ORDER] Creating order with total_amount: {total_amount}")

        order = BotOrder(
            customer_phone=customer_phone,
            customer_name=customer_name or customer.full_name,
            customer_address=customer_address,
            telegram_id=telegram_id,
            mechanic_person_id=mechanic_person_id,
            person_id=customer.id,
            order_items=json.dumps(items),
            total_amount=total_amount,
            status='در انتظار بررسی'
        )

        db.session.add(order)
        db.session.commit()
        logging.info(f"[API_CREATE_ORDER] Order created with ID: {order.id}")

        # ایجاد آیتم‌های سفارش
        for idx, item_data in enumerate(items):
            photo_name = None
            photo_field = item_data.get('photo_field') or f'item_{idx+1}_photo'
            file = request.files.get(photo_field)

            if file and file.filename:
                try:
                    ext = '.jpg'
                    save_dir = os.path.join('app', 'static', 'product_pics')
                    os.makedirs(save_dir, exist_ok=True)
                    safe_product_name = item_data.get("product_name", "").replace(" ", "_").replace("/", "_")
                    save_name = f'order_{order.id}_item_{idx+1}_{safe_product_name}{ext}'
                    save_path = os.path.join(save_dir, save_name)
                    file.save(save_path)
                    photo_name = save_name
                    logging.info(f"[API_CREATE_ORDER] Saved photo: {save_name}")
                except Exception as e:
                    logging.error(f"[API_CREATE_ORDER] Error saving photo for item {idx+1}: {e}")

            item = BotOrderItem(
                order_id=order.id,
                product_name=item_data.get('product_name', ''),
                quantity=item_data.get('quantity', 0),
                unit_price=item_data.get('unit_price', 0),
                total_price=item_data.get('total_price', 0),
                photo=photo_name
            )
            db.session.add(item)
            logging.info(f"[API_CREATE_ORDER] Added item {idx+1}: {item_data.get('product_name', '')}")

        db.session.commit()
        logging.info(f"[API_CREATE_ORDER] All order items created successfully")

        return jsonify({
            'success': True,
            'order_id': order.id,
            'message': 'سفارش با موفقیت ثبت شد'
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"[API_CREATE_ORDER] Error creating order: {e}")
        import traceback
        logging.error(f"[API_CREATE_ORDER] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': 'خطا در ثبت سفارش',
            'error': str(e)
        }), 500


@api_bp.route('/order_status_notify', methods=['POST'])
def order_status_notify():
    """
    API برای اطلاع‌رسانی تغییر وضعیت سفارش به ربات
    """
    import logging
    try:
        data = request.get_json()
        logging.info(f"[ORDER_STATUS_NOTIFY] Received notification: {data}")

        telegram_id = data.get('telegram_id')
        order_id = data.get('order_id')
        status = data.get('status')

        if not all([telegram_id, order_id, status]):
            logging.error("[ORDER_STATUS_NOTIFY] Missing required fields")
            return jsonify({
                'success': False,
                'message': 'فیلدهای الزامی ناقص'
            }), 400

        # اینجا می‌توانید منطق اطلاع‌رسانی به ربات را اضافه کنید
        # مثلاً ارسال پیام به کاربر از طریق Telegram Bot API

        logging.info(f"[ORDER_STATUS_NOTIFY] Notification processed for order {order_id}, user {telegram_id}, status: {status}")

        return jsonify({
            'success': True,
            'message': 'اطلاع‌رسانی با موفقیت پردازش شد'
        })

    except Exception as e:
        logging.error(f"[ORDER_STATUS_NOTIFY] Error processing notification: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در پردازش اطلاع‌رسانی',
            'error': str(e)
        }), 500


@api_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    """
    API برای دریافت جزئیات سفارش
    """
    import logging
    try:
        from app.models import BotOrder, BotOrderItem

        order = BotOrder.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': 'سفارش یافت نشد'
            }), 404

        # دریافت آیتم‌های سفارش
        items = BotOrderItem.query.filter_by(order_id=order_id).all()

        order_data = {
            'id': order.id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'customer_address': order.customer_address,
            'telegram_id': order.telegram_id,
            'status': order.status,
            'total_amount': order.total_amount,
            'created_at': str(order.created_at),
            'items': []
        }

        for item in items:
            order_data['items'].append({
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price,
                'photo': item.photo
            })

        return jsonify({
            'success': True,
            'order': order_data
        })

    except Exception as e:
        logging.error(f"[GET_ORDER_DETAILS] Error: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در دریافت جزئیات سفارش',
            'error': str(e)
        }), 500