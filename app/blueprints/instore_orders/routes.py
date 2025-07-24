# ---------------------------------------------
# فایل: routes.py (instore_orders)
# توضیح: مدیریت سفارش حضوری (ثبت و لیست)
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request, make_response
from flask_login import login_required, current_user
from app import db
from app.models import InStoreOrder, Product, Customer, InventoryProduct
import json
from sqlalchemy import func, or_
import datetime as dt
from jdatetime import date as jdate
from datetime import datetime
# from sms_ir import SmsIr  # موقتاً غیرفعال
import http.client
import urllib.parse

ORDER_STATUSES = [
    'در حال پیگیری', 'آماده تحویل', 'تحویل داده شده', 'لغو شده'
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

        # پیدا کردن یا ساخت مشتری بر اساس شماره تلفن
        customer = Customer.query.filter_by(phone_number=fa_to_en_digits(customer_phone)).first()
        if not customer:
            customer = Customer()
            customer.phone_number = fa_to_en_digits(customer_phone)
            customer.first_name = customer_name
            customer.customer_type = 'حضوری'  # نوع مشتری حضوری
            customer.address = address  # ذخیره آدرس
            customer.province = province  # ذخیره استان
            customer.city = city  # ذخیره شهر
            customer.postal_code = postal_code  # ذخیره کد پستی
            customer.registration_date = datetime.now()
            db.session.add(customer)
            db.session.commit()
        # ثبت سفارش حضوری با ارجاع به customer_id
        order = InStoreOrder()
        order.customer_id = customer.id
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
        
        # کاهش موجودی محصولات اگر از انبار مغازه باشد
        if store_stock and products_info:
            try:
                products_list = json.loads(products_info)
                for product_item in products_list:
                    if 'product_id' in product_item and product_item['product_id']:
                        product = InventoryProduct.query.get(product_item['product_id'])
                        if product:
                            qty = int(product_item.get('qty', 0))
                            if product.available_quantity >= qty:
                                product.available_quantity -= qty
                                product.sold_quantity += qty
                                product.total_quantity -= qty
                                product.updated_at = datetime.now()
                            else:
                                flash(f'موجودی محصول "{product.name}" کافی نیست. موجودی: {product.available_quantity}, درخواستی: {qty}', 'error')
                                db.session.rollback()
                                return redirect(url_for('instore_orders.index'))
            except Exception as e:
                flash(f'خطا در کاهش موجودی محصولات: {str(e)}', 'error')
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
        query = query.filter(
            or_(InStoreOrder.customer_name.ilike(f'%{search_query}%'),
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
    stats = {
        'today': count_today,
        'last_30_days': count_30days,
        'status_counts': status_counts,
        'delivered': delivered_count,
        'total_income': total_income
    }
    # واکشی لیست محصولات برای نمایش در فرم
    products = Product.query.order_by(Product.name).all()
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
                           products=products_dicts)


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
                    product = Product.query.get(product_item['product_id'])
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
    import json
    if new_status in ORDER_STATUSES:
        # رزرو موجودی هنگام آماده تحویل
        if new_status == 'آماده تحویل' and prev_status != 'آماده تحویل':
            try:
                if order.store_stock and order.products_info:
                    products_list = json.loads(order.products_info)
                    for product_item in products_list:
                        if 'product_id' in product_item and product_item['product_id']:
                            product = InventoryProduct.query.get(product_item['product_id'])
                            if product:
                                qty = int(product_item.get('qty', 0))
                                if not product.reserve_quantity(qty):
                                    flash(f'موجودی محصول "{product.name}" کافی نیست. موجودی: {product.available_quantity}, درخواستی: {qty}', 'error')
                                    db.session.rollback()
                                    return redirect(url_for('instore_orders.index'))
                                product.update_quantities()
            except Exception as e:
                flash(f'خطا در رزرو موجودی محصولات: {str(e)}', 'error')
                db.session.rollback()
                return redirect(url_for('instore_orders.index'))
        # انتقال رزرو به فروخته شده هنگام تحویل داده شده
        if new_status == 'تحویل داده شده' and prev_status != 'تحویل داده شده':
            try:
                if order.store_stock and order.products_info:
                    products_list = json.loads(order.products_info)
                    for product_item in products_list:
                        if 'product_id' in product_item and product_item['product_id']:
                            product = InventoryProduct.query.get(product_item['product_id'])
                            if product:
                                qty = int(product_item.get('qty', 0))
                                # فقط اگر قبلاً رزرو شده بود
                                if product.reserved_quantity >= qty:
                                    product.release_reservation(qty)
                                    product.sold_quantity += qty
                                    product.total_quantity -= qty
                                    product.update_quantities()
                                else:
                                    flash(f'رزرو کافی برای محصول "{product.name}" وجود ندارد.', 'error')
                                    db.session.rollback()
                                    return redirect(url_for('instore_orders.index'))
            except Exception as e:
                flash(f'خطا در کسر نهایی موجودی محصولات: {str(e)}', 'error')
                db.session.rollback()
                return redirect(url_for('instore_orders.index'))
        # آزادسازی رزرو هنگام لغو شده
        if new_status == 'لغو شده' and prev_status != 'لغو شده':
            try:
                if order.store_stock and order.products_info:
                    products_list = json.loads(order.products_info)
                    for product_item in products_list:
                        if 'product_id' in product_item and product_item['product_id']:
                            product = InventoryProduct.query.get(product_item['product_id'])
                            if product:
                                qty = int(product_item.get('qty', 0))
                                product.release_reservation(qty)
                                product.update_quantities()
            except Exception as e:
                flash(f'خطا در بازگرداندن رزرو موجودی محصولات: {str(e)}', 'error')
                db.session.rollback()
                return redirect(url_for('instore_orders.index'))
        order.status = new_status
        db.session.commit()
        flash('وضعیت سفارش با موفقیت تغییر کرد.', 'success')
        # ارسال پیامک اگر وضعیت جدید "آماده تحویل" باشد (کد قبلی پیامک دست‌نخورده بماند)
        if new_status == 'آماده تحویل':
            try:
                # اگر مقادیر ارسال پیامک تعریف نشده‌اند، ارسال انجام نشود
                username = locals().get('username', None)
                api_key = locals().get('api_key', None)
                line_number = locals().get('line_number', None)
                customer_name = order.customer.first_name if order.customer else 'مشتری'
                customer_mobile = order.customer.phone_number if order.customer else ''
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
                    print('SMS API response:', data.decode("utf-8"))
            except Exception as e:
                print('خطا در ارسال پیامک:', e)
    else:
        flash('وضعیت نامعتبر است.', 'danger')
    return redirect(url_for('instore_orders.index'))
