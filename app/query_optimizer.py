# ---------------------------------------------
# فایل: query_optimizer.py
# توضیح: بهینه‌سازی کوئری‌های N+1 و بهبود عملکرد دیتابیس
# ---------------------------------------------

from sqlalchemy.orm import joinedload, selectinload, subqueryload
from sqlalchemy import func, and_, or_, desc, asc
from app.models import (
    Product, Category, Order, OrderItem, Customer, User, Role, 
    SupportTicket, TicketMessage, BroadcastMessage, PreOrder,
    InStoreOrder, Task, Notification, FinancialTransaction
)
from app import db


class QueryOptimizer:
    """
    کلاس بهینه‌سازی کوئری‌های N+1
    """
    
    @staticmethod
    def get_products_with_categories():
        """
        دریافت محصولات با دسته‌بندی‌ها (بهینه‌سازی N+1)
        """
        return Product.query.options(
            joinedload(Product.categories)
        ).order_by(Product.id.desc())
    
    @staticmethod
    def get_products_with_categories_and_stats():
        """
        دریافت محصولات با دسته‌بندی‌ها و آمار فروش
        """
        return Product.query.options(
            joinedload(Product.categories)
        ).order_by(Product.total_sales.desc())
    
    @staticmethod
    def get_orders_with_details():
        """
        دریافت سفارشات با جزئیات کامل (بهینه‌سازی N+1)
        """
        return Order.query.options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.coupon)
        ).order_by(Order.order_date.desc())
    
    @staticmethod
    def get_customers_with_stats():
        """
        دریافت مشتریان با آمار کامل
        """
        from app.models import Person
        return Person.query.filter_by(person_type='customer').options(
            selectinload(Person.orders),
            selectinload(Person.instore_orders),
            selectinload(Person.pre_orders)
        ).order_by(Person.total_spent.desc())
    
    @staticmethod
    def get_users_with_roles():
        """
        دریافت کاربران با نقش‌ها و مجوزها
        """
        return User.query.options(
            joinedload(User.roles).joinedload(Role.permissions)
        ).order_by(User.id)
    
    @staticmethod
    def get_support_tickets_with_messages():
        """
        دریافت تیکت‌های پشتیبانی با پیام‌ها
        """
        return SupportTicket.query.options(
            joinedload(SupportTicket.customer),
            selectinload(SupportTicket.messages)
        ).order_by(SupportTicket.created_at.desc())
    
    @staticmethod
    def get_broadcast_messages_with_stats():
        """
        دریافت پیام‌های همگانی با آمار
        """
        return BroadcastMessage.query.options(
            joinedload(BroadcastMessage.created_by_user)
        ).order_by(BroadcastMessage.created_at.desc())
    
    @staticmethod
    def get_pre_orders_with_customer():
        """
        دریافت پیش‌سفارشات با اطلاعات مشتری
        """
        return PreOrder.query.options(
            joinedload(PreOrder.customer),
            joinedload(PreOrder.user)
        ).order_by(PreOrder.created_at.desc())
    
    @staticmethod
    def get_instore_orders_with_customer():
        """
        دریافت سفارشات حضوری با اطلاعات مشتری
        """
        return InStoreOrder.query.options(
            joinedload(InStoreOrder.customer),
            joinedload(InStoreOrder.created_by_user)
        ).order_by(InStoreOrder.created_at.desc())
    
    @staticmethod
    def get_tasks_with_assignees():
        """
        دریافت وظایف با افراد مسئول
        """
        return Task.query.options(
            joinedload(Task.role),
            joinedload(Task.assigned_user),
            joinedload(Task.creator)
        ).order_by(Task.created_at.desc())
    
    @staticmethod
    def get_notifications_with_related():
        """
        دریافت اعلان‌ها با اطلاعات مرتبط
        """
        return Notification.query.options(
            joinedload(Notification.user),
            joinedload(Notification.role),
            joinedload(Notification.task)
        ).order_by(Notification.created_at.desc())
    
    @staticmethod
    def get_categories_with_products_count():
        """
        دریافت دسته‌بندی‌ها با تعداد محصولات
        """
        return Category.query.outerjoin(Product.categories).group_by(Category.id).add_columns(
            func.count(Product.id).label('products_count')
        ).order_by(Category.name)
    
    @staticmethod
    def get_customers_with_recent_orders(limit=5):
        """
        دریافت مشتریان با آخرین سفارشات
        """
        from app.models import Person, Order
        return Person.query.filter_by(person_type='customer').options(
            selectinload(Person.orders.and_(Order.order_date.isnot(None))).order_by(Order.order_date.desc()).limit(limit)
        ).order_by(Person.last_order_date.desc().nullslast())
    
    @staticmethod
    def get_products_with_low_stock(threshold=10):
        """
        دریافت محصولات با موجودی کم
        """
        return Product.query.filter(
            Product.stock <= threshold,
            Product.is_available == True
        ).options(
            joinedload(Product.categories)
        ).order_by(Product.stock.asc())
    
    @staticmethod
    def get_orders_by_status_with_customer(status):
        """
        دریافت سفارشات بر اساس وضعیت با اطلاعات مشتری
        """
        return Order.query.filter(
            Order.status == status
        ).options(
            joinedload(Order.customer),
            selectinload(Order.items)
        ).order_by(Order.order_date.desc())
    
    @staticmethod
    def get_financial_summary():
        """
        دریافت خلاصه مالی (بهینه‌سازی برای داشبورد)
        """
        from datetime import datetime, timedelta
        
        # آمار امروز
        today = datetime.now().date()
        today_stats = db.session.query(
            func.count(Order.id).label('orders_count'),
            func.sum(Order.final_price).label('total_revenue'),
            func.avg(Order.final_price).label('avg_order_value')
        ).filter(
            func.date(Order.order_date) == today
        ).first()
        
        # آمار هفته جاری
        week_start = today - timedelta(days=today.weekday())
        week_stats = db.session.query(
            func.count(Order.id).label('orders_count'),
            func.sum(Order.final_price).label('total_revenue')
        ).filter(
            func.date(Order.order_date) >= week_start
        ).first()
        
        # آمار ماه جاری
        month_start = today.replace(day=1)
        month_stats = db.session.query(
            func.count(Order.id).label('orders_count'),
            func.sum(Order.final_price).label('total_revenue')
        ).filter(
            func.date(Order.order_date) >= month_start
        ).first()
        
        return {
            'today': today_stats,
            'week': week_stats,
            'month': month_stats
        }


