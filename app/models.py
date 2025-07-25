# ---------------------------------------------
# فایل: models.py
# توضیح: این فایل شامل مدل‌های دیتابیس پروژه نیکایدک است.
# هر مدل نمایانگر یک جدول در دیتابیس می‌باشد.
# ---------------------------------------------

from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from sqlalchemy import UniqueConstraint, func
from decimal import Decimal
import pytz
import logging
from sqlalchemy import Column, Integer, String, DateTime


def tehran_now():
    """تابع برای دریافت زمان فعلی تهران"""
    tehran_tz = pytz.timezone('Asia/Tehran')
    return datetime.datetime.now(tehran_tz)


class PaginationMixin:
    """
    Mixin برای اضافه کردن قابلیت pagination به مدل‌ها
    """
    
    @classmethod
    def paginate(cls, page=1, per_page=20, **filters):
        """
        صفحه‌بندی نتایج با فیلترهای اختیاری
        
        Args:
            page (int): شماره صفحه (شروع از 1)
            per_page (int): تعداد آیتم در هر صفحه
            **filters: فیلترهای اضافی برای کوئری
            
        Returns:
            tuple: (items, pagination_info)
        """
        query = cls.query
        
        # اعمال فیلترها
        for key, value in filters.items():
            if value is not None:
                if hasattr(cls, key):
                    if isinstance(value, str) and '%' in value:
                        # جستجوی fuzzy
                        query = query.filter(getattr(cls, key).like(value))
                    else:
                        # جستجوی دقیق
                        query = query.filter(getattr(cls, key) == value)
        
        # مرتب‌سازی (پیش‌فرض بر اساس id نزولی)
        query = query.order_by(cls.id.desc())
        
        # صفحه‌بندی
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
            max_per_page=100
        )
        
        return pagination.items, {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_num': pagination.prev_num,
            'next_num': pagination.next_num
        }


# --- جداول واسط ---


user_roles_table = db.Table(
    'user_roles',
    db.Column('user_id',
              db.Integer,
              db.ForeignKey('user.id'),
              primary_key=True),
    db.Column('role_id',
              db.Integer,
              db.ForeignKey('role.id'),
              primary_key=True))

role_permissions_table = db.Table(
    'role_permissions',
    db.Column('role_id',
              db.Integer,
              db.ForeignKey('role.id'),
              primary_key=True),
    db.Column('permission_id',
              db.Integer,
              db.ForeignKey('permission.id'),
              primary_key=True))

# --- مدل‌های اصلی ---


class User(UserMixin, db.Model):
    """
    مدل کاربر سیستم.
    این مدل اطلاعات کاربران و نقش‌های آن‌ها را نگهداری می‌کند.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64),
                         index=True,
                         unique=True,
                         nullable=False)
    password_hash = db.Column(db.String(256))
    name = db.Column(db.String(100))
    roles = db.relationship('Role',
                            secondary=user_roles_table,
                            backref=db.backref('users', lazy='dynamic'))

    failed_login_attempts = db.Column(db.Integer,
                                      default=0,
                                      nullable=False,
                                      comment='تعداد تلاش ناموفق ورود')
    temp_locked_until = db.Column(db.DateTime,
                                  nullable=True,
                                  comment='زمان پایان قفل موقت')
    permanently_locked = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment='آیا حساب به طور دائمی قفل شده است؟')

    def set_password(self, password):
        """
        تنظیم رمز عبور (هش می‌شود)
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        بررسی صحت رمز عبور وارد شده
        """
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        """
        بررسی داشتن نقش خاص
        """
        return any(role.name == role_name for role in self.roles)

    def can(self, permission_name):
        """
        بررسی داشتن مجوز خاص
        """
        for role in self.roles:
            for perm in role.permissions:
                if perm.name == permission_name:
                    return True
        return False

    def __repr__(self):
        return f'<User {self.username}>'


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.relationship('Permission',
                                  secondary=role_permissions_table,
                                  backref=db.backref('roles', lazy='dynamic'))

    def __repr__(self):
        return f'<Role {self.name}>'


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Permission {self.name}>'


class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer,
                         db.ForeignKey('person.id'),
                         nullable=False)
    order_date = db.Column(db.DateTime,
                           nullable=False,
                           default=datetime.datetime.utcnow)
    status = db.Column(db.String(30), nullable=False, default='در حال بررسی')
    total_price = db.Column(db.Float, nullable=False)

    # اطلاعات مالی اضافی
    discount_amount = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    shipping_cost = db.Column(db.Float, default=0.0)
    final_price = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default='نقدی')
    payment_status = db.Column(db.String(30), default='پرداخت نشده')

    # اطلاعات فاکتور
    invoice_number = db.Column(db.String(50), unique=True, nullable=True)
    invoice_date = db.Column(db.DateTime, nullable=True)

    person = db.relationship('Person', backref='orders')

    items = db.relationship('OrderItem',
                            backref='order',
                            lazy='dynamic',
                            cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Order {self.id}>'

    def generate_invoice_number(self):
        """تولید شماره فاکتور"""
        if not self.invoice_number:
            year = self.order_date.year
            month = self.order_date.month
            count = Order.query.filter(
                func.extract('year', Order.order_date) == year,
                func.extract('month', Order.order_date) == month).count()
            self.invoice_number = f"INV-{year}{month:02d}-{count+1:04d}"

    def calculate_final_price(self):
        """محاسبه قیمت نهایی"""
        self.final_price = self.total_price - self.discount_amount + self.tax_amount + self.shipping_cost

    
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer,
                           db.ForeignKey('inventory_product.id'),
                           nullable=False)
    product = db.relationship('InventoryProduct')

    def __repr__(self):
        return f'<OrderItem {self.id}>'


# --- مدل‌های جدید برای سیستم مالی و پشتیبانی ---

class FinancialTransaction(db.Model):
    """مدل برای تراکنش‌های مالی"""
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(50), nullable=False)  # فروش، بازگشت، تخفیف، commission_payment
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=True)
    mechanic_id = db.Column(db.BigInteger, db.ForeignKey('person.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # فیلدهای جدید برای پرداخت کمیسیون
    payment_method = db.Column(db.String(50), nullable=True)  # bank_transfer, cash, check, other
    tracking_number = db.Column(db.String(100), nullable=True)  # شماره پیگیری
    payment_date = db.Column(db.DateTime, nullable=True)  # تاریخ واریز
    card_number = db.Column(db.String(20), nullable=True)  # شماره کارت مبدا
    check_number = db.Column(db.String(50), nullable=True)  # شماره چک
    receipt_image = db.Column(db.String(255), nullable=True)  # مسیر فایل فیش واریز
    notes = db.Column(db.Text, nullable=True)  # توضیحات
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # کاربر ثبت‌کننده

    order = db.relationship('Order', backref='transactions')
    customer = db.relationship('Person', foreign_keys=[customer_id], backref='transactions_as_customer')
    mechanic = db.relationship('Person', foreign_keys=[mechanic_id], backref='transactions_as_mechanic')
    created_by_user = db.relationship('User', backref='created_transactions')

    def __repr__(self):
        return f'<FinancialTransaction {self.id}>'


class BroadcastMessage(db.Model):
    """مدل برای پیام‌های همگانی"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(16), default='text', nullable=False, server_default='text', comment='نوع پیام فقط متن')
    target_type = db.Column(db.String(20), default='all')  # all, specific, vip, new_customers
    target_persons = db.Column(db.Text, nullable=True)  # JSON array of person IDs (قبلاً customer IDs)
    status = db.Column(db.String(16), default='draft', nullable=False, server_default='draft', comment='وضعیت: draft یا sent')
    sent_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # آمار ارسال
    total_sent = db.Column(db.Integer, default=0)
    total_delivered = db.Column(db.Integer, default=0)
    total_read = db.Column(db.Integer, default=0)

    created_by_user = db.relationship('User', backref='broadcast_messages')

    def __repr__(self):
        return f'<BroadcastMessage {self.id}>'


