# ---------------------------------------------
# فایل: routes.py (telegram_bot)
# توضیح: مسیرهای API برای ارتباط با ربات تلگرام
# ---------------------------------------------

from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from app.models import Mechanic, BotOrder, BotOrderItem, Product, db
from app.decorators import permission_required
import json
import datetime
from datetime import timedelta
import logging
import os
import requests
import time
import json

telegram_bot_bp = Blueprint('telegram_bot',
                           __name__,
                           template_folder='templates')


@telegram_bot_bp.route('/api/orders', methods=['GET'])
def api_get_orders():
    """
    API برای دریافت سفارشات ربات
    """
    try:
        # پارامترهای فیلتر
        status = request.args.get('status', '')
        mechanic_id = request.args.get('mechanic_id', type=int)
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        limit = request.args.get('limit', 50, type=int)
        telegram_id = request.args.get('telegram_id', type=int)
        customer_id = request.args.get('customer_id', type=int)
        
        # اگر telegram_id ارسال شده اما mechanic_id نه، سعی کن mechanic_id را پیدا کن
        if telegram_id and not mechanic_id:
            mechanic = Mechanic.query.filter_by(telegram_id=telegram_id).first()
            if mechanic:
                mechanic_id = mechanic.id
                logging.info(f"[API ORDERS] Found mechanic_id={mechanic_id} for telegram_id={telegram_id}")
            else:
                # اگر مکانیک پیدا نشد، سعی کن مشتری را پیدا کن
                from app.models import Customer
                customer = Customer.query.filter_by(telegram_id=telegram_id).first()
                if customer:
                    customer_id = customer.id
                    logging.info(f"[API ORDERS] Found customer_id={customer_id} for telegram_id={telegram_id}")
        
        logging.warning(f"[API ORDERS] Params: status={status}, mechanic_id={mechanic_id}, telegram_id={telegram_id}, customer_id={customer_id}, limit={limit}")
        query = BotOrder.query
        
        # اعمال فیلترها
        if status:
            query = query.filter(BotOrder.status == status)
        
        if mechanic_id:
            query = query.filter(BotOrder.mechanic_id == mechanic_id)
        
        if telegram_id:
            query = query.filter(BotOrder.telegram_id == telegram_id)
        
        if customer_id:
            query = query.filter(BotOrder.customer_id == customer_id)
        
        if start_date:
            try:
                start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(BotOrder.created_at >= start)
            except ValueError:
                pass
        
        if end_date:
            try:
                end = datetime.datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(BotOrder.created_at < end)
            except ValueError:
                pass
        
        orders = query.order_by(BotOrder.created_at.desc()).limit(limit).all()
        logging.warning(f"[API ORDERS] Orders found: {len(orders)}")
        
        result = []
        for order in orders:
            # دریافت آیتم‌های سفارش
            items_list = []
            total_amount = 0
            
            # اگر سفارش آیتم‌های جداگانه دارد
            if hasattr(order, 'items') and order.items:
                for item in order.items:
                    if hasattr(item, 'product_name') and hasattr(item, 'quantity') and hasattr(item, 'unit_price'):
                        item_total = item.quantity * item.unit_price
                        total_amount += item_total
                        items_list.append({
                            'product_name': item.product_name,
                            'quantity': item.quantity,
                            'unit_price': item.unit_price,
                            'item_total': item_total
                        })
            else:
                # اگر سفارش قدیمی است و آیتم‌های جداگانه ندارد
                if hasattr(order, 'product_name') and hasattr(order, 'quantity') and hasattr(order, 'unit_price'):
                    item_total = order.quantity * order.unit_price
                    total_amount += item_total
                    items_list.append({
                        'product_name': order.product_name,
                        'quantity': order.quantity,
                        'unit_price': order.unit_price,
                        'item_total': item_total
                    })
            
            # استفاده از total_amount از مدل اگر محاسبه شده صفر باشد
            if total_amount == 0 and hasattr(order, 'total_amount'):
                total_amount = order.total_amount
            
            result.append({
                'id': order.id,
                'customer_name': getattr(order, 'customer_name', None),
                'customer_phone': getattr(order, 'customer_phone', None),
                'customer_id': getattr(order, 'customer_id', None),
                'mechanic_id': getattr(order, 'mechanic_id', None),
                'telegram_id': getattr(order, 'telegram_id', None),
                'status': getattr(order, 'status', None),
                'status_display': getattr(order, 'status_display', getattr(order, 'status', None)),
                'created_at': str(getattr(order, 'created_at', '')),
                'total_amount': total_amount,
                'items': items_list,
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logging.exception(f"[API ORDERS] Exception: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در دریافت سفارشات',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/orders', methods=['POST'])
def api_create_order():
    """
    API برای ایجاد سفارش جدید از ربات (با احراز هویت)
    """
    try:
        data = request.get_json()
        
        # بررسی داده‌های ضروری
        required_fields = ['customer_name', 'customer_phone', 'product_name', 'quantity']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'فیلد {field} الزامی است'
                }), 400
        
        # اگر unit_price ارسال نشده، از محصول دریافت کن
        unit_price = data.get('unit_price', 0)
        if unit_price == 0:
            # تلاش برای یافتن قیمت محصول از دیتابیس
            product_name = data.get('product_name', '')
            if product_name:
                product = Product.query.filter(Product.name.ilike(f'%{product_name}%')).first()
                if product:
                    unit_price = product.price
                    logging.info(f"[API] Found product price for '{product_name}': {unit_price}")
                else:
                    logging.warning(f"[API] No product found for '{product_name}', using default price")
                    unit_price = 0  # قیمت پیش‌فرض
            else:
                unit_price = 0
        
        # محاسبه قیمت کل
        total_price = data['quantity'] * data['unit_price']
        
        # ایجاد سفارش جدید
        order = BotOrder(
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            customer_address=data.get('customer_address', ''),
            order_items=json.dumps([{
                'product_name': data['product_name'],
                'quantity': data['quantity'],
                'unit_price': data['unit_price'],
                'total_price': total_price
            }]),
            total_amount=total_price,
            status='در انتظار تایید',
            mechanic_id=data.get('mechanic_id')
        )
        
        db.session.add(order)
        db.session.commit()
        
        # اگر مکانیک مشخص شده، محاسبه کمیسیون
        if order.mechanic_id and order.mechanic:
            commission_amount = (total_price * order.mechanic.commission_percentage) / 100
            order.commission_amount = commission_amount
            order.mechanic.total_commission += commission_amount
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'سفارش با موفقیت ایجاد شد',
            'order_id': order.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'خطا در ایجاد سفارش',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/bot/orders', methods=['POST'])
def api_create_bot_order():
    """
    API برای ایجاد سفارش جدید از ربات (بدون احراز هویت)
    """
    try:
        data = request.get_json()
        logging.info(f"[API] Received bot order data: {data}")
        logging.info(f"[API] Items in data: {data.get('items', [])}")
        for idx, item in enumerate(data.get('items', [])):
            logging.info(f"[API] Item {idx}: {item}")
            if item.get('photo'):
                logging.info(f"[API] Item {idx} has photo: {item['photo']}")
            else:
                logging.info(f"[API] Item {idx} has no photo")
        
        # اضافه کردن لاگ برای بررسی نوع کاربر
        if data.get('mechanic_id'):
            logging.info(f"[API] Order from mechanic: {data['mechanic_id']}")
        elif data.get('customer_id'):
            logging.info(f"[API] Order from customer: {data['customer_id']}")
        else:
            logging.warning(f"[API] No user type specified in order data")
        
        # بررسی داده‌های ضروری
        if not data.get('mechanic_id') and not data.get('customer_id'):
            return jsonify({
                'success': False,
                'message': 'شناسه مکانیک یا مشتری الزامی است'
            }), 400
        
        if not data.get('items') or not isinstance(data['items'], list):
            return jsonify({
                'success': False,
                'message': 'لیست آیتم‌ها الزامی است'
            }), 400
        
        # بررسی اینکه کاربر تایید شده است
        user_id = data.get('mechanic_id') or data.get('customer_id')
        user_type = 'mechanic' if data.get('mechanic_id') else 'customer'
        
        if user_type == 'mechanic':
            user = Mechanic.query.filter_by(
                telegram_id=user_id,
                is_approved=True
            ).first()
        else:
            from app.models import Customer
            user = Customer.query.filter_by(
                telegram_id=user_id,
                is_approved=True
            ).first()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'کاربر تایید نشده یا یافت نشد'
            }), 400
        
        logging.info(f"[API] Found approved {user_type}: {user.full_name if hasattr(user, 'full_name') else user.first_name}")
        
        # ایجاد سفارش جدید
        order = BotOrder(
            mechanic_id=user.id if user_type == 'mechanic' else None,
            customer_id=user.id if user_type == 'customer' else None,
            telegram_id=user_id,
            customer_phone=getattr(user, 'phone_number', ''),
            customer_name=getattr(user, 'full_name', '') or f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip(),
            order_items=json.dumps(data['items']),
            total_amount=sum(item.get('total_price', 0) for item in data['items']),
            status='در انتظار بررسی'
        )
        
        db.session.add(order)
        db.session.commit()
        
        logging.info(f"[API] Created order with ID: {order.id}")
        
        # دانلود و ذخیره عکس‌های محصول
        import requests
        import os
        from datetime import datetime
        
        for idx, item_data in enumerate(data['items']):
            photo_path = None
            
            # اگر عکس محصول وجود دارد، دانلود کن
            if item_data.get('photo'):
                try:
                    logging.info(f"[API] Attempting to download photo for item {idx+1}: {item_data['photo']}")
                    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                    if bot_token:
                        file_info_url = f"https://api.telegram.org/bot{bot_token}/getFile"
                        file_info_response = requests.post(file_info_url, json={'file_id': item_data['photo']})
                        if file_info_response.status_code == 200:
                            file_info = file_info_response.json()
                            if file_info.get('ok') and file_info.get('result'):
                                file_path = file_info['result']['file_path']
                                file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                                file_response = requests.get(file_url)
                                if file_response.status_code == 200:
                                    filename = f"product_{order.id}_{idx+1}_{int(time.time())}.jpg"
                                    file_path = os.path.join(current_app.static_folder, 'product_pics', filename)
                                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                                    with open(file_path, 'wb') as f:
                                        f.write(file_response.content)
                                    # فقط نام فایل را ذخیره کن
                                    item_data['photo'] = filename
                                else:
                                    logging.error(f"[API] Failed to download file: {file_response.status_code}")
                                    item_data['photo'] = None
                            else:
                                logging.error(f"[API] Invalid file info response: {file_info}")
                                item_data['photo'] = None
                        else:
                            logging.error(f"[API] Failed to get file info: {file_info_response.status_code}")
                            item_data['photo'] = None
                    else:
                        logging.error("[API] Bot token not found in environment")
                        item_data['photo'] = None
                except Exception as e:
                    logging.error(f"[API] Error downloading photo: {e}")
                    item_data['photo'] = None
            else:
                logging.info(f"[API] No photo provided for item {idx+1}")
                item_data['photo'] = None
            # ایجاد آیتم سفارش
            order_item = BotOrderItem(
                order_id=order.id,
                product_name=item_data.get('product_name', ''),
                quantity=item_data.get('quantity', 0),
                unit_price=item_data.get('unit_price', 0),
                total_price=item_data.get('total_price', 0),
                photo=item_data.get('photo'), # فقط نام فایل ذخیره شود
                status='در انتظار بررسی'
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        logging.info(f"[API] Order {order.id} created successfully with {len(data['items'])} items")
        
        return jsonify({
            'success': True,
            'message': 'سفارش با موفقیت ایجاد شد',
            'order_id': order.id
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating bot order: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در ایجاد سفارش',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/bot/products/prices', methods=['POST'])
def api_get_product_prices():
    """
    API برای دریافت قیمت محصولات از ربات
    """
    try:
        data = request.get_json()
        product_names = data.get('products', [])
        
        if not product_names:
            return jsonify({
                'success': False,
                'message': 'لیست محصولات الزامی است'
            }), 400
        
        prices = {}
        for product_name in product_names:
            # جستجو در محصولات
            product = Product.query.filter(Product.name.ilike(f'%{product_name}%')).first()
            if product:
                prices[product_name] = {
                    'price': product.price,
                    'available': product.stock > 0,
                    'stock': product.stock
                }
            else:
                # اگر محصول یافت نشد، قیمت پیش‌فرض
                prices[product_name] = {
                    'price': 0,
                    'available': False,
                    'stock': 0
                }
        
        return jsonify({
            'success': True,
            'prices': prices
        })
        
    except Exception as e:
        logging.error(f"Error getting product prices: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در دریافت قیمت‌ها',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/orders/<int:order_id>', methods=['GET'])
def api_get_order(order_id):
    """
    API برای دریافت اطلاعات سفارش
    """
    try:
        order = BotOrder.query.get_or_404(order_id)
        
        # تبدیل آیتم‌ها از JSON به لیست
        items = []
        if order.order_items:
            try:
                items = json.loads(order.order_items)
                # اضافه کردن اطلاعات محصول برای هر آیتم
                for item in items:
                    product_name = item.get('product_name', '')
                    if product_name:
                        # جستجوی محصول در دیتابیس
                        product = Product.query.filter(Product.name.ilike(f'%{product_name}%')).first()
                        if product:
                            item['unit_price'] = product.price
                            item['product_image'] = product.image_url if hasattr(product, 'image_url') else None
                            item['status'] = 'موجود' if product.stock_quantity > 0 else 'عدم موجودی'
                        else:
                            item['unit_price'] = 0
                            item['product_image'] = None
                            item['status'] = 'عدم موجودی'
            except:
                items = []
        
        # اگر سفارش آیتم‌های جداگانه دارد
        if order.items.count() > 0:
            items = []
            for item in order.items:
                item_data = {
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'total_price': item.total_price,
                    'status': item.status,
                    'photo': item.photo,  # اضافه کردن عکس محصول
                    'photo_url': f'/static/product_pics/{item.photo}' if item.photo else None
                }
                items.append(item_data)
        
        return jsonify({
            'success': True,
            'data': {
                'id': order.id,
                'status': order.status,
                'total_amount': order.total_amount,
                'items': items,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'updated_at': order.updated_at.isoformat() if order.updated_at else None,
                'card_number': '6219-8619-0954-8298',  
                'card_holder': 'میثم قادری',           
                'bank': 'بانک سامان'                    
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطا در دریافت اطلاعات سفارش',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def api_update_order_status(order_id):
    """
    API برای بروزرسانی وضعیت سفارش
    """
    try:
        order = BotOrder.query.get_or_404(order_id)
        data = request.get_json()
        
        new_status = data.get('status')
        if not new_status:
            return jsonify({
                'success': False,
                'message': 'وضعیت جدید الزامی است'
            }), 400
        
        # بروزرسانی وضعیت
        order.status = new_status
        order.updated_at = datetime.datetime.now()
        
        # اگر سفارش تحویل داده شد، محاسبه کمیسیون
        if new_status == 'تحویل داده شده' and order.mechanic and not order.commission_amount:
            commission_amount = (order.total_price * order.mechanic.commission_percentage) / 100
            order.commission_amount = commission_amount
            order.mechanic.total_commission += commission_amount
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'وضعیت سفارش بروزرسانی شد'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'خطا در بروزرسانی وضعیت',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/orders/<int:order_id>/upload_receipt', methods=['POST'])
def api_upload_receipt(order_id):
    """
    API برای آپلود رسید پرداخت
    """
    try:
        order = BotOrder.query.get_or_404(order_id)
        
        # بررسی وجود فایل در request
        if 'receipt_image' not in request.files:
            return jsonify({
                'success': False,
                'message': 'فایل رسید ارسال نشده است'
            }), 400
        
        file = request.files['receipt_image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'فایل انتخاب نشده است'
            }), 400
        
        # ایجاد پوشه bot_receipts اگر وجود ندارد
        receipts_dir = os.path.join(current_app.root_path, 'static', 'bot_receipts')
        os.makedirs(receipts_dir, exist_ok=True)
        
        # ذخیره فایل
        filename = f'receipt_{order_id}_{int(datetime.datetime.now().timestamp())}.jpg'
        file_path = os.path.join(receipts_dir, filename)
        file.save(file_path)
        
        # بروزرسانی وضعیت سفارش
        order.status = 'در انتظار تایید پرداخت'
        order.receipt_image = f'bot_receipts/{filename}'  # مسیر نسبی برای نمایش
        order.updated_at = datetime.datetime.now()
        
        # اضافه کردن لاگ برای بررسی
        logging.info(f"✅ رسید سفارش {order_id} با موفقیت آپلود شد: {file_path}")
        logging.info(f"✅ receipt_image field set to: {order.receipt_image}")
        
        db.session.commit()
        
        # بررسی بعد از commit
        db.session.refresh(order)
        logging.info(f"✅ After commit - receipt_image: {order.receipt_image}")
        
        return jsonify({
            'success': True,
            'message': 'رسید پرداخت با موفقیت آپلود شد',
            'receipt_path': f'bot_receipts/{filename}'
        })
        
    except Exception as e:
        logging.error(f"❌ خطا در آپلود رسید سفارش {order_id}: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در آپلود رسید پرداخت',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/mechanics', methods=['GET'])
@login_required
@permission_required('view_mechanics')
def api_get_mechanics():
    """
    API برای دریافت لیست مکانیک‌های تایید شده
    """
    try:
        mechanics = Mechanic.query.filter_by(is_approved=True).all()
        
        result = []
        for mechanic in mechanics:
            result.append({
                'id': mechanic.id,
                'telegram_id': mechanic.telegram_id,
                'full_name': mechanic.full_name,
                'phone_number': mechanic.phone_number,
                'commission_percentage': mechanic.commission_percentage,
                'total_orders': mechanic.total_orders,
                'total_commission': mechanic.total_commission
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطا در دریافت مکانیک‌ها',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/products', methods=['GET'])
def api_get_products():
    """
    API برای دریافت لیست محصولات
    """
    try:
        products = Product.query.filter_by(is_active=True).all()
        
        result = []
        for product in products:
            result.append({
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'description': product.description,
                'category': product.category.name if product.category else None,
                'stock_quantity': product.stock_quantity
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'total': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطا در دریافت محصولات',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/mechanics/register', methods=['POST'])
def api_register_mechanic():
    """
    API برای ثبت‌نام مکانیک از ربات
    """
    try:
        data = request.get_json()
        
        # بررسی داده‌های ضروری
        required_fields = ['telegram_id', 'first_name', 'phone_number']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'فیلد {field} الزامی است'
                }), 400
        
        # بررسی تکراری نبودن
        existing_mechanic = Mechanic.query.filter_by(telegram_id=data['telegram_id']).first()
        if existing_mechanic:
            return jsonify({
                'success': False,
                'message': 'شما قبلاً ثبت‌نام کرده‌اید'
            }), 400
        
        # ایجاد مکانیک جدید
        mechanic = Mechanic(
            telegram_id=data['telegram_id'],
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
            phone_number=data['phone_number'],
            card_number=data.get('card_number', ''),
            sheba_number=data.get('sheba_number', ''),
            shop_address=data.get('shop_address', ''),
            business_license=data.get('business_license', '')
        )
        
        db.session.add(mechanic)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'درخواست ثبت‌نام با موفقیت ارسال شد',
            'mechanic_id': mechanic.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'خطا در ثبت‌نام',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/notifications', methods=['GET'])
@login_required
@permission_required('view_notifications')
def api_get_notifications():
    """
    API برای دریافت اعلان‌های جدید
    """
    try:
        # اعلان‌های مکانیک‌های جدید
        new_mechanics = Mechanic.query.filter_by(is_approved=False).count()
        
        # اعلان‌های سفارشات جدید
        new_orders = BotOrder.query.filter_by(status='در انتظار تایید').count()
        
        return jsonify({
            'success': True,
            'data': {
                'new_mechanics': new_mechanics,
                'new_orders': new_orders,
                'total_notifications': new_mechanics + new_orders
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطا در دریافت اعلان‌ها',
            'error': str(e)
        }), 500


@telegram_bot_bp.route('/api/test', methods=['GET'])
def api_test():
    """
    API تست برای بررسی اتصال
    """
    return jsonify({
        'success': True,
        'message': 'اتصال با موفقیت برقرار است',
        'timestamp': datetime.datetime.now().isoformat()
    })


@telegram_bot_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook برای دریافت پیام‌های ربات
    """
    try:
        data = request.get_json()
        
        # بررسی نوع پیام
        if 'message' in data:
            message = data['message']
            
            # پردازش پیام‌های مختلف
            if 'text' in message:
                text = message['text']
                
                # دستور ثبت‌نام
                if text.startswith('/register'):
                    return handle_register_command(message)
                
                # دستور سفارش
                elif text.startswith('/order'):
                    return handle_order_command(message)
                
                # سایر دستورات
                else:
                    return jsonify({'success': True, 'message': 'پیام دریافت شد'})
        
        return jsonify({'success': True, 'message': 'Webhook processed'})
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'خطا در پردازش webhook',
            'error': str(e)
        }), 500


def handle_register_command(message):
    """
    پردازش دستور ثبت‌نام
    """
    # این تابع در آینده پیاده‌سازی خواهد شد
    return jsonify({'success': True, 'message': 'دستور ثبت‌نام دریافت شد'})


def handle_order_command(message):
    """
    پردازش دستور سفارش
    """
    # این تابع در آینده پیاده‌سازی خواهد شد
    return jsonify({'success': True, 'message': 'دستور سفارش دریافت شد'}) 


@telegram_bot_bp.route('/api/notify_payment_confirmed', methods=['POST'])
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
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return jsonify({
                'success': False,
                'message': 'Bot token یافت نشد'
            }), 500
        
        # ارسال پیام به کاربر
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": int(telegram_id),
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logging.info(f"[API] Payment confirmation message sent to user {telegram_id}")
            return jsonify({
                'success': True,
                'message': 'پیام با موفقیت ارسال شد'
            })
        else:
            logging.error(f"[API] Failed to send message to user {telegram_id}: {response.status_code}")
            return jsonify({
                'success': False,
                'message': 'خطا در ارسال پیام'
            }), 500
            
    except Exception as e:
        logging.error(f"[API] Error in notify_payment_confirmed: {e}")
        return jsonify({
            'success': False,
            'message': 'خطا در اطلاع‌رسانی',
            'error': str(e)
        }), 500 