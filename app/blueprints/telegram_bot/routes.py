# ---------------------------------------------
# فایل: routes.py (telegram_bot)
# توضیح: مسیرهای API برای ارتباط با ربات تلگرام
# ---------------------------------------------

from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from app.models import Person, BotOrder, BotOrderItem, InventoryProduct, db
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
        status = request.args.get('status', '')
        person_id = request.args.get('person_id', type=int)
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        limit = request.args.get('limit', 50, type=int)
        telegram_id = request.args.get('telegram_id', type=int)
        
        if telegram_id and not person_id:
            person = Person.query.filter_by(telegram_id=telegram_id).first()
            if person:
                person_id = person.id
                logging.info(f"[API ORDERS] Found person_id={person_id} for telegram_id={telegram_id}")
        
        logging.warning(f"[API ORDERS] Params: status={status}, person_id={person_id}, telegram_id={telegram_id}, limit={limit}")
        query = BotOrder.query
        
        if status:
            query = query.filter(BotOrder.status == status)
        
        if person_id and telegram_id:
            # اگر هر دو ارسال شده، با OR جستجو کن
            query = query.filter(
                db.or_(
                    BotOrder.person_id == person_id,
                    BotOrder.telegram_id == telegram_id
                )
            )
        elif person_id:
            query = query.filter(BotOrder.person_id == person_id)
        elif telegram_id:
            query = query.filter(BotOrder.telegram_id == telegram_id)
        
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
            items_list = []
            total_amount = 0
            
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
            
            if total_amount == 0 and hasattr(order, 'total_amount'):
                total_amount = order.total_amount
            
            result.append({
                'id': order.id,
                'customer_name': getattr(order, 'customer_name', None),
                'customer_phone': getattr(order, 'customer_phone', None),
                'person_id': getattr(order, 'person_id', None),
                'telegram_id': getattr(order, 'telegram_id', None),
                'status': getattr(order, 'status', None),
                'status_display': getattr(order, 'status', None),
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


@telegram_bot_bp.route('/api/bot/orders', methods=['POST'])
def api_create_bot_order():
    """
    API برای ایجاد سفارش جدید از ربات (بدون احراز هویت)
    """
    try:
        data = request.get_json()
        logging.info(f"[API] Received bot order data: {data}")
        
        if not data.get('person_id'):
            return jsonify({
                'success': False,
                'message': 'شناسه شخص الزامی است'
            }), 400
        
        if not data.get('items') or not isinstance(data['items'], list):
            return jsonify({
                'success': False,
                'message': 'لیست آیتم‌ها الزامی است'
            }), 400
        
        person = Person.query.get(data.get('person_id'))
        if not person:
            return jsonify({
                'success': False,
                'message': 'شخص یافت نشد'
            }), 400
        
        logging.info(f"[API] Found person: {person.full_name}")
        
        order = BotOrder(
            person_id=person.id,
            telegram_id=person.telegram_id,
            customer_phone=person.phone_number,
            customer_name=person.full_name,
            order_items=json.dumps(data['items']),
            total_amount=sum(item.get('total_price', 0) for item in data['items']),
            status='در انتظار بررسی'
        )
        
        db.session.add(order)
        db.session.commit()
        
        logging.info(f"[API] Created order with ID: {order.id}")
        
        for idx, item_data in enumerate(data['items']):
            photo_path = None
            
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
            order_item = BotOrderItem(
                order_id=order.id,
                product_name=item_data.get('product_name', ''),
                quantity=item_data.get('quantity', 0),
                unit_price=item_data.get('unit_price', 0),
                total_price=item_data.get('total_price', 0),
                photo=item_data.get('photo'),
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
            product = InventoryProduct.query.filter(InventoryProduct.name.ilike(f'%{product_name}%')).first()
            if product:
                prices[product_name] = {
                    'price': product.batches.first().purchase_price if product.batches.first() else 0,
                    'available': product.available_quantity > 0,
                    'stock': product.available_quantity
                }
            else:
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
        
        items = []
        if order.items.count() > 0:
            for item in order.items:
                item_data = {
                    'product_name': item.product_name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'total_price': item.total_price,
                    'status': item.status,
                    'photo': item.photo,
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
                'card_number': '6219-8618-6017-5487',  
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
        
        order.status = new_status
        order.updated_at = datetime.datetime.now()
        
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
        
        receipts_dir = os.path.join(current_app.root_path, 'static', 'bot_receipts')
        os.makedirs(receipts_dir, exist_ok=True)
        
        filename = f'receipt_{order_id}_{int(datetime.datetime.now().timestamp())}.jpg'
        file_path = os.path.join(receipts_dir, filename)
        file.save(file_path)
        
        order.status = 'در انتظار تایید پرداخت'
        order.receipt_image = f'bot_receipts/{filename}'
        order.updated_at = datetime.datetime.now()
        
        logging.info(f"✅ رسید سفارش {order_id} با موفقیت آپلود شد: {file_path}")
        logging.info(f"✅ receipt_image field set to: {order.receipt_image}")
        
        db.session.commit()
        
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
        persons = Person.query.filter_by(person_type='mechanic').all()
        
        result = []
        for person in persons:
            result.append({
                'id': person.id,
                'telegram_id': person.telegram_id,
                'full_name': person.full_name,
                'phone_number': person.phone_number,
                'commission_percentage': person.mechanic_profile.commission_percentage if person.mechanic_profile else 0,
                'total_orders': person.total_orders,
                'total_commission': 0 # This needs to be calculated
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
        products = InventoryProduct.query.all()
        
        result = []
        for product in products:
            result.append({
                'id': product.id,
                'name': product.name,
                'price': product.batches.first().purchase_price if product.batches.first() else 0,
                'description': '',
                'category': '',
                'stock_quantity': product.available_quantity
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
        
        # استفاده از full_name به عنوان فیلد استاندارد
        full_name = data.get('full_name', '').strip()
        
        # پشتیبانی از فرمت قدیمی برای سازگاری با نسخه‌های قبلی
        if not full_name:
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            full_name = f"{first_name} {last_name}".strip()
        
        telegram_id = data.get('telegram_id')
        phone_number = data.get('phone_number', '').strip()
        username = data.get('username', '').strip()
        
        # بررسی فیلدهای الزامی
        if not all([telegram_id, full_name, phone_number]):
            return jsonify({
                'success': False,
                'message': 'فیلدهای telegram_id، نام کامل و شماره تلفن الزامی است'
            }), 400
        
        # بررسی تکراری نبودن telegram_id
        existing_person = Person.query.filter_by(telegram_id=telegram_id, person_type='mechanic').first()
        if existing_person:
            return jsonify({
                'success': False,
                'message': 'شما قبلاً ثبت‌نام کرده‌اید'
            }), 400
        
        # بررسی تکراری نبودن شماره تلفن
        existing_phone = Person.query.filter_by(phone_number=phone_number, person_type='mechanic').first()
        if existing_phone:
            return jsonify({
                'success': False,
                'message': 'این شماره تلفن قبلاً ثبت شده است'
            }), 400
        
        # ایجاد شخص جدید
        person = Person(
            telegram_id=telegram_id,
            full_name=full_name,
            phone_number=phone_number,
            person_type='mechanic',
            username=username
        )
        
        db.session.add(person)
        db.session.flush()  # برای دریافت person.id
        
        # ایجاد پروفایل مکانیک
        from app.models import MechanicProfile
        mechanic_profile = MechanicProfile(
            person_id=person.id,
            card_number=data.get('card_number', ''),
            sheba_number=data.get('sheba_number', ''),
            shop_address=data.get('shop_address', ''),
            business_license=data.get('business_license', ''),
            is_approved=False,
            is_rejected=False
        )
        
        db.session.add(mechanic_profile)
        db.session.commit()
        
        # ایجاد اعلان برای ادمین‌ها
        try:
            from app.models import Notification, Role
            admin_role = Role.query.filter_by(name='admin').first()
            if admin_role:
                notification = Notification(
                    message=f'مکانیک جدید {full_name} ثبت‌نام کرده است',
                    role_id=admin_role.id
                )
                db.session.add(notification)
                db.session.commit()
        except Exception as e:
            logging.error(f"Error creating admin notification: {e}")
        
        return jsonify({
            'success': True,
            'message': 'درخواست ثبت‌نام با موفقیت ارسال شد',
            'person_id': person.id
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in mechanic registration: {e}")
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
        new_mechanics = Person.query.filter_by(person_type='mechanic').count()
        
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
        
        if 'message' in data:
            message = data['message']
            
            if 'text' in message:
                text = message['text']
                
                if text.startswith('/register'):
                    return handle_register_command(message)
                
                elif text.startswith('/order'):
                    return handle_order_command(message)
                
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
    return jsonify({'success': True, 'message': 'دستور ثبت‌نام دریافت شد'})


def handle_order_command(message):
    """
    پردازش دستور سفارش
    """
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
        
        import os
        from dotenv import load_dotenv
        
        bot_config_path = os.path.join(os.path.dirname(__file__), '../../../bot/bot_config.env')
        load_dotenv(bot_config_path)
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            return jsonify({
                'success': False,
                'message': 'Bot token یافت نشد'
            }), 500
        
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