class CustomerSegment(db.Model):
    """مدل برای تقسیم‌بندی مشتریان (در ساختار جدید: تقسیم‌بندی اشخاص)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    criteria = db.Column(db.Text, nullable=False)  # JSON criteria (باید بر اساس person_id و ویژگی‌های Person باشد)
    person_count = db.Column(db.Integer, default=0)  # تعداد اشخاص در این سگمنت (قبلاً customer_count)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<CustomerSegment {self.name}>'


class License(db.Model):
    """مدل برای مدیریت لایسنس سیستم"""
    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(255), unique=True, nullable=False)
    license_hash = db.Column(db.String(512), nullable=False)  # هش شده
    is_active = db.Column(db.Boolean, default=False)
    activation_date = db.Column(db.DateTime, nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # اطلاعات اضافی
    customer_name = db.Column(db.String(200), nullable=True)
    customer_email = db.Column(db.String(200), nullable=True)
    max_users = db.Column(db.Integer, default=5)
    features = db.Column(db.Text, nullable=True)  # JSON features

    def __repr__(self):
        return f'<License {self.license_key[:8]}...>'

    def is_valid(self):
        """بررسی اعتبار لایسنس"""
        if not self.is_active:
            return False
        if self.expiry_date and datetime.datetime.utcnow() > self.expiry_date:
            return False
        return True


class PreOrder(db.Model):
    """
    مدل پیش‌سفارش - برای ثبت سفارش‌های حضوری اشخاص (مشتری یا مکانیک)
    به جای ذخیره نام و شماره تلفن، به رکورد Person ارجاع داده می‌شود.
    """
    __tablename__ = 'pre_orders'

    id = db.Column(db.Integer, primary_key=True)
    # ارجاع به شخص
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False, comment='شناسه شخص')
    person = db.relationship('Person', backref='pre_orders')
    # فیلدهای آدرس (اختیاری - فقط برای ارسال پستی)
    shipping_required = db.Column(db.Boolean,
                                  default=False,
                                  comment='نیاز به ارسال پستی')
    province = db.Column(db.String(50), comment='استان')
    city = db.Column(db.String(50), comment='شهرستان')
    address = db.Column(db.Text, comment='آدرس کامل')
    postal_code = db.Column(db.String(10), comment='کد پستی')
    # وضعیت پیش‌سفارش
    status = db.Column(db.String(20),
                       default='درحال پیگیری',
                       comment='وضعیت پیش‌سفارش')
    # اطلاعات محصولات
    products_info = db.Column(db.Text,
                              nullable=False,
                              comment='اطلاعات محصولات (JSON)')
    total_price = db.Column(db.Numeric(10, 2), comment='قیمت کل')
    # تاریخ‌ها
    created_at = db.Column(db.DateTime,
                           default=datetime.datetime.utcnow,
                           comment='تاریخ ایجاد')
    updated_at = db.Column(db.DateTime,
                           default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow,
                           comment='تاریخ بروزرسانی')
    purchased_at = db.Column(db.DateTime, comment='تاریخ خریداری شدن')
    delivered_at = db.Column(db.DateTime, comment='تاریخ تحویل')
    # ارتباط با سفارش (در صورت تبدیل)
    order_id = db.Column(db.Integer,
                         db.ForeignKey('order.id'),
                         comment='شناسه سفارش مرتبط')
    order = db.relationship('Order', backref='pre_orders')
    # کاربر ایجاد کننده
    created_by = db.Column(db.Integer,
                           db.ForeignKey('user.id'),
                           nullable=False,
                           comment='کاربر ایجاد کننده')
    user = db.relationship('User', backref='created_pre_orders')
    # یادداشت‌ها
    notes = db.Column(db.Text, comment='یادداشت‌های اضافی')
    def __repr__(self):
        return f'<PreOrder {self.id}: {self.person_id}>'
    @property
    def status_color(self):
        """رنگ وضعیت پیش‌سفارش"""
        colors = {
            'درحال پیگیری': 'warning',  # زرد
            'خریداری شده': 'info',  # بنفش
            'تحویل داده شده': 'success',  # سبز
            'لغو شده': 'danger'  # قرمز
        }
        return colors.get(self.status, 'secondary')
    @property
    def is_overdue(self):
        """بررسی اینکه آیا پیش‌سفارش بیشتر از 3 روز قدیمی است"""
        if self.status == 'تحویل داده شده' or self.status == 'لغو شده':
            return False
        return (datetime.datetime.utcnow() - self.created_at).days > 3
    def to_dict(self):
        """تبدیل به دیکشنری برای API"""
        return {
            'id': self.id,
            'person_id': self.person_id,
            'shipping_required': self.shipping_required,
            'province': self.province,
            'city': self.city,
            'address': self.address,
            'postal_code': self.postal_code,
            'status': self.status,
            'products_info': self.products_info,
            'total_price': float(self.total_price) if self.total_price else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'purchased_at': self.purchased_at.isoformat() if self.purchased_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'notes': self.notes,
            'is_overdue': self.is_overdue,
            'status_color': self.status_color
        }


class InStoreOrder(db.Model):
    """
    مدل سفارش حضوری
    این مدل برای ثبت سفارشات حضوری اشخاص (مشتری یا مکانیک) استفاده می‌شود و به رکورد Person ارجاع می‌دهد.
    """
    id = db.Column(db.Integer, primary_key=True)
    # ارجاع به شخص
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False, comment='شناسه شخص')
    person = db.relationship('Person', backref='instore_orders')
    products_info = db.Column(
        db.Text,
        nullable=False)  # JSON string: [{product_id, name, qty, price}]
    total_price = db.Column(db.Float, nullable=False, default=0)
    deposit_amount = db.Column(db.Float, nullable=True,
                               comment='مبلغ بیعانه')  # مبلغ بیعانه
    product_type = db.Column(db.String(20), nullable=True,
                             comment='نوع کالا')  # وارداتی/شرکتی/ایرانی
    shipping_required = db.Column(db.Boolean,
                                  default=False,
                                  comment='ارسال پستی')
    store_stock = db.Column(db.Boolean, default=False, comment='انبار مغازه')
    notes = db.Column(db.Text, nullable=True, comment='یادداشت')
    province = db.Column(db.String(50), nullable=True, comment='استان')
    city = db.Column(db.String(50), nullable=True, comment='شهرستان')
    address = db.Column(db.Text, nullable=True, comment='آدرس کامل')
    postal_code = db.Column(db.String(10), nullable=True, comment='کد پستی')
    status = db.Column(db.String(30),
                       nullable=False,
                       default='جدید',
                       comment='وضعیت سفارش')
    created_at = db.Column(db.DateTime,
                           default=tehran_now,
                           comment='تاریخ ایجاد')
    updated_at = db.Column(db.DateTime,
                           default=tehran_now,
                           onupdate=tehran_now,
                           comment='تاریخ بروزرسانی')
    # کاربر ثبت کننده سفارش
    created_by = db.Column(db.Integer,
                           db.ForeignKey('user.id'),
                           nullable=True,
                           comment='کاربر ثبت کننده')
    created_by_user = db.relationship('User', backref='created_instore_orders')
    
    # اطلاعات فاکتور
    invoice_number = db.Column(db.String(50), unique=True, nullable=True, comment='شماره فاکتور')
    invoice_date = db.Column(db.DateTime, nullable=True, comment='تاریخ صدور فاکتور')
    
    def __repr__(self):
        return f'<InStoreOrder {self.id}: {self.person_id}>'
    
    def generate_invoice_number(self):
        """تولید شماره فاکتور"""
        if not self.invoice_number:
            year = self.created_at.year
            month = self.created_at.month
            count = InStoreOrder.query.filter(
                func.extract('year', InStoreOrder.created_at) == year,
                func.extract('month', InStoreOrder.created_at) == month).count()
            self.invoice_number = f"IS-{year}{month:02d}-{count+1:04d}"
            self.invoice_date = self.created_at


# --- مدل وظیفه (Task) و اعلان (Notification) ---


class Task(db.Model):
    """
    مدل وظیفه (Task) برای کارتابل
    هر وظیفه می‌تواند به یک نقش یا کاربر خاص اختصاص یابد.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, comment='عنوان وظیفه')
    description = db.Column(db.Text, nullable=True, comment='توضیحات')
    status = db.Column(
        db.String(30), default='جدید',
        comment='وضعیت وظیفه')  # جدید، در حال انجام، انجام شده، لغو شده
    due_date = db.Column(db.String(20),
                         nullable=True,
                         comment='موعد انجام (تاریخ شمسی)')
    created_at = db.Column(db.DateTime,
                           default=datetime.datetime.utcnow,
                           comment='تاریخ ایجاد')
    updated_at = db.Column(db.DateTime,
                           default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)

    # ارتباط با نقش هدف (اختیاری)
    role_id = db.Column(db.Integer,
                        db.ForeignKey('role.id'),
                        nullable=True,
                        comment='نقش هدف')
    role = db.relationship('Role', backref='tasks')

    # ارتباط با کاربر هدف (اختیاری)
    assigned_user_id = db.Column(db.Integer,
                                 db.ForeignKey('user.id'),
                                 nullable=True,
                                 comment='کاربر هدف')
    assigned_user = db.relationship('User',
                                    foreign_keys=[assigned_user_id],
                                    backref='assigned_tasks')

    created_by = db.Column(db.Integer,
                           db.ForeignKey('user.id'),
                           nullable=False,
                           comment='ایجادکننده')
    creator = db.relationship('User',
                              foreign_keys=[created_by],
                              backref='created_tasks')

    def __repr__(self):
        return f'<Task {self.title}>'