# توابع کمکی برای بهینه‌سازی کوئری‌های خاص
def optimize_product_listing(page=1, per_page=20, category_id=None, search=None):
    """
    بهینه‌سازی لیست محصولات با فیلترها
    """
    query = Product.query.options(
        joinedload(Product.categories)
    )
    
    if category_id:
        query = query.join(Product.categories).filter(Category.id == category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    return query.order_by(Product.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def optimize_customer_search(phone=None, name=None, page=1, per_page=20):
    """
    بهینه‌سازی جستجوی مشتریان
    """
    from app.models import Person
    query = Person.query.filter_by(person_type='customer')

    if phone:
        query = query.filter(Person.phone_number.ilike(f'%{phone}%'))

    if name:
        query = query.filter(Person.full_name.ilike(f'%{name}%'))

    return query.order_by(Person.registration_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def optimize_order_search(customer_id=None, status=None, date_from=None, date_to=None, page=1, per_page=20):
    """
    بهینه‌سازی جستجوی سفارشات
    """
    query = Order.query.options(
        joinedload(Order.customer),
        selectinload(Order.items)
    )
    
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    
    if status:
        query = query.filter(Order.status == status)
    
    if date_from:
        query = query.filter(Order.order_date >= date_from)
    
    if date_to:
        query = query.filter(Order.order_date <= date_to)
    
    return query.order_by(Order.order_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


# توابع جدید برای بهینه‌سازی database queries
def get_dashboard_stats_optimized():
    """
    بهینه‌سازی آمار داشبورد با یک کوئری
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # کوئری بهینه برای دریافت تمام آمار در یک بار
    stats = db.session.query(
        # آمار امروز
        func.sum(func.case((func.date(Order.order_date) == today, Order.final_price), else_=0)).label('today_revenue'),
        func.count(func.case((func.date(Order.order_date) == today, Order.id), else_=None)).label('today_orders'),
        
        # آمار هفته
        func.sum(func.case((func.date(Order.order_date) >= week_start, Order.final_price), else_=0)).label('week_revenue'),
        func.count(func.case((func.date(Order.order_date) >= week_start, Order.id), else_=None)).label('week_orders'),
        
        # آمار ماه
        func.sum(func.case((func.date(Order.order_date) >= month_start, Order.final_price), else_=0)).label('month_revenue'),
        func.count(func.case((func.date(Order.order_date) >= month_start, Order.id), else_=None)).label('month_orders'),
        
        # آمار کلی
        func.sum(Order.final_price).label('total_revenue'),
        func.count(Order.id).label('total_orders'),
        func.count(func.case((Person.person_type == 'customer', Person.id), else_=None)).label('total_customers'),
        func.count(Product.id).label('total_products')
    ).outerjoin(Person).outerjoin(Product).first()
    
    return {
        'today': {
            'revenue': stats.today_revenue or 0,
            'orders': stats.today_orders or 0
        },
        'week': {
            'revenue': stats.week_revenue or 0,
            'orders': stats.week_orders or 0
        },
        'month': {
            'revenue': stats.month_revenue or 0,
            'orders': stats.month_orders or 0
        },
        'total': {
            'revenue': stats.total_revenue or 0,
            'orders': stats.total_orders or 0,
            'customers': stats.total_customers or 0,
            'products': stats.total_products or 0
        }
    }


def get_recent_activities_optimized(limit=10):
    """
    بهینه‌سازی دریافت فعالیت‌های اخیر
    """
    # ترکیب سفارشات، پیش‌سفارشات و تیکت‌ها در یک کوئری
    orders = db.session.query(
        Order.id.label('id'),
        Order.order_date.label('date'),
        Order.status.label('status'),
        'order'.label('type'),
        Person.full_name.label('customer_name'),
        Order.final_price.label('amount')
    ).join(Person).filter(Person.person_type == 'customer').order_by(Order.order_date.desc()).limit(limit)
    
    pre_orders = db.session.query(
        PreOrder.id.label('id'),
        PreOrder.created_at.label('date'),
        PreOrder.status.label('status'),
        'pre_order'.label('type'),
        Person.full_name.label('customer_name'),
        PreOrder.total_price.label('amount')
    ).join(Person).filter(Person.person_type == 'customer').order_by(PreOrder.created_at.desc()).limit(limit)
    
    tickets = db.session.query(
        SupportTicket.id.label('id'),
        SupportTicket.created_at.label('date'),
        SupportTicket.status.label('status'),
        'ticket'.label('type'),
        Person.full_name.label('customer_name'),
        func.literal(0).label('amount')
    ).join(Person).filter(Person.person_type == 'customer').order_by(SupportTicket.created_at.desc()).limit(limit)
    
    # ترکیب نتایج
    all_activities = []
    
    for activity in orders.union(pre_orders).union(tickets).order_by(desc('date')).limit(limit):
        all_activities.append({
            'id': activity.id,
            'date': activity.date,
            'status': activity.status,
            'type': activity.type,
            'customer_name': activity.customer_name,
            'amount': activity.amount
        })
    
    return all_activities


def get_product_analytics_optimized():
    """
    بهینه‌سازی تحلیل محصولات
    """
    return db.session.query(
        Product.id,
        Product.name,
        Product.price,
        Product.stock,
        Product.total_sales,
        Product.total_revenue,
        func.count(OrderItem.id).label('order_count'),
        func.sum(OrderItem.quantity).label('total_quantity_sold')
    ).outerjoin(OrderItem).group_by(Product.id).order_by(desc(Product.total_sales)).all()


def get_customer_analytics_optimized():
    """
    بهینه‌سازی تحلیل مشتریان
    """
    return db.session.query(
        Person.id,
        Person.full_name,
        Person.phone_number,
        Person.total_orders,
        Person.total_spent,
        func.count(Order.id).label('recent_orders'),
        func.sum(Order.final_price).label('recent_spent')
    ).filter(Person.person_type == 'customer').outerjoin(Order).group_by(Person.id).order_by(desc(Person.total_spent)).all()


def get_sales_report_optimized(start_date=None, end_date=None):
    """
    بهینه‌سازی گزارش فروش
    """
    query = db.session.query(
        func.date(Order.order_date).label('date'),
        func.count(Order.id).label('orders_count'),
        func.sum(Order.final_price).label('total_revenue'),
        func.avg(Order.final_price).label('avg_order_value'),
        func.sum(Order.discount_amount).label('total_discount')
    ).group_by(func.date(Order.order_date))
    
    if start_date:
        query = query.filter(Order.order_date >= start_date)
    
    if end_date:
        query = query.filter(Order.order_date <= end_date)
    
    return query.order_by(desc('date')).all() 