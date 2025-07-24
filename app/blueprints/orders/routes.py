# ---------------------------------------------
# فایل: routes.py (orders)
# توضیح: مدیریت سفارشات، مشاهده، ویرایش وضعیت، اعمال و حذف کوپن، صدور فاکتور
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request, make_response
from flask_login import login_required
from app import db
from app.models import Order, Coupon, InStoreOrder, Customer, BotOrder
from app.decorators import permission_required

orders_bp = Blueprint('orders', __name__, template_folder='templates')


@orders_bp.route('/')
@login_required
@permission_required('manage_orders')  # ⬇️ اعمال دسترسی
def index():
    """
    صفحه اصلی مدیریت سفارشات (نمایش لیست سفارشات)
    """
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search_query = request.args.get('q', '').strip()
    type_filter = request.args.get('type', '').strip()
    all_orders = Order.query.order_by(Order.order_date.desc()).all()
    all_instore = InStoreOrder.query.order_by(InStoreOrder.created_at.desc()).all()
    all_bot_orders = BotOrder.query.order_by(BotOrder.created_at.desc()).all()
    
    # تبدیل هر سفارش به دیکشنری با نوع سفارش
    orders_combined = []
    for o in all_orders:
        orders_combined.append({
            'id': o.id,
            'customer': o.customer,
            'date': o.order_date,
            'total_price': o.total_price,
            'status': o.status,
            'type': 'تلگرام',
            'view_url': url_for('orders.view_order', order_id=o.id)
        })
    for i in all_instore:
        orders_combined.append({
            'id': i.id,
            'customer': i.customer,
            'date': i.created_at,
            'total_price': i.total_price,
            'status': i.status,
            'type': 'حضوری'
            # 'view_url' حذف شد
        })
    for b in all_bot_orders:
        # ایجاد مشتری مجازی برای سفارشات ربات
        virtual_customer = type('obj', (object,), {
            'full_name': b.customer_name or f'مکانیک {b.telegram_id}',
            'phone_number': b.customer_phone,
            'first_name': b.customer_name or f'مکانیک {b.telegram_id}',
            'last_name': ''
        })
        orders_combined.append({
            'id': b.id,
            'customer': virtual_customer,
            'date': b.created_at,
            'total_price': b.total_amount,
            'status': b.status,
            'type': 'ربات',
            'view_url': url_for('bot_orders.detail', order_id=b.id)
        })
    # --- فیلتر جستجو ---
    if search_query:
        def match(order):
            c = order['customer']
            name = (c.first_name or '') + ' ' + (c.last_name or '') if c else ''
            phone = c.phone_number if c else ''
            return (search_query in name) or (search_query in phone)
        orders_combined = [o for o in orders_combined if match(o)]
    if type_filter:
        orders_combined = [o for o in orders_combined if o['type'] == type_filter]
    # مرتب‌سازی ترکیبی بر اساس تاریخ نزولی
    orders_combined.sort(key=lambda x: x['date'], reverse=True)
    # صفحه‌بندی دستی
    total = len(orders_combined)
    start = (page - 1) * per_page
    end = start + per_page
    items = orders_combined[start:end]
    class Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
        @property
        def has_prev(self):
            return self.page > 1
        @property
        def has_next(self):
            return self.page < self.pages
        @property
        def prev_num(self):
            return self.page - 1
        @property
        def next_num(self):
            return self.page + 1
    orders = Pagination(items, page, per_page, total)
    return render_template('orders.html',
                           orders=orders,
                           title="مدیریت سفارشات",
                           search_query=search_query,
                           type_filter=type_filter)


@orders_bp.route('/view/<int:order_id>')
@login_required
@permission_required('manage_orders')  # ⬇️ اعمال دسترسی
def view_order(order_id):
    """
    نمایش جزئیات یک سفارش خاص و وضعیت آن
    """
    order = db.session.get(Order, order_id)
    if not order:
        flash('سفارش مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('orders.index'))

    statuses = [
        'در حال بررسی', 'تایید شده', 'ارسال شده', 'تحویل داده شد', 'لغو شده'
    ]
    return render_template('view_order.html',
                           order=order,
                           statuses=statuses,
                           title=f"جزئیات سفارش #{order.id}")


@orders_bp.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
@permission_required('manage_orders')  # ⬇️ اعمال دسترسی
def update_status(order_id):
    """
    تغییر وضعیت سفارش توسط مدیر
    """
    order = db.session.get(Order, order_id)
    if not order:
        flash('سفارش مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('orders.index'))

    new_status = request.form.get('status')
    if new_status:
        order.status = new_status
        db.session.commit()
        flash(
            f'وضعیت سفارش #{order.id} با موفقیت به "{new_status}" تغییر کرد.',
            'success')
    else:
        flash('وضعیت انتخاب نشده است.', 'warning')
    return redirect(url_for('orders.view_order', order_id=order.id))


@orders_bp.route('/invoice/<int:order_id>')
@login_required
@permission_required('manage_orders')  # ⬇️ اعمال دسترسی
def invoice(order_id):
    """
    صدور و نمایش فاکتور سفارش
    """
    order = db.session.get(Order, order_id)
    if not order:
        flash('سفارش مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('orders.index'))

    return render_template('invoice.html',
                           order=order,
                           title=f"فاکتور سفارش #{order.id}")


@orders_bp.route('/apply_coupon/<int:order_id>', methods=['POST'])
@login_required
@permission_required('manage_orders')
def apply_coupon(order_id):
    """
    اعمال کوپن تخفیف روی سفارش
    """
    order = db.session.get(Order, order_id)
    if not order:
        flash('سفارش مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('orders.index'))

    coupon_code = request.form.get('coupon_code')
    if not coupon_code:
        flash('کد کوپن وارد نشده است.', 'warning')
        return redirect(url_for('orders.view_order', order_id=order.id))

    # پیدا کردن کوپن
    coupon = Coupon.query.filter_by(code=coupon_code).first()
    if not coupon:
        flash('کوپن یافت نشد.', 'warning')
        return redirect(url_for('orders.view_order', order_id=order.id))

    # اعمال کوپن
    success, message = order.apply_coupon(coupon)
    if success:
        db.session.commit()
        flash(message, 'success')
    else:
        flash(message, 'warning')

    return redirect(url_for('orders.view_order', order_id=order.id))


@orders_bp.route('/remove_coupon/<int:order_id>', methods=['POST'])
@login_required
@permission_required('manage_orders')
def remove_coupon(order_id):
    """
    حذف کوپن تخفیف از سفارش
    """
    order = db.session.get(Order, order_id)
    if not order:
        flash('سفارش مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('orders.index'))

    success, message = order.remove_coupon()
    if success:
        db.session.commit()
        flash(message, 'success')
    else:
        flash(message, 'warning')

    return redirect(url_for('orders.view_order', order_id=order.id))