class Notification(db.Model):
    """
    مدل اعلان درون‌برنامه‌ای
    هر اعلان می‌تواند به یک کاربر یا نقش اختصاص یابد و به یک وظیفه مرتبط باشد.
    """
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False, comment='متن اعلان')
    is_read = db.Column(db.Boolean, default=False, comment='خوانده شده')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # ارتباط با کاربر هدف (اختیاری)
    user_id = db.Column(db.Integer,
                        db.ForeignKey('user.id'),
                        nullable=True,
                        comment='کاربر هدف')
    user = db.relationship('User', backref='notifications')

    # ارتباط با نقش هدف (اختیاری)
    role_id = db.Column(db.Integer,
                        db.ForeignKey('role.id'),
                        nullable=True,
                        comment='نقش هدف')
    role = db.relationship('Role', backref='notifications')

    # ارتباط با وظیفه (اختیاری) - حذف شده چون اعلان‌ها مستقل هستند
    # task_id = db.Column(db.Integer,
    #                     db.ForeignKey('task.id'),
    #                     nullable=True,
    #                     comment='وظیفه مرتبط')
    # task = db.relationship('Task', backref='notifications')

    notification_type = db.Column(db.String(50), nullable=True, comment='نوع اعلان')

    def __repr__(self):
        return f'<Notification {self.message[:20]}>'


