# ---------------------------------------------
# فایل: database_indexes.py
# توضیح: تعریف index های دیتابیس برای بهبود عملکرد کوئری‌ها
# ---------------------------------------------

from sqlalchemy import Index, UniqueConstraint
from app.models import (
    Product, Category, Order, OrderItem, Customer, User, 
    SupportTicket, BroadcastMessage, PreOrder, InStoreOrder,
    Task, Notification, Coupon, FinancialTransaction
)


# تعریف index های بهینه‌سازی شده
class DatabaseIndexes:
    """
    کلاس تعریف index های دیتابیس برای بهبود عملکرد
    """
    
    # Index های جدول Product
    product_name_index = Index('idx_product_name', Product.name)
    product_price_index = Index('idx_product_price', Product.price)
    product_stock_index = Index('idx_product_stock', Product.stock)
    product_available_index = Index('idx_product_available', Product.is_available)
    product_sales_index = Index('idx_product_total_sales', Product.total_sales)
    product_revenue_index = Index('idx_product_total_revenue', Product.total_revenue)
    
    # Index ترکیبی برای جستجوی محصولات
    product_search_index = Index(
        'idx_product_search', 
        Product.name, 
        Product.is_available, 
        Product.stock
    )
    
    # Index های جدول Category
    category_name_index = Index('idx_category_name', Category.name)
    category_parent_index = Index('idx_category_parent', Category.parent_id)
    
    # Index های جدول Order
    order_customer_index = Index('idx_order_customer', Order.customer_id)
    order_date_index = Index('idx_order_date', Order.order_date)
    order_status_index = Index('idx_order_status', Order.status)
    order_payment_status_index = Index('idx_order_payment_status', Order.payment_status)
    order_coupon_index = Index('idx_order_coupon', Order.coupon_id)
    
    # Index ترکیبی برای جستجوی سفارشات
    order_search_index = Index(
        'idx_order_search',
        Order.customer_id,
        Order.status,
        Order.order_date
    )
    
    # Index های جدول OrderItem
    orderitem_order_index = Index('idx_orderitem_order', OrderItem.order_id)
    orderitem_product_index = Index('idx_orderitem_product', OrderItem.product_id)
    
    # Index های جدول Customer
    customer_phone_index = Index('idx_customer_phone', Customer.phone_number)
    customer_telegram_index = Index('idx_customer_telegram', Customer.telegram_id)
    customer_device_index = Index('idx_customer_device', Customer.device_id)
    customer_level_index = Index('idx_customer_level', Customer.customer_level)
    customer_registration_index = Index('idx_customer_registration', Customer.registration_date)
    customer_last_order_index = Index('idx_customer_last_order', Customer.last_order_date)
    
    # Index ترکیبی برای جستجوی مشتریان
    customer_search_index = Index(
        'idx_customer_search',
        Customer.first_name,
        Customer.last_name,
        Customer.phone_number
    )
    
    # Index های جدول User
    user_username_index = Index('idx_user_username', User.username)
    user_failed_login_index = Index('idx_user_failed_login', User.failed_login_attempts)
    user_locked_index = Index('idx_user_locked', User.permanently_locked)
    
    # Index های جدول SupportTicket
    ticket_customer_index = Index('idx_ticket_customer', SupportTicket.customer_id)
    ticket_status_index = Index('idx_ticket_status', SupportTicket.status)
    ticket_priority_index = Index('idx_ticket_priority', SupportTicket.priority)
    ticket_category_index = Index('idx_ticket_category', SupportTicket.category)
    ticket_created_index = Index('idx_ticket_created', SupportTicket.created_at)
    
    # Index ترکیبی برای جستجوی تیکت‌ها
    ticket_search_index = Index(
        'idx_ticket_search',
        SupportTicket.status,
        SupportTicket.priority,
        SupportTicket.created_at
    )
    
    # Index های جدول TicketMessage
    ticketmessage_ticket_index = Index('idx_ticketmessage_ticket', TicketMessage.ticket_id)
    ticketmessage_sender_index = Index('idx_ticketmessage_sender', TicketMessage.sender_id)
    ticketmessage_created_index = Index('idx_ticketmessage_created', TicketMessage.created_at)
    
    # Index های جدول BroadcastMessage
    broadcast_status_index = Index('idx_broadcast_status', BroadcastMessage.status)
    broadcast_type_index = Index('idx_broadcast_type', BroadcastMessage.message_type)
    broadcast_target_index = Index('idx_broadcast_target', BroadcastMessage.target_type)
    broadcast_created_index = Index('idx_broadcast_created', BroadcastMessage.created_at)
    broadcast_scheduled_index = Index('idx_broadcast_scheduled', BroadcastMessage.scheduled_at)
    
    # Index های جدول PreOrder
    preorder_customer_index = Index('idx_preorder_customer', PreOrder.customer_id)
    preorder_status_index = Index('idx_preorder_status', PreOrder.status)
    preorder_created_index = Index('idx_preorder_created', PreOrder.created_at)
    preorder_user_index = Index('idx_preorder_user', PreOrder.created_by)
    
    # Index ترکیبی برای جستجوی پیش‌سفارشات
    preorder_search_index = Index(
        'idx_preorder_search',
        PreOrder.status,
        PreOrder.created_at,
        PreOrder.customer_id
    )
    
    # Index های جدول InStoreOrder
    instoreorder_customer_index = Index('idx_instoreorder_customer', InStoreOrder.customer_id)
    instoreorder_status_index = Index('idx_instoreorder_status', InStoreOrder.status)
    instoreorder_created_index = Index('idx_instoreorder_created', InStoreOrder.created_at)
    instoreorder_user_index = Index('idx_instoreorder_user', InStoreOrder.created_by)
    
    # Index های جدول Task
    task_status_index = Index('idx_task_status', Task.status)
    task_role_index = Index('idx_task_role', Task.role_id)
    task_assigned_index = Index('idx_task_assigned', Task.assigned_user_id)
    task_creator_index = Index('idx_task_creator', Task.created_by)
    task_created_index = Index('idx_task_created', Task.created_at)
    
    # Index ترکیبی برای جستجوی وظایف
    task_search_index = Index(
        'idx_task_search',
        Task.status,
        Task.assigned_user_id,
        Task.created_at
    )
    
    # Index های جدول Notification
    notification_user_index = Index('idx_notification_user', Notification.user_id)
    notification_role_index = Index('idx_notification_role', Notification.role_id)
    notification_read_index = Index('idx_notification_read', Notification.is_read)
    notification_created_index = Index('idx_notification_created', Notification.created_at)
    
    # Index های جدول Coupon
    coupon_code_index = Index('idx_coupon_code', Coupon.code)
    coupon_active_index = Index('idx_coupon_active', Coupon.is_active)
    coupon_type_index = Index('idx_coupon_type', Coupon.discount_type)
    coupon_start_date_index = Index('idx_coupon_start_date', Coupon.start_date)
    coupon_end_date_index = Index('idx_coupon_end_date', Coupon.end_date)
    
    # Index ترکیبی برای کوپن‌های فعال
    coupon_active_search_index = Index(
        'idx_coupon_active_search',
        Coupon.is_active,
        Coupon.start_date,
        Coupon.end_date
    )
    
    # Index های جدول FinancialTransaction
    transaction_type_index = Index('idx_transaction_type', FinancialTransaction.transaction_type)
    transaction_order_index = Index('idx_transaction_order', FinancialTransaction.order_id)
    transaction_customer_index = Index('idx_transaction_customer', FinancialTransaction.customer_id)
    transaction_created_index = Index('idx_transaction_created', FinancialTransaction.created_at)
    
    # Index ترکیبی برای گزارش‌های مالی
    transaction_report_index = Index(
        'idx_transaction_report',
        FinancialTransaction.transaction_type,
        FinancialTransaction.created_at
    )


