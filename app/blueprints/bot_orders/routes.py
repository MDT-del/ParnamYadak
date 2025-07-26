# ---------------------------------------------
# فایل: routes.py
# توضیح: مسیرهای مربوط به سفارشات ربات تلگرام
# ---------------------------------------------

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import BotOrder, BotOrderItem, Person, InventoryProduct, db
from app.decorators import permission_required
import json
import logging
import os
from datetime import datetime
from app.models import Notification, Role, InventoryBatch, InventoryHistory
from app.utils import shamsi_datetime
import requests
from sqlalchemy import or_
from datetime import datetime, timedelta
from app.models import User

from . import bot_orders_bp


@bot_orders_bp.route('/')
@login_required
def index():
    """
    صفحه اصلی سفارشات ربات
    """
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = BotOrder.query
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(BotOrder.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # برای هر سفارش، اطلاعات مکانیک را بر اساس telegram_id پیدا کن
    for order in orders.items:
        if order.telegram_id:
            mechanic = Person.query.filter_by(telegram_id=order.telegram_id, person_type='mechanic').first()
            if mechanic:
                order.mechanic_info = {
                    'name': mechanic.full_name,
                    'phone': mechanic.phone_number,
                    'commission_percentage': mechanic.commission_percentage
                }
                order.mechanic_obj = mechanic
            else:
                order.mechanic_info = {
                    'name': f"مکانیک {order.telegram_id}",
                    'phone': 'نامشخص',
                    'commission_percentage': 0
                }
                order.mechanic_obj = None
        else:
            order.mechanic_info = {
                'name': 'نامشخص',
                'phone': 'نامشخص',
                'commission_percentage': 0
            }
            order.mechanic_obj = None
        # واکشی اطلاعات مشتری اگر سفارش مکانیک نیست
        if not order.mechanic_obj:
            customer = None
            if order.person_id:
                customer = Person.query.get(order.person_id)
            elif order.customer_phone:
                customer = Person.query.filter_by(phone_number=order.customer_phone, person_type='customer').first()
            if customer:
                order.customer_name = customer.full_name
                order.customer_phone = customer.phone_number
            else:
                # اگر اطلاعات مشتری در خود سفارش موجود بود، همان را نمایش بده
                if order.customer_name:
                    order.customer_name = order.customer_name
                if order.customer_phone:
                    order.customer_phone = order.customer_phone
    
    # مجموع درآمد فقط بر اساس سفارش‌های نهایی
    total_income = db.session.query(db.func.sum(BotOrder.total_amount)).filter(
        BotOrder.status.in_(['تایید شده', 'پرداخت شده', 'تکمیل شده'])
    ).scalar() or 0
    
    return render_template('bot_orders/index.html', 
                         orders=orders,
                         status=status,
                         total_income=total_income)


@bot_orders_bp.route('/<int:order_id>')
@login_required
def detail(order_id):
    """نمایش جزئیات سفارش ربات"""
    order = BotOrder.query.get_or_404(order_id)
    
    # اضافه کردن لاگ برای بررسی اطلاعات سفارش
    logging.info(f"[BOT_ORDER_DETAIL] Order {order_id}: status={order.status}, receipt_image={order.receipt_image}")
    logging.info(f"[BOT_ORDER_DETAIL] Order {order_id}: receipt_image type={type(order.receipt_image)}, value='{order.receipt_image}'")
    
    # اگر سفارش آیتم‌های جداگانه دارد
    if order.items.count() > 0:
        # سفارش جدید با آیتم‌های جداگانه
        items = order.items.all()
        for item in items:
            # اگر آیتم به محصول مرتبط نیست، سعی کن آن را پیدا کن
            if not item.product and item.product_name:
                product = InventoryProduct.query.filter(
                    InventoryProduct.name.ilike(f'%{item.product_name}%')
                ).first()
                if product:
                    item.product = product
    else:
        # سفارش قدیمی - آیتم‌ها در JSON ذخیره شده‌اند
        items = []
        if order.order_items:
            try:
                items_data = json.loads(order.order_items)
                for item_data in items_data:
                    item = type('Item', (), {
                        'product_name': item_data.get('product_name', ''),
                        'quantity': item_data.get('quantity', 0),
                        'unit_price': item_data.get('unit_price', 0),
                        'total_price': item_data.get('total_price', 0),
                        'status': item_data.get('status', 'در انتظار بررسی'),
                        'photo': item_data.get('photo', None),
                        'product': None
                    })()
                    items.append(item)
            except:
                items = []
    
    # اطلاعات مکانیک
    mechanic_info = None
    if order.telegram_id:
        mechanic = Person.query.filter_by(telegram_id=order.telegram_id, person_type='mechanic').first()
        if mechanic:
            mechanic_info = {
                'name': mechanic.full_name,
                'phone': mechanic.phone_number,
                'commission_percentage': mechanic.commission_percentage
            }
    # واکشی اطلاعات مشتری
    customer = None
    if order.person_id:
        customer = Person.query.get(order.person_id)
    elif order.customer_phone:
        customer = Person.query.filter_by(phone_number=order.customer_phone, person_type='customer').first()
    
    return render_template('bot_orders/detail.html', 
                         order=order, 
                         items=items,
                         mechanic_info=mechanic_info,
                         customer=customer)


@bot_orders_bp.route('/<int:order_id>/process', methods=['POST'])
@login_required
def process_order(order_id):
    """
    پردازش سفارش ربات
    """
    order = BotOrder.query.get_or_404(order_id)
    action = request.form.get('action')
    
    if action == 'approve':
        return approve_order(order)
    elif action == 'reject':
        return reject_order(order)
    elif action == 'confirm_payment':
        return confirm_payment(order)
    else:
        return jsonify({'success': False, 'message': 'عملیات نامعتبر'})


def approve_order(order):
    import logging
    logging.info(f"[APPROVE] approve_order called for order_id={order.id}")
    """
    تایید سفارش
    """
    try:
        items = list(order.items.all())
        logging.info(f"[APPROVE] Items in order: {[{'id': item.id, 'status': item.status, 'product': item.product_id, 'quantity': item.quantity if hasattr(item, 'quantity') else None} for item in items]}")
        if items:
            all_out_of_stock = all(getattr(item, 'status', '') == 'عدم موجودی' for item in items)
            if all_out_of_stock:
                logging.warning("[APPROVE] Early return: all items out of stock")
                order.status = 'لغو شده'
                db.session.commit()
                return jsonify({
                    'success': False,
                    'message': 'همه آیتم‌های سفارش عدم موجودی دارند. سفارش به صورت خودکار لغو شد.'
                })
            if len(items) == 1 and getattr(items[0], 'status', '') == 'عدم موجودی':
                logging.warning("[APPROVE] Early return: single item out of stock")
                order.status = 'لغو شده'
                db.session.commit()
                return jsonify({
                    'success': False,
                    'message': 'آیتم سفارش عدم موجودی دارد. سفارش به صورت خودکار لغو شد.'
                })
        else:
            logging.warning("[APPROVE] Early return: no items in order")
            return jsonify({'success': False, 'message': 'سفارشی بدون آیتم'})
        # --- اصلاح منطق بررسی موجودی آیتم‌ها قبل از رزرو ---
        any_available = False
        error_details = []
        for item in items:
            if item.status == 'موجود' and item.product:
                if not item.product.can_reserve(item.quantity):
                    item.status = 'عدم موجودی'
                    db.session.add(item)
                    error_details.append(f"محصول '{item.product.name}' موجودی کافی ندارد (درخواست: {item.quantity}، موجود: {item.product.available_quantity})")
                else:
                    any_available = True
            elif item.status != 'موجود':
                error_details.append(f"آیتم '{item.product_name}' وضعیت: {item.status}")
            elif not item.product:
                error_details.append(f"آیتم '{item.product_name}' به محصول متصل نیست")
            elif not hasattr(item, 'quantity') or item.quantity <= 0:
                error_details.append(f"آیتم '{item.product_name}' تعداد نامعتبر: {item.quantity}")
        db.session.commit()
        if not any_available:
            order.status = 'لغو شده'
            db.session.commit()
            return jsonify({
                'success': False,
                'message': 'هیچ آیتمی موجود نیست. سفارش لغو شد. جزئیات: ' + ' | '.join(error_details)
            })
        for item in items:
            logging.info(f"[APPROVE] Reserve try: id={item.id}, status={item.status}, product={item.product_id}")
            if item.status == 'موجود' and item.product:
                item.reserve_inventory()
        order.expires_at = datetime.now() + timedelta(hours=2)
        order.status = 'در انتظار تایید کاربر'
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'سفارش تایید شد و موجودی رزرو شد. منتظر تایید نهایی کاربر است.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'خطا در تایید سفارش: {str(e)}'})


def cancel_order_and_release_reservations(order):
    """
    لغو سفارش و آزادسازی رزرو همه آیتم‌ها
    """
    for item in order.items.all():
        item.release_reservation()
    order.status = 'لغو شده'
    from app import db
    db.session.commit()


def reject_order(order):
    """
    رد سفارش
    """
    try:
        cancel_order_and_release_reservations(order)
        # ارسال پیام به ربات (در آینده)
        # send_rejection_message_to_bot(order.telegram_id)
        return jsonify({
            'success': True,
            'message': 'سفارش رد شد'
        })
    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطا در رد سفارش'})


def confirm_payment(order):
    """
    تایید پرداخت
    """
    try:
        order.payment_confirmed = True
        order.payment_confirmed_by = current_user.id
        order.payment_confirmed_at = datetime.now()
        order.status = 'پرداخت شده'
        
        # کسر از موجودی (FIFO)
        for item in order.items.all():
            if item.product and item.reserved_quantity > 0:
                print(f"[DEBUG] Processing item: {item.product.name}, reserved: {item.reserved_quantity}, needed: {item.quantity}")
                remaining = item.quantity
                batches = item.product.batches.filter(InventoryBatch.remaining_quantity > 0).order_by(InventoryBatch.created_at).all()
                print(f"[DEBUG] Found {len(batches)} batches for product {item.product.name}")
                
                for batch in batches:
                    if remaining <= 0:
                        break
                    
                    available = min(batch.remaining_quantity, remaining)
                    batch.remaining_quantity -= available
                    remaining -= available
                    print(f"[DEBUG] Deducted {available} from batch {batch.id}, remaining: {batch.remaining_quantity}")
                
                if remaining > 0:
                    print(f"[WARNING] Not enough stock for {item.product.name}, remaining: {remaining}")
        
        db.session.commit()
        
        # ارسال پیام به ربات (فقط از طریق وبهوک)
        try:
            import requests
            bot_notify_url = "https://panel.parnamyadak.ir/api/order_status_notify"
            if order.telegram_id:
                requests.post(bot_notify_url, json={"telegram_id": int(order.telegram_id), "order_id": order.id, "status": order.status}, timeout=5)
        except Exception as e:
            print(f"[BOT] Error sending payment confirmation: {e}")
        
        return jsonify({
            'success': True,
            'message': 'پرداخت تایید شد و موجودی کسر شد'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error confirming payment: {e}")
        return jsonify({'success': False, 'message': 'خطا در تایید پرداخت'})


@bot_orders_bp.route('/<int:order_id>/link_product', methods=['POST'])
@login_required
def link_product(order_id):
    """
    ارتباط محصول ربات با محصول انبار
    """
    order = BotOrder.query.get_or_404(order_id)
    item_id = request.form.get('item_id', type=int)
    product_id = request.form.get('product_id', type=int)
    
    if not item_id or not product_id:
        return jsonify({'success': False, 'message': 'پارامترهای نامعتبر'})
    
    item = BotOrderItem.query.get(item_id)
    product = InventoryProduct.query.get(product_id)
    
    if not item or not product:
        return jsonify({'success': False, 'message': 'آیتم یا محصول یافت نشد'})
    
    try:
        item.product_id = product_id
        item.status = 'موجود'
        db.session.commit()
        # محاسبه کمیسیون مکانیک بعد از اتصال محصول
        order.calculate_commission()
        db.session.commit()
        # اگر سفارش تایید شده بود، رزرو موجودی انجام شود
        if order.status == 'تایید شده' and item.product:
            item.reserve_inventory()
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'محصول {product.name} به آیتم مرتبط شد و موجودی رزرو شد'
            })
        return jsonify({
            'success': True,
            'message': f'محصول {product.name} به آیتم مرتبط شد'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'خطا در ارتباط محصول'})


@bot_orders_bp.route('/<int:order_id>/update_item/<int:item_id>', methods=['POST'])
@login_required
def update_item(order_id, item_id):
    """
    ویرایش وضعیت و قیمت واحد آیتم سفارش ربات
    """
    order = BotOrder.query.get_or_404(order_id)
    item = BotOrderItem.query.get_or_404(item_id)
    status = request.form.get('status')
    unit_price = request.form.get('unit_price', type=float)
    if status:
        item.status = status
    if unit_price is not None:
        item.unit_price = unit_price
        item.total_price = item.unit_price * item.quantity
    db.session.commit()
    # محاسبه کمیسیون مکانیک بعد از ویرایش آیتم
    order.calculate_commission()
    db.session.commit()
    flash('آیتم با موفقیت ویرایش شد.', 'success')
    return redirect(url_for('bot_orders.detail', order_id=order_id))


@bot_orders_bp.route('/<int:order_id>/notify_mechanic', methods=['POST'])
@login_required
def notify_mechanic(order_id):
    """
    ارسال وضعیت سفارش به ربات و اطلاع‌رسانی به مکانیک
    """
    import requests
    order = BotOrder.query.get_or_404(order_id)
    items = []
    for item in order.items.all():
        items.append({
            'product_name': item.product_name,
            'quantity': item.quantity,
            'status': item.status,
            'unit_price': item.unit_price,
            'total_price': item.total_price
        })
    payload = {
        'telegram_id': order.telegram_id,
        'order_id': order.id,
        'items': items,
        'total_amount': order.total_amount
    }
    # آدرس API ربات (در صورت نیاز مقداردهی کنید)
    BOT_API_URL = 'http://localhost:8000/bot/api/order_status'  # مقداردهی صحیح کنید
    try:
        response = requests.post(BOT_API_URL, json=payload, timeout=10)
        if response.status_code == 200:
            order.status = 'در انتظار تایید مکانیک'
            db.session.commit()
            flash('وضعیت سفارش با موفقیت برای مکانیک ارسال شد.', 'success')
        else:
            flash('ارسال به ربات ناموفق بود.', 'danger')
    except Exception as e:
        flash('خطا در ارسال به ربات: {}'.format(e), 'danger')
    return redirect(url_for('bot_orders.detail', order_id=order_id))


@bot_orders_bp.route('/api/orders')
@login_required
def api_orders():
    """
    API برای دریافت لیست سفارشات با فیلتر
    """
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    mechanic_id = request.args.get('mechanic_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = BotOrder.query
    
    if status:
        query = query.filter_by(status=status)
    
    if mechanic_id:
        query = query.filter_by(mechanic_id=mechanic_id)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(BotOrder.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(BotOrder.created_at < to_date)
        except ValueError:
            pass
    
    orders = query.order_by(BotOrder.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    orders_data = []
    for order in orders.items:
        orders_data.append({
            'id': order.id,
            'customer_name': order.customer_name or 'نامشخص',
            'customer_phone': order.customer_phone,
            'telegram_id': order.telegram_id,
            'mechanic_name': order.mechanic.full_name if order.mechanic else None,
            'total_amount': order.total_amount,
            'commission_amount': order.commission_amount,
            'status': order.status,
            'payment_confirmed': order.payment_confirmed,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'items_count': order.items.count()
        })
    
    return jsonify({
        'success': True,
        'orders': orders_data,
        'pagination': {
            'page': orders.page,
            'pages': orders.pages,
            'per_page': orders.per_page,
            'total': orders.total,
            'has_next': orders.has_next,
            'has_prev': orders.has_prev
        }
    })


@bot_orders_bp.route('/api/mechanics')
@login_required
def api_mechanics():
    """
    API برای دریافت لیست مکانیک‌ها
    """
    mechanics = Person.query.filter_by(is_approved=True, person_type='mechanic').all()
    
    mechanics_data = []
    for mechanic in mechanics:
        mechanics_data.append({
            'id': mechanic.id,
            'full_name': mechanic.full_name,
            'phone_number': mechanic.phone_number,
            'commission_percentage': mechanic.commission_percentage
        })
    
    return jsonify({
        'success': True,
        'mechanics': mechanics_data
    })


@bot_orders_bp.route('/api/search_products')
@login_required
def search_products():
    """
    API برای جستجوی محصولات در انبار
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': False, 'message': 'عبارت جستجو الزامی است'})
    
    try:
        # جستجو در محصولات انبار
        products = InventoryProduct.query.filter(
            or_(
                InventoryProduct.name.ilike(f'%{query}%'),
                InventoryProduct.product_number.ilike(f'%{query}%')
            )
        ).limit(10).all()
        
        results = []
        for product in products:
            results.append({
                'id': product.id,
                'name': product.name,
                'product_number': product.product_number,
                'quality': product.quality,
                'available_quantity': product.available_quantity,
                'unit_price': product.unit_price if hasattr(product, 'unit_price') else 0
            })
        
        return jsonify({
            'success': True,
            'products': results
        })
        
    except Exception as e:
        logging.error(f"Error searching products: {e}")
        return jsonify({'success': False, 'message': 'خطا در جستجوی محصولات'})


@bot_orders_bp.route('/api/link_product/<int:item_id>', methods=['POST'])
@login_required
def link_product_to_item(item_id):
    """
    API برای اتصال محصول انبار به آیتم سفارش ربات
    """
    data = request.get_json()
    product_id = data.get('product_id')
    unit_price = data.get('unit_price', 0)
    
    if not product_id:
        return jsonify({'success': False, 'message': 'شناسه محصول الزامی است'})
    
    try:
        # پیدا کردن آیتم سفارش
        item = BotOrderItem.query.get_or_404(item_id)
        
        # پیدا کردن محصول انبار
        product = InventoryProduct.query.get_or_404(product_id)
        
        # اتصال محصول به آیتم
        item.product_id = product_id
        item.unit_price = unit_price
        item.total_price = item.quantity * unit_price

        # حذف رزرو موجودی از اینجا
        # بروزرسانی مبلغ کل سفارش
        order = item.order
        order.total_amount = sum(item.total_price for item in order.items)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'محصول با موفقیت به سفارش متصل شد',
            'item': {
                'id': item.id,
                'product_name': product.name,
                'product_number': product.product_number,
                'unit_price': item.unit_price,
                'total_price': item.total_price
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error linking product: {e}")
        return jsonify({'success': False, 'message': 'خطا در اتصال محصول'})


@bot_orders_bp.route('/api/create_order', methods=['POST'])
def api_create_order():
    data = request.form
    items_json = data.get('items')
    if not items_json:
        return jsonify({'success': False, 'message': 'اطلاعات آیتم‌ها ناقص'}), 400
    try:
        items = json.loads(items_json)
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطا در خواندن آیتم‌ها: {e}'})
    customer_phone = data.get('customer_phone')
    customer_name = data.get('customer_name')
    customer_address = data.get('customer_address')
    telegram_id = data.get('telegram_id')
    mechanic_id = data.get('mechanic_id')
    # فقط اگر mechanic_id مقدار دارد و عددی نیست (مثلاً telegram_id است)، دنبال مکانیک بگرد
    if mechanic_id:
        if not str(mechanic_id).isdigit() or len(str(mechanic_id)) > 6:
            mechanic = Person.query.filter_by(telegram_id=mechanic_id, person_type='mechanic').first()
            if mechanic:
                mechanic_id = mechanic.id
            else:
                if data.get('is_mechanic') or data.get('type') == 'mechanic':
                    return jsonify({'success': False, 'message': 'مکانیک یافت نشد'}), 400
                mechanic_id = None
    # ثبت یا واکشی مشتری در Person
    customer = None
    if customer_phone:
        customer = Person.query.filter_by(phone_number=customer_phone, person_type='customer').first()
        if not customer:
            customer = Person(
                full_name=customer_name or 'نامشخص',
                phone_number=customer_phone,
                person_type='customer',
                address=customer_address or None,
                telegram_id=telegram_id
            )
            db.session.add(customer)
            db.session.commit()
    else:
        return jsonify({'success': False, 'message': 'شماره تلفن مشتری الزامی است'}), 400
    # اگر باز هم نام مشتری خالی بود، مقدار پیش‌فرض قرار بده
    if not customer_name:
        customer_name = customer.full_name if customer else 'نامشخص'
    if not customer_phone:
        customer_phone = customer.phone_number if customer else 'نامشخص'
    if not items:
        return jsonify({'success': False, 'message': 'اطلاعات ناقص'})
    try:
        total_amount = sum(item.get('total_price', 0) for item in items)
        order = BotOrder(
            customer_phone=customer_phone,
            customer_name=customer_name,
            customer_address=customer_address,
            telegram_id=telegram_id,
            mechanic_person_id=mechanic_id if mechanic_id else None,
            person_id=customer.id if customer else None,
            order_items=json.dumps(items),
            total_amount=total_amount
        )
        db.session.add(order)
        db.session.commit()
        # ذخیره آیتم‌ها
        for idx, item_data in enumerate(items):
            photo_name = None
            photo_field = item_data.get('photo_field') or f'item_{idx+1}_photo'
            file = request.files.get(photo_field)
            if file:
                ext = '.jpg'
                save_dir = os.path.join('app', 'static', 'product_pics')
                os.makedirs(save_dir, exist_ok=True)
                save_name = f'order_{order.id}_item_{idx+1}_{item_data.get("product_name", "").replace(" ", "_")}{ext}'
                save_path = os.path.join(save_dir, save_name)
                file.save(save_path)
                photo_name = save_name
            item = BotOrderItem(
                order_id=order.id,
                product_name=item_data.get('product_name', ''),
                quantity=item_data.get('quantity', 0),
                unit_price=item_data.get('unit_price', 0),
                total_price=item_data.get('total_price', 0),
                photo=photo_name
            )
            db.session.add(item)
        db.session.commit()
        from app.models import InventoryProduct
        items_in_order = BotOrderItem.query.filter_by(order_id=order.id).all()
        for item in items_in_order:
            product = InventoryProduct.query.filter(InventoryProduct.name == item.product_name).first()
            if not product:
                item.status = 'عدم موجودی'
            else:
                if product.available_quantity >= item.quantity:
                    item.status = 'موجود'
                    item.product_id = product.id
                else:
                    item.status = 'عدم موجودی'
                    item.product_id = product.id
            db.session.add(item)
        db.session.commit()
        order.calculate_commission()
        if customer:
            customer.update_first_order_info()
            db.session.add(customer)
        db.session.commit()
        # ارسال نوتیفیکیشن و اطلاع‌رسانی به ربات (بدون تغییر)
        try:
            notified_users = set()
            roles = Role.query.all()
            for role in roles:
                users = User.query.join(User.roles).filter(Role.id == role.id).all()
                for user in users:
                    if user.id not in notified_users:
                        notif = Notification(
                            message=f"سفارش جدیدی از ربات توسط مکانیک {telegram_id} ثبت شد.",
                            user_id=user.id
                        )
                        db.session.add(notif)
                        notified_users.add(user.id)
            db.session.commit()
            logging.info(f"[BOT_ORDERS] Notification sent to all unique users for order {order.id}")
        except Exception as notif_err:
            # فقط لاگ بگیر، هیچ پیام خطایی به کاربر نمایش نده
            pass
        # ارسال اطلاع‌رسانی به ربات پس از ثبت سفارش جدید
        try:
            import requests
            bot_notify_url = "https://panel.parnamyadak.ir/api/order_status_notify"
            if order.telegram_id:
                requests.post(bot_notify_url, json={"telegram_id": int(order.telegram_id), "order_id": order.id, "status": order.status}, timeout=5)
        except Exception as e:
            # فقط لاگ بگیر، هیچ پیام خطایی به کاربر نمایش نده
            print(f"❌ خطا در ارسال اطلاع‌رسانی سفارش جدید به ربات: {e}")
        return jsonify({
            'success': True,
            'order_id': order.id,
            'message': 'سفارش با موفقیت ثبت شد'
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"[BOT_ORDERS] Error in create_order: {e}")
        return jsonify({'success': False, 'message': 'خطا در ثبت سفارش'}) 


@bot_orders_bp.route('/api/order_status/<int:order_id>', methods=['GET'])
def api_order_status(order_id):
    """
    API برای دریافت وضعیت و جزئیات سفارش ربات (برای polling ربات)
    خروجی: {success, status, items: [...], total_amount, payment_confirmed, ...}
    """
    order = BotOrder.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'سفارش یافت نشد'}), 404
    items = []
    available_items = []
    unavailable_items = []
    total_available_amount = 0
    for item in order.items.all():
        item_info = {
            'id': item.id,
            'product_name': item.product_name,
            'quantity': item.quantity,
            'status': item.status,
            'unit_price': item.unit_price,
            'total_price': item.total_price
        }
        items.append(item_info)
        if item.status == 'موجود':
            available_items.append(item_info)
            total_available_amount += item.total_price
        elif item.status == 'عدم موجودی':
            unavailable_items.append(item_info)
    # ساخت پیام متنی برای ربات
    message_lines = []
    if unavailable_items:
        message_lines.append('آیتم‌های زیر موجود نیستند:')
        for item in unavailable_items:
            message_lines.append(f"- {item['product_name']} (تعداد: {item['quantity']})")
    if available_items:
        message_lines.append('آیتم‌های زیر موجود هستند:')
        for item in available_items:
            message_lines.append(f"- {item['product_name']} (تعداد: {item['quantity']})، قیمت هر عدد: {item['unit_price']} تومان، جمع: {item['total_price']} تومان")
        message_lines.append(f"جمع کل آیتم‌های موجود: {total_available_amount} تومان")
    message = '\n'.join(message_lines)
    return jsonify({
        'success': True,
        'order_id': order.id,
        'status': order.status,
        'items': items,
        'total_amount': order.total_amount,
        'total_available_amount': total_available_amount,
        'payment_confirmed': order.payment_confirmed,
        'telegram_id': order.telegram_id,
        'message': message
    }) 

@bot_orders_bp.route('/api/order_status/<int:order_id>/confirm', methods=['POST'])
def api_order_confirm(order_id):
    """
    تایید سفارش توسط مکانیک (از سمت ربات)
    ورودی: telegram_id, confirm=True
    """
    order = BotOrder.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'سفارش یافت نشد'}), 404
    data = request.get_json() or {}
    if data.get('confirm'):
        order.status = 'در انتظار پرداخت'
        db.session.commit()
        # ارسال اطلاع‌رسانی به ربات پس از تغییر وضعیت سفارش
        try:
            import requests
            bot_notify_url = "https://panel.parnamyadak.ir/api/order_status_notify"
            if order.telegram_id:
                requests.post(bot_notify_url, json={"telegram_id": int(order.telegram_id), "order_id": order.id, "status": order.status}, timeout=5)
        except Exception as e:
            import logging
            logging.error(f"❌ خطا در ارسال اطلاع‌رسانی وضعیت سفارش به ربات: {e}")
        return jsonify({'success': True, 'message': 'سفارش تایید شد و منتظر پرداخت است.'})
    return jsonify({'success': False, 'message': 'درخواست نامعتبر'})

@bot_orders_bp.route('/api/order_status/<int:order_id>/cancel', methods=['POST'])
def api_order_cancel(order_id):
    """
    لغو سفارش از سمت ربات یا پنل
    """
    order = BotOrder.query.get_or_404(order_id)
    try:
        cancel_order_and_release_reservations(order)
        return jsonify({'success': True, 'message': 'سفارش لغو شد و رزرو آزاد شد'})
    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطا در لغو سفارش'})

@bot_orders_bp.route('/api/order_status/<int:order_id>/upload_receipt', methods=['POST'])
def api_order_upload_receipt(order_id):
    import logging
    logging.info(f"[UPLOAD_RECEIPT] --- START --- order_id={order_id}")
    order = BotOrder.query.get(order_id)
    logging.info(f"[UPLOAD_RECEIPT] BEFORE: order_id={order_id}, order={order}")
    if not order:
        logging.error(f"[UPLOAD_RECEIPT] سفارش یافت نشد: order_id={order_id}")
        return jsonify({'success': False, 'message': 'سفارش یافت نشد'}), 404
    telegram_id = request.form.get('telegram_id')
    logging.info(f"[UPLOAD_RECEIPT] telegram_id from form: {telegram_id}")
    logging.info(f"[UPLOAD_RECEIPT] فایل‌های ارسالی: {list(request.files.keys())}")
    logging.info(f"[UPLOAD_RECEIPT] فرم داده‌ها: {list(request.form.keys())}")
    file = request.files.get('receipt_image')
    if not file:
        logging.warning(f"[UPLOAD_RECEIPT] فایل receipt_image یافت نشد برای order_id={order_id}, telegram_id={telegram_id}")
        return jsonify({'success': False, 'message': 'فایل یافت نشد'})
    logging.info(f"[UPLOAD_RECEIPT] فایل دریافت شد: {file.filename}, نوع: {file.content_type}")
    try:
        save_dir = os.path.join('app', 'static', 'bot_receipts')
        os.makedirs(save_dir, exist_ok=True)
        save_name = f'order_{order_id}_{telegram_id}.jpg'
        save_path = os.path.join(save_dir, save_name)
        logging.info(f"[UPLOAD_RECEIPT] تلاش برای ذخیره در: {save_path}")
        file.save(save_path)
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            logging.info(f"[UPLOAD_RECEIPT] فایل رسید با موفقیت ذخیره شد: {save_path}, اندازه: {file_size} bytes")
        else:
            logging.error(f"[UPLOAD_RECEIPT] فایل ذخیره نشد: {save_path}")
            return jsonify({'success': False, 'message': 'فایل ذخیره نشد'})
        order.receipt_image = f'bot_receipts/{save_name}'
        order.status = 'در انتظار تایید پرداخت'
        db.session.commit()
        logging.info(f"[UPLOAD_RECEIPT] AFTER: order_id={order_id}, order.receipt_image={order.receipt_image}, order.status={order.status}")
        logging.info(f"[UPLOAD_RECEIPT] --- END --- order_id={order_id}")
        return jsonify({'success': True, 'message': 'رسید پرداخت دریافت شد و سفارش منتظر تایید ادمین است.'})
    except Exception as e:
        logging.error(f"[UPLOAD_RECEIPT] خطا در ذخیره رسید: {e}")
        import traceback
        logging.error(f"[UPLOAD_RECEIPT] جزئیات خطا: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'خطا در ذخیره رسید: {e}'}) 

@bot_orders_bp.route('/api/notify_payment_confirmed', methods=['POST'])
def api_notify_payment_confirmed():
    """
    API برای اطلاع‌رسانی تایید پرداخت به ربات
    """
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        order_id = data.get('order_id')
        message = data.get('message', 'پرداخت تایید شد!')
        
        if not telegram_id:
            return jsonify({
                'success': False,
                'message': 'telegram_id الزامی است'
            }), 400
        
        # ارسال پیام به ربات
        import os
        from dotenv import load_dotenv
        
        # بارگذاری تنظیمات ربات
        bot_config_path = os.path.join(os.path.dirname(__file__), '../../../bot/bot_config.env')
        load_dotenv(bot_config_path)
        
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            return jsonify({
                'success': False,
                'message': 'BOT_TOKEN یافت نشد'
            }), 500
        
        # ارسال پیام به ربات
        import requests
        
        bot_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': telegram_id,
            'text': f"✅ {message}\n\nسفارش شماره {order_id} شما با موفقیت پرداخت شد و به آدرس شما ارسال خواهد شد.",
            'parse_mode': 'HTML'
        }
        
        response = requests.post(bot_url, json=payload)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'پیام با موفقیت ارسال شد'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'خطا در ارسال پیام: {response.status_code}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطا: {str(e)}'
        }), 500 