class SessionLog(db.Model):
    """
    ثبت نشست‌های کاربران برای امنیت و مدیریت نشست‌ها
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    device_id = db.Column(db.String(100), nullable=True)
    login_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    logout_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_activity = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='session_logs')

    def __repr__(self):
        return f'<SessionLog {self.user_id} {self.ip_address} {self.login_time}>'


class AuditLog(db.Model):
    """
    ثبت لاگ فرآیندهای مهم سیستم برای امنیت و پیگیری
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship('User', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.user_id} {self.action} {self.created_at}>'


class BackupFile(db.Model):
    """
    ثبت اطلاعات بک‌آپ‌های دیتابیس
    """
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_downloaded = db.Column(db.Boolean, default=False)
    downloaded_by = db.Column(db.Integer,
                              db.ForeignKey('user.id'),
                              nullable=True)
    downloaded_at = db.Column(db.DateTime, nullable=True)

    downloader = db.relationship('User',
                                 backref='downloaded_backups',
                                 foreign_keys=[downloaded_by])

    def __repr__(self):
        return f'<BackupFile {self.filename} {self.created_at}>'


# ==================== مدل‌های جدید برای ربات تلگرام ====================


class InventoryAlert(db.Model):
    """
    مدل اعلان‌های موجودی
    """
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('inventory_product.id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    
    # نوع اعلان (موجودی کم، موجودی تمام شد، موجودی اضافه شد)
    alert_type = db.Column(db.String(20), nullable=False)
    # آستانه موجودی
    threshold_quantity = db.Column(db.Integer, nullable=True)
    # وضعیت اعلان
    status = db.Column(db.String(20), default='فعال')  # فعال، غیرفعال، ارسال شده
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    
    # روابط
    product = db.relationship('InventoryProduct', backref='inventory_alerts')
    person = db.relationship('Person', backref='inventory_alerts')
    
    def __repr__(self):
        return f'<InventoryAlert {self.id} - Product: {self.product_id}, Person: {self.person_id}, Type: {self.alert_type}>'


class PushNotification(db.Model):
    """
    مدل اعلان‌های فوری
    """
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    telegram_id = db.Column(db.BigInteger, nullable=True)
    
    # محتوای اعلان
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # order_status, inventory, promotion, etc.
    
    # وضعیت ارسال
    status = db.Column(db.String(20), default='در انتظار')  # در انتظار، ارسال شده، ناموفق
    sent_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # اطلاعات اضافی (JSON)
    extra_data = db.Column(db.Text, nullable=True)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    
    # روابط
    person = db.relationship('Person', backref='push_notifications')
    
    def __repr__(self):
        return f'<PushNotification {self.id} - Person: {self.person_id}, Type: {self.notification_type}>'


class InventoryProduct(PaginationMixin, db.Model):
    """
    مدل محصولات انبار
    این مدل جایگزین مدل Product قدیمی می‌شود و شامل مدیریت موجودی و پارت‌ها است.
    """
    __table_args__ = (db.UniqueConstraint('name', 'quality', name='_name_quality_uc'),)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True, comment='نام محصول')
    quality = db.Column(db.String(20), nullable=False, default='ایرانی', comment='کیفیت: ایرانی، شرکتی، وارداتی')
    
    # شماره محصول (فرمت: P-XXXX)
    product_number = db.Column(db.String(10), unique=True, nullable=False, index=True, comment='شماره محصول')
    
    # آمار کلی
    total_quantity = db.Column(db.Integer, default=0, comment='موجودی کل')
    reserved_quantity = db.Column(db.Integer, default=0, comment='موجودی رزرو شده')
    available_quantity = db.Column(db.Integer, default=0, comment='موجودی قابل فروش')
    sold_quantity = db.Column(db.Integer, default=0, comment='تعداد فروخته شده')
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=tehran_now, comment='تاریخ ثبت اولیه')
    updated_at = db.Column(db.DateTime, default=tehran_now, onupdate=tehran_now, comment='تاریخ بروزرسانی')
    
    # روابط
    batches = db.relationship('InventoryBatch', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<InventoryProduct {self.product_number} - {self.name} ({self.quality})>'
    
    def generate_product_number(self):
        """تولید شماره محصول جدید"""
        if not self.product_number:
            # پیدا کردن آخرین شماره محصول
            last_product = InventoryProduct.query.order_by(InventoryProduct.id.desc()).first()
            if last_product and last_product.product_number:
                try:
                    last_number = int(last_product.product_number.split('-')[1])
                    new_number = last_number + 1
                except (IndexError, ValueError):
                    new_number = 1
            else:
                new_number = 1
            
            self.product_number = f"P-{new_number:04d}"
        return self.product_number
    
    def update_quantities(self):
        """بروزرسانی آمار موجودی بر اساس پارت‌ها"""
        # محاسبه موجودی کل از تمام پارت‌ها (حتی آنهایی که موجودی صفر دارند)
        total = sum(batch.remaining_quantity for batch in self.batches)
        self.total_quantity = total
        self.available_quantity = total - self.reserved_quantity
        # اطمینان از اینکه موجودی قابل فروش منفی نباشد
        if self.available_quantity < 0:
            self.available_quantity = 0
        
        # محاسبه تعداد فروخته شده از تاریخچه
        from sqlalchemy import func
        sold_history = db.session.query(func.sum(InventoryHistory.quantity)).filter(
            InventoryHistory.product_id == self.id,
            InventoryHistory.operation_type == 'remove'
        ).scalar() or 0
        self.sold_quantity = sold_history
        
        db.session.commit()
        # اعلان موجودی کم
        if self.available_quantity < 2:
            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role:
                admins = User.query.join(User.roles).filter(Role.id == admin_role.id).all()
                for admin in admins:
                    if admin.can('manage_products'):
                        notif = Notification(
                            message=f"موجودی محصول '{self.name}' به کمتر از ۲ عدد رسید.",
                            user_id=admin.id
                        )
                        db.session.add(notif)
                db.session.commit()
    
    def can_reserve(self, quantity):
        """بررسی امکان رزرو موجودی"""
        return self.available_quantity >= quantity
    
    def reserve_quantity(self, quantity):
        """رزرو موجودی"""
        if self.can_reserve(quantity):
            self.reserved_quantity += quantity
            self.available_quantity -= quantity
            db.session.commit()
            return True
        return False
    
    def release_reservation(self, quantity):
        """آزادسازی رزرو"""
        if self.reserved_quantity >= quantity:
            self.reserved_quantity -= quantity
            self.available_quantity += quantity
            # حذف db.session.commit() از اینجا
            return True
        return False


class InventoryBatch(db.Model):
    """
    مدل پارت‌های خرید انبار
    هر محصول می‌تواند چندین پارت خرید داشته باشد.
    """
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('inventory_product.id'), nullable=False)
    
    # شماره پارت (فرمت: P-XXXX-B)
    batch_number = db.Column(db.String(15), unique=True, nullable=False, index=True, comment='شماره پارت')
    
    # اطلاعات پارت
    initial_quantity = db.Column(db.Integer, nullable=False, comment='موجودی اولیه پارت')
    remaining_quantity = db.Column(db.Integer, nullable=False, comment='موجودی باقی‌مانده')
    reserved_quantity = db.Column(db.Integer, default=0, comment='موجودی رزرو شده')
    sold_quantity = db.Column(db.Integer, default=0, comment='تعداد فروخته شده')
    purchase_price = db.Column(db.Float, nullable=True, comment='قیمت خرید (اختیاری)')
    
    # اطلاعات ثبت‌کننده
    created_by = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False, comment='شخص ثبت‌کننده')
    created_by_person = db.relationship('Person', backref='created_batches')
    created_at = db.Column(db.DateTime, default=tehran_now, comment='تاریخ ورود به انبار')
    
    def __repr__(self):
        return f'<InventoryBatch {self.batch_number} - {self.product.name} - {self.initial_quantity} units>'
    
    def generate_batch_number(self):
        """تولید شماره پارت جدید"""
        if not self.batch_number:
            # پیدا کردن آخرین پارت برای این محصول
            last_batch = InventoryBatch.query.filter_by(product_id=self.product_id).order_by(InventoryBatch.id.desc()).first()
            if last_batch and last_batch.batch_number:
                try:
                    # استخراج شماره پارت از فرمت P-XXXX-B
                    parts = last_batch.batch_number.split('-')
                    if len(parts) == 3 and parts[2].isdigit():
                        batch_num = int(parts[2]) + 1
                    else:
                        batch_num = 1
                except (IndexError, ValueError):
                    batch_num = 1
            else:
                batch_num = 1
            
            # استفاده از شماره محصول
            product_number = self.product.product_number if self.product else f"P-{self.product_id:04d}"
            self.batch_number = f"{product_number}-{batch_num}"
        return self.batch_number
    
    def consume_quantity(self, quantity):
        """مصرف موجودی از پارت (FIFO)"""
        if self.remaining_quantity >= quantity:
            self.remaining_quantity -= quantity
            db.session.commit()
            return True
        return False