# توابع کمکی برای ایجاد index ها
def create_database_indexes():
    """
    ایجاد تمام index های تعریف شده در دیتابیس
    """
    from app import db
    
    indexes = [
        # Product indexes
        DatabaseIndexes.product_name_index,
        DatabaseIndexes.product_price_index,
        DatabaseIndexes.product_stock_index,
        DatabaseIndexes.product_available_index,
        DatabaseIndexes.product_sales_index,
        DatabaseIndexes.product_revenue_index,
        DatabaseIndexes.product_search_index,
        
        # Category indexes
        DatabaseIndexes.category_name_index,
        DatabaseIndexes.category_parent_index,
        
        # Order indexes
        DatabaseIndexes.order_customer_index,
        DatabaseIndexes.order_date_index,
        DatabaseIndexes.order_status_index,
        DatabaseIndexes.order_payment_status_index,
        DatabaseIndexes.order_coupon_index,
        DatabaseIndexes.order_search_index,
        
        # OrderItem indexes
        DatabaseIndexes.orderitem_order_index,
        DatabaseIndexes.orderitem_product_index,
        
        # Customer indexes
        DatabaseIndexes.customer_phone_index,
        DatabaseIndexes.customer_telegram_index,
        DatabaseIndexes.customer_device_index,
        DatabaseIndexes.customer_level_index,
        DatabaseIndexes.customer_registration_index,
        DatabaseIndexes.customer_last_order_index,
        DatabaseIndexes.customer_search_index,
        
        # User indexes
        DatabaseIndexes.user_username_index,
        DatabaseIndexes.user_failed_login_index,
        DatabaseIndexes.user_locked_index,
        
        # SupportTicket indexes
        DatabaseIndexes.ticket_customer_index,
        DatabaseIndexes.ticket_status_index,
        DatabaseIndexes.ticket_priority_index,
        DatabaseIndexes.ticket_category_index,
        DatabaseIndexes.ticket_created_index,
        DatabaseIndexes.ticket_search_index,
        
        # TicketMessage indexes
        DatabaseIndexes.ticketmessage_ticket_index,
        DatabaseIndexes.ticketmessage_sender_index,
        DatabaseIndexes.ticketmessage_created_index,
        
        # BroadcastMessage indexes
        DatabaseIndexes.broadcast_status_index,
        DatabaseIndexes.broadcast_type_index,
        DatabaseIndexes.broadcast_target_index,
        DatabaseIndexes.broadcast_created_index,
        DatabaseIndexes.broadcast_scheduled_index,
        
        # PreOrder indexes
        DatabaseIndexes.preorder_customer_index,
        DatabaseIndexes.preorder_status_index,
        DatabaseIndexes.preorder_created_index,
        DatabaseIndexes.preorder_user_index,
        DatabaseIndexes.preorder_search_index,
        
        # InStoreOrder indexes
        DatabaseIndexes.instoreorder_customer_index,
        DatabaseIndexes.instoreorder_status_index,
        DatabaseIndexes.instoreorder_created_index,
        DatabaseIndexes.instoreorder_user_index,
        
        # Task indexes
        DatabaseIndexes.task_status_index,
        DatabaseIndexes.task_role_index,
        DatabaseIndexes.task_assigned_index,
        DatabaseIndexes.task_creator_index,
        DatabaseIndexes.task_created_index,
        DatabaseIndexes.task_search_index,
        
        # Notification indexes
        DatabaseIndexes.notification_user_index,
        DatabaseIndexes.notification_role_index,
        DatabaseIndexes.notification_read_index,
        DatabaseIndexes.notification_created_index,
        
        # Coupon indexes
        DatabaseIndexes.coupon_code_index,
        DatabaseIndexes.coupon_active_index,
        DatabaseIndexes.coupon_type_index,
        DatabaseIndexes.coupon_start_date_index,
        DatabaseIndexes.coupon_end_date_index,
        DatabaseIndexes.coupon_active_search_index,
        
        # FinancialTransaction indexes
        DatabaseIndexes.transaction_type_index,
        DatabaseIndexes.transaction_order_index,
        DatabaseIndexes.transaction_customer_index,
        DatabaseIndexes.transaction_created_index,
        DatabaseIndexes.transaction_report_index,
    ]
    
    for index in indexes:
        try:
            index.create(db.engine)
            print(f"Index {index.name} created successfully")
        except Exception as e:
            print(f"Error creating index {index.name}: {e}")


