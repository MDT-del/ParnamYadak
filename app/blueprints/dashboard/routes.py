# ---------------------------------------------
# فایل: routes.py (dashboard)
# توضیح: مدیریت داشبورد و نمایش آمار کلی سیستم
# ---------------------------------------------

from flask import render_template, Blueprint
from flask_login import login_required
from sqlalchemy import func
from app import db
from app.models import Order, Person, InStoreOrder, InventoryProduct, BotOrder
from app.decorators import permission_required
import json
import jdatetime
import datetime

# تعریف بلوپرینت
dashboard_bp = Blueprint('dashboard', __name__, template_folder='templates')


@dashboard_bp.route('/')
@login_required
@permission_required('view_dashboard')
def index():
    """
    ویو اصلی داشبورد
    نمایش آمار محصولات، سفارشات، مشتریان و نمودار فروش ماهانه
    """
    product_count = db.session.query(func.count(InventoryProduct.id)).scalar() or 0
    order_count = (db.session.query(func.count(Order.id)).scalar() or 0) + (db.session.query(func.count(InStoreOrder.id)).scalar() or 0) + (db.session.query(func.count(BotOrder.id)).filter(BotOrder.status.in_(['پرداخت شده', 'تکمیل شده'])).scalar() or 0)
    
    # شمارش مشتریان از مدل Person
    customer_count = db.session.query(func.count(Person.id)).filter(Person.person_type == 'customer').scalar() or 0
    
    total_revenue_order = db.session.query(func.sum(Order.total_price)).scalar() or 0
    total_revenue_instore = db.session.query(func.sum(InStoreOrder.total_price)).filter(InStoreOrder.status == 'تحویل داده شده').scalar() or 0
    total_revenue_bot = db.session.query(func.sum(BotOrder.total_amount)).filter(BotOrder.status.in_(['پرداخت شده', 'تکمیل شده'])).scalar() or 0
    total_revenue = total_revenue_order + total_revenue_instore + total_revenue_bot

    sales_data = []
    today = datetime.date.today()
    for i in range(12):
        month = today.month - i
        year = today.year
        if month <= 0:
            month += 12
            year -= 1

        monthly_sale_order = db.session.query(func.sum(Order.total_price)).filter(
            db.extract('year', Order.order_date) == year,
            db.extract('month', Order.order_date) == month).scalar() or 0

        monthly_sale_instore = db.session.query(func.sum(InStoreOrder.total_price)).filter(
            db.extract('year', InStoreOrder.created_at) == year,
            db.extract('month', InStoreOrder.created_at) == month,
            InStoreOrder.status == 'تحویل داده شده'
        ).scalar() or 0

        monthly_sale_bot = db.session.query(func.sum(BotOrder.total_amount)).filter(
            db.extract('year', BotOrder.created_at) == year,
            db.extract('month', BotOrder.created_at) == month,
            BotOrder.status.in_(['پرداخت شده', 'تکمیل شده'])
        ).scalar() or 0

        monthly_total = monthly_sale_order + monthly_sale_instore + monthly_sale_bot

        gregorian_date_obj = datetime.date(year, month, 1)
        shamsi_label = jdatetime.date.fromgregorian(
            date=gregorian_date_obj).strftime("%Y/%m")

        sales_data.insert(0, {'month': shamsi_label, 'total': monthly_total})

    chart_labels = json.dumps([item['month'] for item in sales_data])
    chart_values = json.dumps([item['total'] for item in sales_data])

    instore_order_count = db.session.query(func.count(InStoreOrder.id)).scalar() or 0
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(7).all()
    recent_instore_orders = InStoreOrder.query.order_by(InStoreOrder.created_at.desc()).limit(7).all()
    recent_bot_orders = BotOrder.query.filter(BotOrder.status.in_(['پرداخت شده', 'تکمیل شده'])).order_by(BotOrder.created_at.desc()).limit(7).all()
    
    combined = []
    for o in recent_orders:
        combined.append({
            'id': o.id,
            'total_price': o.total_price,
            'customer_name': o.person.full_name if o.person else '',
            'date': o.order_date,
            'type': 'telegram',
            'status': getattr(o, 'status', None)
        })
    for o in recent_instore_orders:
        combined.append({
            'id': o.id,
            'total_price': o.total_price,
            'customer_name': o.person.full_name if o.person else '',
            'date': o.created_at,
            'type': 'instore',
            'status': o.status
        })
    for o in recent_bot_orders:
        combined.append({
            'id': o.id,
            'total_price': o.total_amount,
            'customer_name': o.customer_name or f'مکانیک {o.telegram_id}',
            'date': o.created_at,
            'type': 'bot',
            'status': o.status
        })
    combined = sorted(combined, key=lambda x: x['date'], reverse=True)[:7]
    
    return render_template('dashboard.html',
                           title="داشبورد",
                           product_count=product_count,
                           order_count=order_count,
                           customer_count=customer_count,
                           total_revenue=total_revenue,
                           chart_labels=chart_labels,
                           chart_values=chart_values,
                           recent_orders_combined=combined,
                           instore_order_count=instore_order_count)