class BotOrder(db.Model):
    """
    مدل سفارشات ربات تلگرام
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # اطلاعات مشتری
    customer_phone = db.Column(db.String(20), nullable=False, index=True, comment='شماره تلفن مشتری')
    customer_name = db.Column(db.String(100), nullable=True, comment='نام مشتری')
    customer_address = db.Column(db.Text, nullable=True, comment='آدرس مشتری')
    telegram_id = db.Column(db.BigInteger, nullable=True, comment='آیدی تلگرام')
    
    # اطلاعات مکانیک (اختیاری)
    mechanic_person_id = db.Column(db.BigInteger, db.ForeignKey('person.id'), nullable=True, comment='مکانیک مرتبط')
    # اطلاعات مشتری (اختیاری)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=True, comment='شخص مرتبط')
    
    # اطلاعات سفارش
    order_items = db.Column(db.Text, nullable=False, comment='آیتم‌های سفارش (JSON)')
    total_amount = db.Column(db.Float, nullable=False, comment='مبلغ کل')
    commission_amount = db.Column(db.Float, default=0.0, comment='مبلغ کمیسیون')
    commission_paid = db.Column(db.Boolean, default=False, comment='کمیسیون پرداخت شده')
    
    # وضعیت سفارش
    status = db.Column(db.String(30), default='در انتظار بررسی', comment='وضعیت سفارش')
    # وضعیت‌ها:
    # - در انتظار بررسی
    # - در حال تامین
    # - تایید شده
    # - پرداخت شده
    # - تکمیل شده
    # - لغو شده
    # - در انتظار پرداخت
    # - در انتظار تایید پرداخت
    # - در انتظار تایید کاربر
    # - موجود
    # - عدم موجودی
    
    # اطلاعات پرداخت
    payment_receipt = db.Column(db.String(255), nullable=True, comment='فایل رسید پرداخت')
    payment_confirmed = db.Column(db.Boolean, default=False, comment='پرداخت تایید شده')
    payment_confirmed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, comment='کاربر تاییدکننده پرداخت')
    payment_confirmed_at = db.Column(db.DateTime, nullable=True, comment='تاریخ تایید پرداخت')
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=tehran_now, comment='تاریخ ثبت سفارش')
    updated_at = db.Column(db.DateTime, default=tehran_now, onupdate=tehran_now, comment='تاریخ بروزرسانی')
    expires_at = db.Column(db.DateTime, nullable=True, comment='تاریخ انقضای رزرو')
    
    # روابط
    payment_confirmed_by_user = db.relationship('User', backref='confirmed_bot_orders')
    items = db.relationship('BotOrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    person = db.relationship('Person', foreign_keys=[person_id], backref='bot_orders_as_customer')
    mechanic_person = db.relationship('Person', foreign_keys=[mechanic_person_id], backref='bot_orders_as_mechanic')
    
    # اضافه کردن فیلد receipt_image
    receipt_image = db.Column(db.String(256), nullable=True, comment='مسیر عکس رسید پرداخت')
    
    # اطلاعات فاکتور
    invoice_number = db.Column(db.String(50), unique=True, nullable=True, comment='شماره فاکتور')
    invoice_date = db.Column(db.DateTime, nullable=True, comment='تاریخ صدور فاکتور')
    
    def __repr__(self):
        return f'<BotOrder {self.id} - {self.customer_phone}>'
    
    def generate_invoice_number(self):
        """تولید شماره فاکتور"""
        if not self.invoice_number:
            year = self.created_at.year
            month = self.created_at.month
            count = BotOrder.query.filter(
                func.extract('year', BotOrder.created_at) == year,
                func.extract('month', BotOrder.created_at) == month).count()
            self.invoice_number = f"BO-{year}{month:02d}-{count+1:04d}"
            self.invoice_date = self.created_at
    
    def calculate_commission(self):
        """محاسبه کمیسیون مکانیک یا مشتری عادی"""
        if self.mechanic_person and self.mechanic_person.person_type == 'mechanic' and self.mechanic_person.mechanic_profile:
            self.commission_amount = self.total_amount * (self.mechanic_person.mechanic_profile.commission_percentage / 100)
        else:
            # برای سفارشات مشتریان عادی، کمیسیون باید صفر باشد
            self.commission_amount = 0.0
        db.session.commit()


class BotOrderItem(db.Model):
    """
    مدل آیتم‌های سفارش ربات
    """
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('bot_order.id'), nullable=False)
    
    # اطلاعات محصول
    product_name = db.Column(db.String(200), nullable=False, comment='نام محصول وارد شده')
    product_id = db.Column(db.Integer, db.ForeignKey('inventory_product.id'), nullable=True, comment='محصول مرتبط در انبار')
    quantity = db.Column(db.Integer, nullable=False, comment='تعداد')
    unit_price = db.Column(db.Float, nullable=False, comment='قیمت واحد')
    total_price = db.Column(db.Float, nullable=False, comment='قیمت کل')
    
    # وضعیت آیتم
    status = db.Column(db.String(30), default='در انتظار بررسی', comment='وضعیت آیتم')
    # وضعیت‌ها:
    # - در انتظار بررسی
    # - موجود
    # - در حال تامین
    # - عدم موجودی
    
    # رزرو موجودی
    reserved_quantity = db.Column(db.Integer, default=0, comment='موجودی رزرو شده')
    
    # عکس محصول (اختیاری)
    photo = db.Column(db.String(255), nullable=True, comment='مسیر عکس محصول')
    
    # روابط
    product = db.relationship('InventoryProduct', backref='bot_order_items')
    
    def __repr__(self):
        return f'<BotOrderItem {self.product_name} - {self.quantity} units>'
    
    def reserve_inventory(self):
        """رزرو موجودی برای این آیتم"""
        import logging
        if self.product:
            logging.info(f"[RESERVE] Try reserve: product={self.product.name}, available={self.product.available_quantity}, requested={self.quantity}")
            if self.product.can_reserve(self.quantity):
                self.product.reserve_quantity(self.quantity)
                self.reserved_quantity = self.quantity
                self.status = 'موجود'
                db.session.commit()
                logging.info(f"[RESERVE] Success: product={self.product.name}, reserved={self.quantity}")
                return True
            else:
                logging.warning(f"[RESERVE] Failed: Not enough stock for product={self.product.name}, available={self.product.available_quantity}, requested={self.quantity}")
        else:
            logging.warning(f"[RESERVE] Failed: No product linked for item_id={self.id}, product_name={self.product_name}")
        return False
    
    def release_reservation(self):
        """آزادسازی رزرو"""
        if self.reserved_quantity > 0:
            self.product.release_reservation(self.reserved_quantity)
            self.reserved_quantity = 0
            # حذف db.session.commit() از اینجا

class PaymentHistory(db.Model):
    """تاریخچه پرداخت‌ها - شامل همه پرداخت‌های اشخاص (مشتریان و مکانیک‌ها)"""
    id = db.Column(db.Integer, primary_key=True)
    
    # نوع پرداخت
    payment_type = db.Column(db.String(50), nullable=False)  # order_payment, commission, refund, etc.
    
    # اطلاعات پرداخت‌کننده
    payer_type = db.Column(db.String(20), nullable=False)  # customer, mechanic
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)  # شخص پرداخت‌کننده (مشتری یا مکانیک)
    
    # مبلغ و اطلاعات مالی
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)  # cash, card, transfer, etc.
    payment_status = db.Column(db.String(30), default='pending')  # pending, completed, failed, refunded
    
    # مرجع پرداخت
    reference_type = db.Column(db.String(50), nullable=True)  # order, bot_order, commission, etc.
    reference_id = db.Column(db.Integer, nullable=True)
    
    # اطلاعات اضافی
    description = db.Column(db.Text, nullable=True)
    receipt_file = db.Column(db.String(255), nullable=True)  # مسیر فایل رسید
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # کاربر تاییدکننده (در صورت نیاز)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    
    # روابط
    person = db.relationship('Person', backref='payment_history')
    confirmed_by_user = db.relationship('User', backref='confirmed_payments')   
    def __repr__(self):
        return f'<PaymentHistory {self.payment_type}: {self.amount}>'

class InventoryHistory(db.Model):
    """تاریخچه مدیریت کالا - شامل ورود، خروج، رزرو و آزادسازی"""
    id = db.Column(db.Integer, primary_key=True)
    
    # محصول و پارت
    product_id = db.Column(db.Integer, db.ForeignKey('inventory_product.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('inventory_batch.id'), nullable=True)
    
    # نوع عملیات
    operation_type = db.Column(db.String(50), nullable=False)  # add, remove, reserve, release, adjust
    
    # مقدار
    quantity = db.Column(db.Integer, nullable=False)
    quantity_before = db.Column(db.Integer, nullable=True)  # موجودی قبل از عملیات
    quantity_after = db.Column(db.Integer, nullable=True)   # موجودی بعد از عملیات
    
    # مرجع عملیات
    reference_type = db.Column(db.String(50), nullable=True)  # order, bot_order, manual, etc.
    reference_id = db.Column(db.Integer, nullable=True)
    
    # اطلاعات اضافی
    description = db.Column(db.Text, nullable=True)
    unit_price = db.Column(db.Float, nullable=True)  # قیمت واحد (در صورت فروش)
    
    # شخص انجام‌دهنده
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=True)
    person = db.relationship('Person', backref='inventory_operations')
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # روابط
    product = db.relationship('InventoryProduct', backref='inventory_history')
    batch = db.relationship('InventoryBatch', backref='inventory_history')
    
    def __repr__(self):
        return f'<InventoryHistory {self.product_id}: {self.operation_type} {self.quantity}>'

class CommissionHistory(db.Model):
    """تاریخچه پرداخت کمیسیون اشخاص (مکانیک‌ها)"""
    id = db.Column(db.Integer, primary_key=True)
    
    # مکانیک
    person_id = db.Column(db.BigInteger, db.ForeignKey('person.id'), nullable=False)
    
    # سفارش مرتبط
    order_id = db.Column(db.Integer, db.ForeignKey('bot_order.id'), nullable=False)
    
    # اطلاعات کمیسیون
    commission_amount = db.Column(db.Float, nullable=False)
    commission_percentage = db.Column(db.Float, nullable=False)
    order_total = db.Column(db.Float, nullable=False)
    
    # وضعیت پرداخت
    payment_status = db.Column(db.String(30), default='pending')  # pending, paid, cancelled
    payment_date = db.Column(db.DateTime, nullable=True)
    
    # اطلاعات پرداخت
    payment_method = db.Column(db.String(50), nullable=True)
    payment_reference = db.Column(db.String(100), nullable=True)  # شماره تراکنش
    
    # کاربر پرداخت‌کننده
    paid_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # روابط
    person = db.relationship('Person', backref='commission_history')
    order = db.relationship('BotOrder', backref='commission_history')
    paid_by_user = db.relationship('User', backref='paid_commissions')   
    def __repr__(self):
        return f'<CommissionHistory {self.person_id}: {self.commission_amount}>'

class BroadcastHistory(db.Model):
    """تاریخچه ارسال پیام‌های انبوه به اشخاص (مشتری یا مکانیک)"""
    id = db.Column(db.Integer, primary_key=True)
    broadcast_id = db.Column(db.Integer, db.ForeignKey('broadcast_message.id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)  # شخص دریافت‌کننده
    sent_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    error_message = db.Column(db.Text, nullable=True)

    broadcast = db.relationship('BroadcastMessage', backref='history')
    person = db.relationship('Person', backref='broadcast_history')

    def __repr__(self):
        return f'<BroadcastHistory {self.person_id} - {self.broadcast_id}>'

class SalesHistory(db.Model):
    """تاریخچه فروش به اشخاص (مشتری یا مکانیک)"""
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)  # شخص خریدار
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)  # سفارش مرتبط
    sale_amount = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    payment_method = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    person = db.relationship('Person', backref='sales_history')
    order = db.relationship('Order', backref='sales_history')

    def __repr__(self):
        return f'<SalesHistory {self.person_id} - {self.order_id}>'

class TaskHistory(db.Model):
    """تاریخچه کارتابل و تسک‌ها"""
    id = db.Column(db.Integer, primary_key=True)
    
    # تسک
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    
    # کاربر
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # نوع عملیات
    action_type = db.Column(db.String(50), nullable=False)  # created, assigned, status_changed, completed, etc.
    
    # اطلاعات عملیات
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # روابط
    task = db.relationship('Task', backref='history')
    user = db.relationship('User', backref='task_history')   
    def __repr__(self):
        return f'<TaskHistory {self.task_id}: {self.action_type}>'


class InStoreOrderBatch(db.Model):
    """
    واسط بین سفارش حضوری و پارت‌های انبار برای مدیریت رزرو، فروش و مرجوعی به صورت دقیق و FIFO
    """
    __tablename__ = 'instore_order_batch'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('instore_order.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('inventory_batch.id'), nullable=False)
    reserved_qty = db.Column(db.Integer, default=0, nullable=False)  # مقدار رزرو شده
    sold_qty = db.Column(db.Integer, default=0, nullable=False)      # مقدار فروخته شده
    returned_qty = db.Column(db.Integer, default=0, nullable=False)  # مقدار مرجوع شده
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    order = db.relationship('InStoreOrder', backref=db.backref('batches', lazy='dynamic', cascade='all, delete-orphan'))
    batch = db.relationship('InventoryBatch', backref=db.backref('order_links', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<InStoreOrderBatch order={self.order_id} batch={self.batch_id} reserved={self.reserved_qty} sold={self.sold_qty} returned={self.returned_qty}>'

class Person(db.Model):
    """
    مدل واحد برای همه اشخاص (مشتری، مکانیک و ...)
    شماره تلفن شناسه یکتا است.
    """
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    telegram_id = db.Column(db.BigInteger, nullable=True, index=True)
    person_type = db.Column(db.String(20), nullable=False, comment='customer, mechanic, ...')
    # فیلدهای تکمیلی
    username = db.Column(db.String(100), nullable=True, comment='نام کاربری (اختیاری)')
    address = db.Column(db.Text, nullable=True, comment='آدرس کامل')
    city = db.Column(db.String(50), nullable=True, comment='شهر')
    province = db.Column(db.String(50), nullable=True, comment='استان')
    postal_code = db.Column(db.String(10), nullable=True, comment='کد پستی')
    # فیلدهای آماری و وفاداری
    total_orders = db.Column(db.Integer, default=0, comment='تعداد سفارشات')
    total_spent = db.Column(db.Float, default=0.0, comment='مجموع خرید')
    registration_date = db.Column(db.DateTime, default=datetime.datetime.utcnow, comment='تاریخ ثبت‌نام')
    last_order_date = db.Column(db.DateTime, nullable=True, comment='تاریخ آخرین سفارش')
    first_order_date = db.Column(db.DateTime, nullable=True, comment='تاریخ اولین سفارش')
    first_order_type = db.Column(db.String(20), nullable=True, comment='نوع اولین سفارش: تلگرام، حضوری، ربات')
    # سایر فیلدهای مشترک در صورت نیاز

    def __repr__(self):
        return f'<Person {self.full_name} - {self.phone_number}>'

    # متدهای محاسبه وفاداری و ... را می‌توان اینجا اضافه کرد

class MechanicProfile(db.Model):
    """
    اطلاعات تکمیلی فقط برای مکانیک‌ها
    """
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False, unique=True)
    commission_percentage = db.Column(db.Float, default=0.0)
    business_license = db.Column(db.String(100), nullable=True)
    business_license_image = db.Column(db.String(255), nullable=True)
    shop_address = db.Column(db.Text, nullable=True)
    # سایر فیلدهای خاص مکانیک در آینده

    person = db.relationship('Person', backref=db.backref('mechanic_profile', uselist=False))
