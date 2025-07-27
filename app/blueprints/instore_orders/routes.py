# ---------------------------------------------
# فایل: routes.py (instore_orders)
# توضیح: مدیریت سفارش حضوری (ثبت و لیست)
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request, make_response
from flask_login import login_required, current_user
from app import db
from app.models import InStoreOrder, Person, InventoryProduct, InventoryBatch
import json
from sqlalchemy import func, or_
import datetime as dt
from jdatetime import date as jdate
from datetime import datetime
# from sms_ir import SmsIr  # موقتاً غیرفعال
import http.client
import urllib.parse
from app.utils import fa_to_en_digits

ORDER_STATUSES = [
    'در حال پیگیری', 'آماده تحویل', 'تحویل داده شده', 'لغو شده', 'مرجوع شده'
]

instore_orders_bp = Blueprint('instore_orders',
                              __name__,
                              template_folder='templates')


def to_bool(val):
    if isinstance(val, str):
        return val.strip().lower() in ['true', '1', 'on', 'yes']
    return bool(val)


def to_float(val, default=0):
    try:
        if val is None:
            return default
        sval = str(val).strip().lower()
        if sval == '' or sval == 'nan':
            return default
        return float(val)
    except Exception:
        return default


@instore_orders_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        customer_phone = request.form.get('customer_phone')
        products_info = request.form.get('products_info')
        total_price = request.form.get('total_price', 0)
        deposit_amount = to_float(request.form.get('deposit_amount', None), 0)
        product_type = request.form.get('product_type')
        shipping_required = to_bool(request.form.get('shipping_required'))
        store_stock = to_bool(request.form.get('store_stock'))
        notes = request.form.get('notes')
        province = request.form.get('province')
        city = request.form.get('city')
        address = request.form.get('address')
        postal_code = request.form.get('postal_code')
        status = request.form.get('status', 'در حال پیگیری')

        # اعتبارسنجی فیلدها
        if not customer_name or not customer_phone or not products_info or products_info.strip() == '[]':
            flash('نام مشتری، شماره تلفن و محصول نمی‌تواند خالی باشد.', 'error')
            return redirect(url_for('instore_orders.index'))

        # پیدا کردن یا ساخت مشتری بر اساس شماره تلفن
        customer = Person.query.filter_by(phone_number=fa_to_en_digits(customer_phone), person_type='customer').first()
        if not customer:
            customer = Person()
            customer.phone_number = fa_to_en_digits(customer_phone)
            customer.full_name = customer_name
            customer.person_type = 'customer'  # نوع مشتری
            customer.address = address  # ذخیره آدرس
            customer.province = province  # ذخیره استان
            customer.city = city  # ذخیره شهر
            customer.postal_code = postal_code  # ذخیره کد پستی
            customer.registration_date = datetime.now()
            db.session.add(customer)
            db.session.commit()
        # ثبت سفارش حضوری با ارجاع به customer_id
        order = InStoreOrder()
        order.person_id = customer.id
        order.products_info = products_info or '[]'
        order.total_price = total_price or 0
        order.deposit_amount = deposit_amount
        order.product_type = product_type or ''
        order.shipping_required = shipping_required
        order.store_stock = store_stock
        order.notes = notes or ''
        order.province = province or ''
        order.city = city or ''
        order.address = address or ''
        order.postal_code = postal_code or ''
        order.status = status or 'در حال پیگیری'
        order.created_by = current_user.id
        db.session.add(order)
        
        # فقط بررسی موجودی کافی بودن - بدون تغییر موجودی
        # موجودی در مرحله "آماده تحویل" رزرو می‌شود و در "تحویل داده شده" فروخته می‌شود
        if store_stock and products_info:
            try:
                products_list = json.loads(products_info)
                for product_item in products_list:
                    if 'product_id' in product_item and product_item['product_id']:
                        product = InventoryProduct.query.get(product_item['product_id'])
                        if product:
                            qty = int(product_item.get('qty', 0))
                            if product.available_quantity < qty:
                                flash(f'موجودی محصول "{product.name}" کافی نیست. موجودی: {product.available_quantity}, درخواستی: {qty}', 'error')
                                db.session.rollback()
                                return redirect(url_for('instore_orders.index'))
            except Exception as e:
                flash(f'خطا در بررسی موجودی محصولات: {str(e)}', 'error')
                db.session.rollback()
                return redirect(url_for('instore_orders.index'))
        
        # بروزرسانی اطلاعات اولین سفارش مشتری
        customer.update_first_order_info()
        db.session.add(customer)
        
        db.session.commit()
        flash('سفارش حضوری با موفقیت ثبت شد.', 'success')
        return redirect(url_for('instore_orders.index'))
    # --- فیلتر و جستجو ---
    status_filter = request.args.get('status', None)
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10  # تعداد آیتم در هر صفحه
    
    query = InStoreOrder.query
    if status_filter:
        query = query.filter(InStoreOrder.status == status_filter)
    if search_query:
        # جستجو بر اساس نام مشتری و محصولات
        customer_ids = [c.id for c in Person.query.filter(Person.full_name.ilike(f'%{search_query}%'), Person.person_type=='customer').all()]
        query = query.filter(
            or_(InStoreOrder.person_id.in_(customer_ids),
                InStoreOrder.products_info.ilike(f'%{search_query}%')))
    
    # اعمال pagination
    orders = query.order_by(InStoreOrder.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    # --- آمار ---
    today = dt.date.today()
    start_30 = today - dt.timedelta(days=30)
    count_today = InStoreOrder.query.filter(
        func.date(InStoreOrder.created_at) == today).count()
    count_30days = InStoreOrder.query.filter(
        InStoreOrder.created_at >= start_30).count()
    status_counts = dict(
        db.session.query(InStoreOrder.status, func.count(
            InStoreOrder.id)).group_by(InStoreOrder.status).all())
    # تعداد سفارش تحویل داده شده
    delivered_count = InStoreOrder.query.filter(InStoreOrder.status == 'تحویل داده شده').count()
    # مجموع درآمد سفارش‌های تحویل داده شده
    total_income = db.session.query(func.coalesce(func.sum(InStoreOrder.total_price), 0)).filter(InStoreOrder.status == 'تحویل داده شده').scalar()
    total_instore_orders = InStoreOrder.query.count()
    stats = {
        'today': count_today,
        'last_30_days': count_30days,
        'status_counts': status_counts,
        'delivered': delivered_count,
        'total_income': total_income
    }
    # واکشی لیست محصولات برای نمایش در فرم
    products = InventoryProduct.query.order_by(InventoryProduct.name).all()
    products_dicts = []
    for p in products:
        d = p.__dict__.copy()
        d.pop('_sa_instance_state', None)
        products_dicts.append(d)
    return render_template('instore_orders/index.html',
                           orders=orders,
                           title='سفارش حضوری',
                           stats=stats,
                           status_filter=status_filter,
                           search_query=search_query,
                           products=products_dicts,
                           total_instore_orders=total_instore_orders)


@instore_orders_bp.route('/delete/<int:order_id>', methods=['POST'])
@login_required
def delete(order_id):
    order = InStoreOrder.query.get_or_404(order_id)
    
    # بازگرداندن موجودی محصولات اگر از انبار مغازه بود
    if order.store_stock and order.products_info:
        try:
            import json
            products_list = json.loads(order.products_info)
            for product_item in products_list:
                if 'product_id' in product_item and product_item['product_id']:
                    product = InventoryProduct.query.get(product_item['product_id'])
                    if product:
                        qty = int(product_item.get('qty', 0))
                        product.stock += qty
                        # کاهش آمار فروش
                        product.total_sales -= qty
                        product.total_revenue -= (qty * float(product_item.get('price', 0)))
        except Exception as e:
            flash(f'خطا در بازگرداندن موجودی محصولات: {str(e)}', 'error')
            return redirect(url_for('instore_orders.index'))
    
    db.session.delete(order)
    db.session.commit()
    flash('سفارش حضوری حذف شد.', 'success')
    return redirect(url_for('instore_orders.index'))


@instore_orders_bp.route('/print-invoices')
@login_required
def print_invoices():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    status = request.args.get('status')
    query = InStoreOrder.query
    # تبدیل تاریخ شمسی به میلادی
    if from_date:
        try:
            y, m, d = map(int, from_date.split('-'))
            from_greg = jdate(y, m, d).togregorian()
            query = query.filter(InStoreOrder.created_at >= from_greg)
        except Exception:
            pass
    if to_date:
        try:
            y, m, d = map(int, to_date.split('-'))
            to_greg = jdate(y, m, d).togregorian()
            # تا انتهای روز
            to_greg = datetime(to_greg.year, to_greg.month, to_greg.day, 23,
                               59, 59)
            query = query.filter(InStoreOrder.created_at <= to_greg)
        except Exception:
            pass
    if status:
        query = query.filter(InStoreOrder.status == status)
    orders = query.order_by(InStoreOrder.created_at.asc()).all()
    # آماده‌سازی محصولات هر سفارش
    import json
    orders_data = []
    for order in orders:
        try:
            products = json.loads(order.products_info)
        except Exception:
            products = []
        orders_data.append({'order': order, 'products': products})
    return render_template('instore_orders/print_invoices.html',
                           orders_data=orders_data,
                           from_date=from_date,
                           to_date=to_date,
                           status=status)


@instore_orders_bp.route('/change-status/<int:order_id>', methods=['POST'])
@login_required
def change_status(order_id):
    order = InStoreOrder.query.get_or_404(order_id)
    new_status = request.form.get('status')
    prev_status = order.status
    
    # بررسی محدودیت‌های تغییر وضعیت
    if prev_status == 'تحویل داده شده' and new_status == 'آماده تحویل':
        flash('سفارش تحویل داده شده را نمی‌توان به آماده تحویل برگرداند.', 'error')
        return redirect(url_for('instore_orders.index'))
    
    if new_status not in ORDER_STATUSES:
        flash('وضعیت نامعتبر است.', 'error')
        return redirect(url_for('instore_orders.index'))
    
    import json
    
    try:
        # ۱. رزرو موجودی هنگام آماده تحویل (مثل سفارش ربات)
        if new_status == 'آماده تحویل' and prev_status != 'آماده تحویل':
            if not order.store_stock or not order.products_info:
                flash('این سفارش از انبار مغازه نیست یا محصولی ندارد.', 'error')
                return redirect(url_for('instore_orders.index'))

            products_list = json.loads(order.products_info)
            for product_item in products_list:
                if 'product_id' in product_item and product_item['product_id']:
                    product = InventoryProduct.query.get(product_item['product_id'])
                    if not product:
                        flash(f'محصول با شناسه {product_item["product_id"]} یافت نشد.', 'error')
                        db.session.rollback()
                        return redirect(url_for('instore_orders.index'))

                    qty = int(product_item.get('qty', 0))
                    if qty <= 0:
                        continue

                    # بررسی موجودی کافی
                    if not product.can_reserve(qty):
                        flash(f'موجودی کافی برای محصول "{product.name}" وجود ندارد. موجودی قابل دسترس: {product.available_quantity}, درخواستی: {qty}', 'error')
                        db.session.rollback()
                        return redirect(url_for('instore_orders.index'))

                    # رزرو موجودی (مثل سفارش ربات)
                    product.reserve_quantity(qty)
        
        # ۲. فروش هنگام تحویل داده شده
        elif new_status == 'تحویل داده شده' and prev_status != 'تحویل داده شده':
            print(f"[DEBUG] Processing sale for order {order.id}: store_stock={order.store_stock}, has_products={bool(order.products_info)}")

            # فقط بررسی وجود محصولات - store_stock اختیاری است
            if not order.products_info:
                flash('این سفارش محصولی ندارد.', 'error')
                return redirect(url_for('instore_orders.index'))

            # اگر store_stock=false باشد، فقط وضعیت تغییر کند بدون تغییر موجودی
            if not order.store_stock:
                print(f"[DEBUG] Order {order.id} is not from store stock - only changing status")
                # تغییر وضعیت
                order.status = new_status
                db.session.commit()
                flash('وضعیت سفارش با موفقیت تغییر کرد.', 'success')
                return redirect(url_for('instore_orders.index'))
            
            products_list = json.loads(order.products_info)
            print(f"[DEBUG] Products to process: {len(products_list)}")

            for product_item in products_list:
                if 'product_id' in product_item and product_item['product_id']:
                    product = InventoryProduct.query.get(product_item['product_id'])
                    if not product:
                        print(f"[DEBUG] Product not found: {product_item['product_id']}")
                        continue

                    qty = int(product_item.get('qty', 0))
                    if qty <= 0:
                        print(f"[DEBUG] Invalid quantity for product {product.id}: {qty}")
                        continue

                    print(f"[DEBUG] Processing product {product.id} ({product.name}): qty={qty}")

                    # کسر از موجودی (FIFO) - مثل سفارش ربات
                    remaining = qty
                    batches = product.batches.filter(InventoryBatch.remaining_quantity > 0).order_by(InventoryBatch.created_at).all()
                    print(f"[DEBUG] Found {len(batches)} batches with remaining quantity")

                    for batch in batches:
                        if remaining <= 0:
                            break

                        available = min(batch.remaining_quantity, remaining)
                        print(f"[DEBUG] Batch {batch.id}: remaining={batch.remaining_quantity}, taking={available}")

                        batch.remaining_quantity -= available
                        batch.sold_quantity += available
                        remaining -= available

                        print(f"[DEBUG] Batch {batch.id} after: remaining={batch.remaining_quantity}, sold={batch.sold_quantity}")

                    if remaining > 0:
                        print(f"[DEBUG] Not enough stock for product {product.name}: needed={remaining}")
                        flash(f'موجودی کافی برای محصول "{product.name}" وجود ندارد.', 'error')
                        db.session.rollback()
                        return redirect(url_for('instore_orders.index'))

                    # کاهش رزرو و بروزرسانی موجودی
                    print(f"[DEBUG] Reducing reserved quantity: {product.reserved_quantity} - {qty}")
                    product.reserved_quantity -= qty
                    product.update_quantities()
                    print(f"[DEBUG] Product {product.id} after update: reserved={product.reserved_quantity}")
        
        # ۳. لغو رزرو هنگام لغو شده (قبل از فروش)
        elif new_status == 'لغو شده' and prev_status != 'لغو شده':
            if prev_status == 'تحویل داده شده':
                flash('سف��رش تحویل داده شده را نمی‌توان لغو کرد. برای مرجوعی از وضعیت "مرجوع شده" استفاده کنید.', 'error')
                return redirect(url_for('instore_orders.index'))
            
            if order.store_stock and order.products_info:
                # آزادسازی رزرو (مثل سفارش ربات)
                products_list = json.loads(order.products_info)
                for product_item in products_list:
                    if 'product_id' in product_item and product_item['product_id']:
                        product = InventoryProduct.query.get(product_item['product_id'])
                        if product:
                            qty = int(product_item.get('qty', 0))
                            if qty > 0:
                                # آزادسازی رزرو
                                product.reserved_quantity -= qty
                                product.available_quantity += qty
                                product.update_quantities()
        
        # ۴. مرجوعی (بعد از فروش) - فعلاً غیرفعال
        elif new_status == 'مرجوع شده' and prev_status == 'تحویل داده شده' and False:
            if order.store_stock and order.products_info:
                # بازگرداندن موجودی فروخته شده به پ��رت‌ها
                order_batches = InStoreOrderBatch.query.filter_by(order_id=order.id).all()
                for order_batch in order_batches:
                    if order_batch.sold_qty > 0:
                        batch = order_batch.batch
                        if batch:
                            # بازگرداندن موجودی به پارت
                            batch.remaining_quantity += order_batch.sold_qty
                            batch.sold_quantity -= order_batch.sold_qty
                            
                            # ثبت مرجوعی
                            order_batch.returned_qty += order_batch.sold_qty
                            order_batch.sold_qty = 0
                        
                        # بروزرسانی موجودی محصول
                        if batch:
                            product = batch.product
                            if product:
                                product.update_quantities()
        
        # تغییر وضعیت
        order.status = new_status
        db.session.commit()
        flash('وضعیت سفارش با موفقیت تغییر کرد.', 'success')
        
        # ارسال پیامک اگر وضعیت جدید "آماده تحویل" باشد
        if new_status == 'آماده تحویل':
            try:
                # اگر مقادیر ارسال پیامک تعریف نشده‌اند، ارسال انجام نشود
                username = locals().get('username', None)
                api_key = locals().get('api_key', None)
                line_number = locals().get('line_number', None)
                customer_name = order.person.full_name if order.person else 'مشتری'
                customer_mobile = order.person.phone_number if order.person else ''
                import json
                products = []
                try:
                    products = [p['name'] for p in json.loads(order.products_info)]
                except Exception:
                    pass
                products_str = "، ".join(products) if products else "سفارش شما"
                if username and api_key and line_number and customer_mobile:
                    message = f"آقا/خانم {customer_name} محصولات {products_str} آماده تحویل است لطفا مراجعه بفرمایید. باتشکر"
                    message_encoded = urllib.parse.quote(message)
                    url = f"/v1/send?username={username}&password={api_key}&mobile={customer_mobile}&line={line_number}&text={message_encoded}"
                    conn = http.client.HTTPSConnection("api.sms.ir")
                    payload = ''
                    headers = {'Accept': 'text/plain'}
                    conn.request("GET", url, payload, headers)
                    res = conn.getresponse()
                    data = res.read()
                    print(data.decode("utf-8"))
            except Exception as e:
                print(f"خطا در ارسال پیامک: {str(e)}")
        
    except Exception as e:
        flash(f'خطا در تغییر وضعیت سفارش: {str(e)}', 'error')
        db.session.rollback()
        return redirect(url_for('instore_orders.index'))
    
    return redirect(url_for('instore_orders.index'))