def drop_database_indexes():
    """
    حذف تمام index های تعریف شده از دیتابیس
    """
    from app import db
    
    indexes = [
        # Product indexes
        DatabaseIndexes.product_name_index,
        DatabaseIndexes.product_price_index,
        DatabaseIndexes.product_stock_index,
        DatabaseIndexes.product_available_index,
        DatabaseIndexes.product_sales_index,
        DatabaseIndexes.product_revenue_index,
        DatabaseIndexes.product_search_index,
        
        # Category indexes
        DatabaseIndexes.category_name_index,
        DatabaseIndexes.category_parent_index,
        
        # Order indexes
        DatabaseIndexes.order_customer_index,
        DatabaseIndexes.order_date_index,
        DatabaseIndexes.order_status_index,
        DatabaseIndexes.order_payment_status_index,
        DatabaseIndexes.order_coupon_index,
        DatabaseIndexes.order_search_index,
        
        # OrderItem indexes
        DatabaseIndexes.orderitem_order_index,
        DatabaseIndexes.orderitem_product_index,
        
        # Customer indexes
        DatabaseIndexes.customer_phone_index,
        DatabaseIndexes.customer_telegram_index,
        DatabaseIndexes.customer_device_index,
        DatabaseIndexes.customer_level_index,
        DatabaseIndexes.customer_registration_index,
        DatabaseIndexes.customer_last_order_index,
        DatabaseIndexes.customer_search_index,
        
        # User indexes
        DatabaseIndexes.user_username_index,
        DatabaseIndexes.user_failed_login_index,
        DatabaseIndexes.user_locked_index,
        
        # SupportTicket indexes
        DatabaseIndexes.ticket_customer_index,
        DatabaseIndexes.ticket_status_index,
        DatabaseIndexes.ticket_priority_index,
        DatabaseIndexes.ticket_category_index,
        DatabaseIndexes.ticket_created_index,
        DatabaseIndexes.ticket_search_index,
        
        # TicketMessage indexes
        DatabaseIndexes.ticketmessage_ticket_index,
        DatabaseIndexes.ticketmessage_sender_index,
        DatabaseIndexes.ticketmessage_created_index,
        
        # BroadcastMessage indexes
        DatabaseIndexes.broadcast_status_index,
        DatabaseIndexes.broadcast_type_index,
        DatabaseIndexes.broadcast_target_index,
        DatabaseIndexes.broadcast_created_index,
        DatabaseIndexes.broadcast_scheduled_index,
        
        # PreOrder indexes
        DatabaseIndexes.preorder_customer_index,
        DatabaseIndexes.preorder_status_index,
        DatabaseIndexes.preorder_created_index,
        DatabaseIndexes.preorder_user_index,
        DatabaseIndexes.preorder_search_index,
        
        # InStoreOrder indexes
        DatabaseIndexes.instoreorder_customer_index,
        DatabaseIndexes.instoreorder_status_index,
        DatabaseIndexes.instoreorder_created_index,
        DatabaseIndexes.instoreorder_user_index,
        
        # Task indexes
        DatabaseIndexes.task_status_index,
        DatabaseIndexes.task_role_index,
        DatabaseIndexes.task_assigned_index,
        DatabaseIndexes.task_creator_index,
        DatabaseIndexes.task_created_index,
        DatabaseIndexes.task_search_index,
        
        # Notification indexes
        DatabaseIndexes.notification_user_index,
        DatabaseIndexes.notification_role_index,
        DatabaseIndexes.notification_read_index,
        DatabaseIndexes.notification_created_index,
        
        # Coupon indexes
        DatabaseIndexes.coupon_code_index,
        DatabaseIndexes.coupon_active_index,
        DatabaseIndexes.coupon_type_index,
        DatabaseIndexes.coupon_start_date_index,
        DatabaseIndexes.coupon_end_date_index,
        DatabaseIndexes.coupon_active_search_index,
        
        # FinancialTransaction indexes
        DatabaseIndexes.transaction_type_index,
        DatabaseIndexes.transaction_order_index,
        DatabaseIndexes.transaction_customer_index,
        DatabaseIndexes.transaction_created_index,
        DatabaseIndexes.transaction_report_index,
    ]
    
    for index in indexes:
        try:
            index.drop(db.engine)
            print(f"Index {index.name} dropped successfully")
        except Exception as e:
            print(f"Error dropping index {index.name}: {e}") 