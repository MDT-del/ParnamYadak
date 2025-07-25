# ---------------------------------------------
# فایل: routes.py (orders)
# توضیح: مدیریت سفارشات، مشاهده، ویرایش وضعیت، صدور فاکتور
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request, make_response
from flask_login import login_required
from app import db
from app.models import Order, InStoreOrder, Person, BotOrder
from app.decorators import permission_required

orders_bp = Blueprint('orders', __name__, template_folder='templates')


@orders_bp.route('/')
@login_required
@permission_required('manage_orders')
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
            'person': o.person,
            'date': o.order_date,
            'total_price': o.total_price,
            'status': o.status,
            'type': 'تلگرام',
            'view_url': url_for('orders.view_order', order_id=o.id)
        })
    for i in all_instore:
        orders_combined.append({
            'id': i.id,
            'person': i.person,
            'date': i.created_at,
            'total_price': i.total_price,
            'status': i.status,
            'type': 'حضوری'
        })
    for b in all_bot_orders:
        virtual_person = type('obj', (object,), {
            'full_name': b.customer_name or f'مکانیک {b.telegram_id}',
            'phone_number': b.customer_phone
        })
        orders_combined.append({
            'id': b.id,
            'person': virtual_person,
            'date': b.created_at,
            'total_price': b.total_amount,
            'status': b.status,
            'type': 'ربات',
            'view_url': url_for('bot_orders.detail', order_id=b.id)
        })
    # --- فیلتر جستجو ---
    if search_query:
        def match(order):
            p = order['person']
            name = p.full_name if p else ''
            phone = p.phone_number if p else ''
            return (search_query in name) or (search_query in phone)
        orders_combined = [o for o in orders_combined if match(o)]
    if type_filter:
        orders_combined = [o for o in orders_combined if o['type'] == type_filter]
    orders_combined.sort(key=lambda x: x['date'], reverse=True)
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
@permission_required('manage_orders')
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
@permission_required('manage_orders')
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
@permission_required('manage_orders')
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