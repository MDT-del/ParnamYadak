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

product_category_table = db.Table(
    'product_category',
    db.Column('product_id',
              db.Integer,
              db.ForeignKey('product.id'),
              primary_key=True),
    db.Column('category_id',
              db.Integer,
              db.ForeignKey('category.id'),
              primary_key=True))

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


class Product(PaginationMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    image_file = db.Column(db.String(20),
                           nullable=False,
                           default='default.jpg')
    categories = db.relationship('Category',
                                 secondary=product_category_table,
                                 backref=db.backref('products', lazy=True))
    # آمار فروش
    total_sales = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f'<Product {self.name}>'


class Category(db.Model):
    __tablename__ = 'category'
    # ⬇️ تعریف یک محدودیت ترکیبی جدید ⬇️
    # این کد تضمین می‌کند که ترکیب "نام" و "شناسه والد" منحصر به فرد باشد
    __table_args__ = (UniqueConstraint('name',
                                       'parent_id',
                                       name='_name_parent_uc'), )

    id = db.Column(db.Integer, primary_key=True)
    # ⬇️ محدودیت unique=True از اینجا حذف شد ⬇️
    name = db.Column(db.String(100), nullable=False)

    parent_id = db.Column(db.Integer,
                          db.ForeignKey('category.id'),
                          nullable=True)

    parent = db.relationship('Category', remote_side=[id], backref=db.backref('children', lazy='dynamic', cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Category {self.name}>'

    @property
    def full_path(self):
        path = [self.name]
        current = self
        while True:
            parent = getattr(current, 'parent', None)
            if parent is None or not isinstance(parent, Category):
                break
            current = parent
            path.append(current.name)
        return ' > '.join(reversed(path))


class Customer(db.Model):
    """
    مدل مشتری
    این مدل اطلاعات مشتریان را نگهداری می‌کند و شماره تلفن به عنوان شناسه یکتا استفاده می‌شود.
    اگر مشتری از تلگرام یا حضوری ثبت شود، بر اساس شماره تلفن ادغام می‌گردد.
    """
    id = db.Column(db.Integer, primary_key=True)
    # شماره تلفن به عنوان شناسه یکتا و اجباری
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True, comment='شماره تلفن مشتری')
    # آیدی تلگرام (ممکن است خالی باشد)
    telegram_id = db.Column(db.BigInteger, nullable=True, index=True, comment='آیدی تلگرام (در صورت وجود)')
    # نوع مشتری
    customer_type = db.Column(db.String(20), default='حضوری', comment='نوع مشتری: حضوری، ربات، مکانیک')
    first_name = db.Column(db.String(100), nullable=True, comment='نام')
    last_name = db.Column(db.String(100), nullable=True, comment='نام خانوادگی')
    username = db.Column(db.String(100), nullable=True, comment='یوزرنیم تلگرام')
    address = db.Column(db.Text, nullable=True, comment='آدرس')
    city = db.Column(db.String(50), nullable=True, comment='شهر')
    province = db.Column(db.String(50), nullable=True, comment='استان')
    postal_code = db.Column(db.String(20), nullable=True, comment='کد پستی')
    device_id = db.Column(db.String(100), nullable=True, index=True, comment='شناسه دستگاه')
    last_known_ip = db.Column(db.String(45), nullable=True, comment='آخرین آی‌پی')
    # اطلاعات مالی و وفاداری
    total_orders = db.Column(db.Integer, default=0, comment='تعداد سفارشات')
    total_spent = db.Column(db.Float, default=0.0, comment='مجموع خرید')
    loyalty_points = db.Column(db.Integer, default=0, comment='امتیاز وفاداری')
    customer_level = db.Column(db.String(20), default='برنزی', comment='سطح مشتری')
    # is_vip = db.Column(db.Boolean, default=False, comment='مشتری VIP')  # حذف شد
    registration_date = db.Column(db.DateTime, default=datetime.datetime.utcnow, comment='تاریخ ثبت‌نام')
    last_order_date = db.Column(db.DateTime, nullable=True, comment='تاریخ آخرین سفارش')
    # اطلاعات اولین سفارش
    first_order_date = db.Column(db.DateTime, nullable=True, comment='تاریخ اولین سفارش')
    first_order_type = db.Column(db.String(20), nullable=True, comment='نوع اولین سفارش: تلگرام، حضوری، ربات')
    orders = db.relationship('Order', backref='customer', lazy='dynamic')
    instore_orders = db.relationship('InStoreOrder', backref='customer', lazy='dynamic')
    tickets = db.relationship('SupportTicket', backref='customer', lazy='dynamic')

    def __repr__(self):
        return f'<Customer {self.phone_number}>'

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"مشتری {self.phone_number}"

    def update_loyalty_stats(self):
        """بروزرسانی آمار وفاداری مشتری"""
        self.total_orders = self.orders.count() if hasattr(self.orders, 'count') else 0
        self.total_spent = db.session.query(func.sum(
            Order.total_price)).filter(
                Order.customer_id == self.id).scalar() or 0.0

        # محاسبه سطح وفاداری
        if self.total_spent >= 1000000:  # 1 میلیون تومان
            self.customer_level = 'الماس'
            self.loyalty_points = int(self.total_spent / 10000)
        elif self.total_spent >= 500000:  # 500 هزار تومان
            self.customer_level = 'طلایی'
            self.loyalty_points = int(self.total_spent / 5000)
        elif self.total_spent >= 200000:  # 200 هزار تومان
            self.customer_level = 'نقره‌ای'
            self.loyalty_points = int(self.total_spent / 2000)
        else:
            self.customer_level = 'برنزی'
            self.loyalty_points = int(self.total_spent / 1000)

    def update_first_order_info(self):
        """بروزرسانی اطلاعات اولین سفارش مشتری"""
        from app.models import BotOrder
        
        # اولین سفارش تلگرام
        first_telegram = self.orders.order_by(Order.order_date.asc()).first()
        # اولین سفارش حضوری
        first_instore = self.instore_orders.order_by(InStoreOrder.created_at.asc()).first()
        # اولین سفارش ربات (بر اساس شماره تلفن)
        first_bot = None
        if self.phone_number:
            first_bot = BotOrder.query.filter_by(customer_phone=self.phone_number).order_by(BotOrder.created_at.asc()).first()
        
        # مقایسه تاریخ‌ها و انتخاب اولین سفارش
        orders_to_compare = []
        if first_telegram:
            orders_to_compare.append((first_telegram.order_date, 'تلگرام'))
        if first_instore:
            orders_to_compare.append((first_instore.created_at, 'حضوری'))
        if first_bot:
            orders_to_compare.append((first_bot.created_at, 'ربات'))
        
        if orders_to_compare:
            # مرتب‌سازی بر اساس تاریخ و انتخاب اولین سفارش
            orders_to_compare.sort(key=lambda x: x[0])
            self.first_order_date, self.first_order_type = orders_to_compare[0]
        else:
            self.first_order_date = None
            self.first_order_type = None


class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer,
                            db.ForeignKey('customer.id'),
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

    # Foreign Key برای کوپن
    coupon_id = db.Column(db.Integer,
                          db.ForeignKey('coupon.id'),
                          nullable=True)

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

    def apply_coupon(self, coupon):
        """اعمال کوپن تخفیف"""
        if not coupon or not coupon.is_valid():
            return False, "کوپن نامعتبر است"

        # محاسبه تخفیف
        if coupon.discount_type == 'percent':
            discount_amount = self.total_price * (coupon.discount_value / 100)
        else:
            discount_amount = coupon.discount_value

        # بررسی حداکثر تخفیف
        if discount_amount > self.total_price:
            discount_amount = self.total_price

        self.discount_amount = discount_amount
        self.coupon_id = coupon.id
        self.calculate_final_price()

        # بروزرسانی آمار کوپن
        coupon.times_used += 1
        coupon.total_discount_given += discount_amount

        return True, f"تخفیف {discount_amount:,.0f} تومان اعمال شد"

    def remove_coupon(self):
        """حذف کوپن تخفیف"""
        if self.coupon_id:
            coupon = Coupon.query.get(self.coupon_id)
            if coupon:
                coupon.times_used -= 1
                coupon.total_discount_given -= self.discount_amount

            self.coupon_id = None
            self.discount_amount = 0.0
            self.calculate_final_price()
            return True, "کوپن حذف شد"
        return False, "کوپنی اعمال نشده است"


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer,
                           db.ForeignKey('product.id'),
                           nullable=False)
    product = db.relationship('Product')

    def __repr__(self):
        return f'<OrderItem {self.id}>'


class Coupon(db.Model):
    """مدل برای نگهداری کدهای تخفیف"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    # نوع تخفیف: 'percent' یا 'fixed'
    discount_type = db.Column(db.String(10), nullable=False, default='percent')
    discount_value = db.Column(db.Float, nullable=False)

    max_usage = db.Column(db.Integer, default=1)  # حداکثر تعداد استفاده
    times_used = db.Column(db.Integer, default=0)  # تعداد دفعات استفاده شده

    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)

    is_active = db.Column(db.Boolean, default=True)

    # اطلاعات مالی
    total_discount_given = db.Column(db.Float, default=0.0)

    # رابطه با سفارشات
    orders = db.relationship('Order', backref='coupon', lazy='dynamic')

    def __repr__(self):
        return f'<Coupon {self.code}>'

    def is_valid(self):
        """بررسی اعتبار کوپن"""
        now = datetime.datetime.utcnow()
        if not self.is_active:
            return False
        if self.times_used >= self.max_usage:
            return False
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


# --- مدل‌های جدید برای سیستم مالی و پشتیبانی ---


class FinancialTransaction(db.Model):
    """مدل برای تراکنش‌های مالی"""
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(50),
                                 nullable=False)  # فروش، بازگشت، تخفیف، commission_payment
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    customer_id = db.Column(db.Integer,
                            db.ForeignKey('customer.id'),
                            nullable=True)
    mechanic_id = db.Column(db.Integer, db.ForeignKey('mechanic.id'), nullable=True)
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
    customer = db.relationship('Customer', backref='transactions')
    mechanic = db.relationship('Mechanic', backref='transactions')
    created_by_user = db.relationship('User', backref='created_transactions')

    def __repr__(self):
        return f'<FinancialTransaction {self.id}>'


class SupportTicket(db.Model):
    """مدل برای تیکت‌های پشتیبانی"""
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer,
                            db.ForeignKey('customer.id'),
                            nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(30), default='باز')  # باز، در حال بررسی، بسته
    priority = db.Column(db.String(20),
                         default='عادی')  # کم، عادی، بالا، بحرانی
    category = db.Column(db.String(50),
                         default='عمومی')  # فنی، مالی، سفارش، شکایت
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

    messages = db.relationship('TicketMessage',
                               backref='ticket',
                               lazy='dynamic',
                               cascade="all, delete-orphan")

    def __repr__(self):
        return f'<SupportTicket {self.ticket_number}>'

    def generate_ticket_number(self):
        """تولید شماره تیکت"""
        if not self.ticket_number:
            year = datetime.datetime.now().year
            count = SupportTicket.query.filter(
                func.extract('year', SupportTicket.created_at) ==
                year).count()
            self.ticket_number = f"TKT-{year}-{count+1:04d}"


class TicketMessage(db.Model):
    """مدل برای پیام‌های تیکت"""
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer,
                          db.ForeignKey('support_ticket.id'),
                          nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # customer, admin
    sender_id = db.Column(db.Integer, nullable=False)  # customer_id یا user_id
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # فایل‌های پیوست
    attachment_path = db.Column(db.String(255), nullable=True)
    attachment_type = db.Column(db.String(20), nullable=True)  # photo, document

    def __repr__(self):
        return f'<TicketMessage {self.id}>'


class BroadcastMessage(db.Model):
    """مدل برای پیام‌های همگانی"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20),
                             default='text')  # text, photo, video, document
    target_type = db.Column(db.String(20),
                            default='all')  # all, specific, vip, new_customers
    target_customers = db.Column(db.Text,
                                 nullable=True)  # JSON array of customer IDs
    status = db.Column(db.String(20),
                       default='draft')  # draft, sent, scheduled
    scheduled_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer,
                           db.ForeignKey('user.id'),
                           nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # آمار ارسال
    total_sent = db.Column(db.Integer, default=0)
    total_delivered = db.Column(db.Integer, default=0)
    total_read = db.Column(db.Integer, default=0)

    created_by_user = db.relationship('User', backref='broadcast_messages')

    def __repr__(self):
        return f'<BroadcastMessage {self.id}>'


class CustomerSegment(db.Model):
    """مدل برای تقسیم‌بندی مشتریان"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    criteria = db.Column(db.Text, nullable=False)  # JSON criteria
    customer_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.datetime.utcnow,
                           onupdate=datetime.datetime.utcnow)

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
    مدل پیش‌سفارش - برای ثبت سفارش‌های حضوری مشتریان
    به جای ذخیره نام و شماره تلفن، به رکورد Customer ارجاع داده می‌شود.
    """
    __tablename__ = 'pre_orders'

    id = db.Column(db.Integer, primary_key=True)
    # ارجاع به مشتری
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False, comment='شناسه مشتری')
    customer = db.relationship('Customer', backref='pre_orders')
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
        return f'<PreOrder {self.id}: {self.customer_id}>'
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
            'customer_id': self.customer_id,
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
    این مدل برای ثبت سفارشات حضوری مشتریان استفاده می‌شود و به رکورد Customer ارجاع می‌دهد.
    """
    id = db.Column(db.Integer, primary_key=True)
    # ارجاع به مشتری
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False, comment='شناسه مشتری')
    # customer = db.relationship('Customer', backref='instore_orders')  # این خط حذف شد
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
        return f'<InStoreOrder {self.id}: {self.customer_id}>'
    
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

class ProductReview(db.Model):
    """
    مدل نظرات و امتیازهای محصولات
    """
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    
    # امتیاز (1 تا 5)
    rating = db.Column(db.Integer, nullable=False)
    # نظر
    review_text = db.Column(db.Text, nullable=True)
    # وضعیت (تایید شده، در انتظار تایید، رد شده)
    status = db.Column(db.String(20), default='در انتظار تایید')
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # روابط
    product = db.relationship('Product', backref='reviews')
    customer = db.relationship('Customer', backref='reviews')
    order = db.relationship('Order', backref='reviews')
    
    def __repr__(self):
        return f'<ProductReview {self.id} - Product: {self.product_id}, Rating: {self.rating}>'


class InventoryAlert(db.Model):
    """
    مدل اعلان‌های موجودی
    """
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    
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
    product = db.relationship('Product', backref='inventory_alerts')
    customer = db.relationship('Customer', backref='inventory_alerts')
    
    def __repr__(self):
        return f'<InventoryAlert {self.id} - Product: {self.product_id}, Type: {self.alert_type}>'


class PushNotification(db.Model):
    """
    مدل اعلان‌های فوری
    """
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
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
    customer = db.relationship('Customer', backref='push_notifications')
    
    def __repr__(self):
        return f'<PushNotification {self.id} - Customer: {self.customer_id}, Type: {self.notification_type}>'


class ShoppingCart(db.Model):
    """
    مدل سبد خرید
    """
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    telegram_id = db.Column(db.BigInteger, nullable=True)
    
    # اطلاعات سبد خرید
    total_price = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    final_price = db.Column(db.Float, default=0.0)
    
    # کوپن اعمال شده
    applied_coupon_id = db.Column(db.Integer, db.ForeignKey('coupon.id'), nullable=True)
    
    # وضعیت سبد خرید
    status = db.Column(db.String(20), default='فعال')  # فعال، تبدیل شده، منقضی شده
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # روابط
    customer = db.relationship('Customer', backref='shopping_carts')
    applied_coupon = db.relationship('Coupon', backref='applied_carts')
    items = db.relationship('CartItem', backref='cart', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ShoppingCart {self.id} - Customer: {self.customer_id}, Total: {self.total_price}>'
    
    def calculate_total(self):
        """محاسبه قیمت کل سبد خرید"""
        total = 0.0
        for item in self.items:
            total += item.total_price
        self.total_price = total
        self.calculate_final_price()
        return total
    
    def calculate_final_price(self):
        """محاسبه قیمت نهایی با اعمال تخفیف"""
        self.final_price = self.total_price - self.discount_amount
        return self.final_price
    
    def apply_coupon(self, coupon):
        """اعمال کوپن تخفیف"""
        if not coupon or not coupon.is_valid():
            return False, "کوپن نامعتبر است"
        
        if coupon.times_used >= coupon.max_usage:
            return False, "کوپن تمام شده است"
        
        # محاسبه تخفیف
        if coupon.discount_type == 'percent':
            discount = (self.total_price * coupon.discount_value) / 100
        else:  # fixed
            discount = coupon.discount_value
        
        self.discount_amount = discount
        self.applied_coupon_id = coupon.id
        self.calculate_final_price()
        
        return True, f"کوپن {coupon.code} با موفقیت اعمال شد"
    
    def remove_coupon(self):
        """حذف کوپن تخفیف"""
        self.discount_amount = 0.0
        self.applied_coupon_id = None
        self.calculate_final_price()
        return True, "کوپن حذف شد"


class CartItem(db.Model):
    """
    مدل آیتم‌های سبد خرید
    """
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('shopping_cart.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    # اطلاعات محصول
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # روابط
    product = db.relationship('Product', backref='cart_items')
    
    def __repr__(self):
        return f'<CartItem {self.id} - Product: {self.product_id}, Qty: {self.quantity}>'
    
    def calculate_total(self):
        """محاسبه قیمت کل آیتم"""
        self.total_price = self.quantity * self.unit_price
        return self.total_price


class ProductRating(db.Model):
    """
    مدل امتیازهای محصولات (آمار)
    """
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
    # آمار امتیازها
    total_ratings = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    rating_1_count = db.Column(db.Integer, default=0)
    rating_2_count = db.Column(db.Integer, default=0)
    rating_3_count = db.Column(db.Integer, default=0)
    rating_4_count = db.Column(db.Integer, default=0)
    rating_5_count = db.Column(db.Integer, default=0)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # روابط
    product = db.relationship('Product', backref='rating_stats')
    
    def __repr__(self):
        return f'<ProductRating {self.id} - Product: {self.product_id}, Avg: {self.average_rating}>'
    
    def update_stats(self):
        """به‌روزرسانی آمار امتیازها"""
        reviews = ProductReview.query.filter_by(
            product_id=self.product_id,
            status='تایید شده'
        ).all()
        
        self.total_ratings = len(reviews)
        
        if self.total_ratings > 0:
            total_rating = sum(review.rating for review in reviews)
            self.average_rating = total_rating / self.total_ratings
            
            # شمارش امتیازهای مختلف
            self.rating_1_count = sum(1 for r in reviews if r.rating == 1)
            self.rating_2_count = sum(1 for r in reviews if r.rating == 2)
            self.rating_3_count = sum(1 for r in reviews if r.rating == 3)
            self.rating_4_count = sum(1 for r in reviews if r.rating == 4)
            self.rating_5_count = sum(1 for r in reviews if r.rating == 5)
        else:
            self.average_rating = 0.0
            self.rating_1_count = 0
            self.rating_2_count = 0
            self.rating_3_count = 0
            self.rating_4_count = 0
            self.rating_5_count = 0

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
    purchase_price = db.Column(db.Float, nullable=True, comment='قیمت خرید (اختیاری)')
    
    # اطلاعات ثبت‌کننده
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, comment='کاربر ثبت‌کننده')
    created_at = db.Column(db.DateTime, default=tehran_now, comment='تاریخ ورود به انبار')
    
    # روابط
    created_by_user = db.relationship('User', backref='created_batches')
    
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


class Mechanic(db.Model):
    """
    مدل مکانیک‌ها
    مکانیک‌ها از طریق ربات تلگرام ثبت‌نام می‌کنند.
    """
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False, comment='آیدی تلگرام')
    
    # اطلاعات شخصی
    first_name = db.Column(db.String(100), nullable=False, comment='نام')
    last_name = db.Column(db.String(100), nullable=True, comment='نام خانوادگی')
    phone_number = db.Column(db.String(20), nullable=False, comment='شماره تلفن')
    username = db.Column(db.String(100), nullable=True, comment='یوزرنیم تلگرام')
    
    # اطلاعات مالی
    card_number = db.Column(db.String(20), nullable=True, comment='شماره کارت')
    sheba_number = db.Column(db.String(30), nullable=True, comment='شماره شبا')
    
    # اطلاعات کسب‌وکار
    shop_address = db.Column(db.Text, nullable=True, comment='آدرس مغازه')
    business_license = db.Column(db.String(100), nullable=True, comment='شماره جواز کسب')
    business_license_image = db.Column(db.String(255), nullable=True, comment='مسیر عکس جواز کسب')
    
    # وضعیت تایید
    is_approved = db.Column(db.Boolean, default=False, comment='تایید شده')
    # اضافه کردن وضعیت رد شده
    is_rejected = db.Column(db.Boolean, default=False, comment='رد شده')
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, comment='کاربر تاییدکننده')
    approved_at = db.Column(db.DateTime, nullable=True, comment='تاریخ تایید')
    
    # کمیسیون
    commission_percentage = db.Column(db.Float, default=0.0, comment='درصد کمیسیون')
    
    # آمار
    total_orders = db.Column(db.Integer, default=0, comment='تعداد سفارشات')
    total_commission = db.Column(db.Float, default=0.0, comment='مجموع کمیسیون')
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=tehran_now, comment='تاریخ ثبت‌نام')
    updated_at = db.Column(db.DateTime, default=tehran_now, onupdate=tehran_now, comment='تاریخ بروزرسانی')
    
    # روابط
    approved_by_user = db.relationship('User', backref='approved_mechanics')
    bot_orders = db.relationship('BotOrder', backref='mechanic', lazy='dynamic')
    
    def __repr__(self):
        return f'<Mechanic {self.first_name} {self.last_name}>'
    
    @property
    def full_name(self):
        """نام کامل مکانیک"""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    def approve(self, user_id, commission_percentage):
        """تایید مکانیک"""
        self.is_approved = True
        self.approved_by = user_id
        self.approved_at = tehran_now()
        self.commission_percentage = commission_percentage
        db.session.commit()


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
    mechanic_id = db.Column(db.Integer, db.ForeignKey('mechanic.id'), nullable=True, comment='مکانیک مرتبط')
    # اطلاعات مشتری (اختیاری)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True, comment='مشتری مرتبط')
    
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
        if self.mechanic and self.mechanic.is_approved:
            self.commission_amount = self.total_amount * (self.mechanic.commission_percentage / 100)
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


class CustomerHistory(db.Model):
    """تاریخچه کامل مشتری - شامل همه سفارشات، پرداخت‌ها و فعالیت‌ها"""
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    
    # نوع فعالیت
    activity_type = db.Column(db.String(50), nullable=False)  # order, payment, support, etc.
    
    # اطلاعات فعالیت
    activity_data = db.Column(db.Text, nullable=False)  # JSON data
    amount = db.Column(db.Float, nullable=True)  # مبلغ (در صورت وجود)
    
    # مرجع فعالیت
    reference_type = db.Column(db.String(50), nullable=True)  # order, bot_order, support_ticket, etc.
    reference_id = db.Column(db.Integer, nullable=True)  # ID مرجع
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # روابط
    customer = db.relationship('Customer', backref='history')   
    def __repr__(self):
        return f'<CustomerHistory {self.customer_id}: {self.activity_type}>'

class PaymentHistory(db.Model):
    """تاریخچه پرداخت‌ها - شامل همه پرداخت‌های مشتریان و مکانیک‌ها"""
    id = db.Column(db.Integer, primary_key=True)
    
    # نوع پرداخت
    payment_type = db.Column(db.String(50), nullable=False)  # order_payment, commission, refund, etc.
    
    # اطلاعات پرداخت‌کننده
    payer_type = db.Column(db.String(20), nullable=False)  # customer, mechanic
    payer_id = db.Column(db.Integer, nullable=False)  # customer_id یا mechanic_id
    
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
    
    # کاربر انجام‌دهنده
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # روابط
    product = db.relationship('InventoryProduct', backref='inventory_history')
    batch = db.relationship('InventoryBatch', backref='inventory_history')
    performed_by_user = db.relationship('User', backref='inventory_operations')   
    def __repr__(self):
        return f'<InventoryHistory {self.product_id}: {self.operation_type} {self.quantity}>'

class CommissionHistory(db.Model):
    """تاریخچه پرداخت کمیسیون مکانیک‌ها"""
    id = db.Column(db.Integer, primary_key=True)
    
    # مکانیک
    mechanic_id = db.Column(db.Integer, db.ForeignKey('mechanic.id'), nullable=False)
    
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
    mechanic = db.relationship('Mechanic', backref='commission_history')
    order = db.relationship('BotOrder', backref='commission_history')
    paid_by_user = db.relationship('User', backref='paid_commissions')   
    def __repr__(self):
        return f'<CommissionHistory {self.mechanic_id}: {self.commission_amount}>'

class MechanicOrderHistory(db.Model):
    """تاریخچه سفارشات مکانیک‌ها"""
    id = db.Column(db.Integer, primary_key=True)
    
    # مکانیک
    mechanic_id = db.Column(db.Integer, db.ForeignKey('mechanic.id'), nullable=False)
    
    # سفارش
    order_id = db.Column(db.Integer, db.ForeignKey('bot_order.id'), nullable=False)
    
    # وضعیت سفارش
    status = db.Column(db.String(50), nullable=False)
    status_changed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # اطلاعات اضافی
    notes = db.Column(db.Text, nullable=True)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # روابط
    mechanic = db.relationship('Mechanic', backref='order_history')
    order = db.relationship('BotOrder', backref='status_history')   
    def __repr__(self):
        return f'<MechanicOrderHistory {self.mechanic_id}: {self.status}>'

class SupportMessageHistory(db.Model):
    """تاریخچه پیام‌های پشتیبانی هر کاربر"""
    id = db.Column(db.Integer, primary_key=True)
    
    # کاربر
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # تیکت و پیام
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('ticket_message.id'), nullable=False)
    
    # نوع پیام
    message_type = db.Column(db.String(20), nullable=False)  # sent, received
    
    # اطلاعات پیام
    message_preview = db.Column(db.String(200), nullable=True)  # خلاصه پیام
    has_attachment = db.Column(db.Boolean, default=False)
    attachment_type = db.Column(db.String(20), nullable=True)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # روابط
    user = db.relationship('User', backref='support_message_history')
    ticket = db.relationship('SupportTicket', backref='message_history')
    message = db.relationship('TicketMessage', backref='history_records')   
    def __repr__(self):
        return f'<SupportMessageHistory {self.user_id}: {self.message_type}>'

class BroadcastHistory(db.Model):
    """اریخچه پیام‌های همگانی"""
    id = db.Column(db.Integer, primary_key=True)
    
    # پیام همگانی
    broadcast_id = db.Column(db.Integer, db.ForeignKey('broadcast_message.id'), nullable=False)
    
    # اطلاعات ارسال
    target_type = db.Column(db.String(20), nullable=False)  # all, specific, vip, etc.
    target_count = db.Column(db.Integer, default=0)  # تعداد هدف
    
    # آمار ارسال
    sent_count = db.Column(db.Integer, default=0)
    delivered_count = db.Column(db.Integer, default=0)
    read_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    
    # وضعیت ارسال
    status = db.Column(db.String(20), default='pending')  # pending, sending, completed, failed
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # روابط
    broadcast = db.relationship('BroadcastMessage', backref='send_history')   
    def __repr__(self):
        return f'<BroadcastHistory {self.broadcast_id}: {self.status}>'

class SalesHistory(db.Model):
    """اریخچه فروش - برای گزارش‌گیری روزانه/ماهانه/سالانه"""
    id = db.Column(db.Integer, primary_key=True)
    
    # دوره زمانی
    period_type = db.Column(db.String(20), nullable=False)  # daily, monthly, yearly
    period_date = db.Column(db.Date, nullable=False)  # تاریخ دوره
    
    # آمار فروش
    total_orders = db.Column(db.Integer, default=0)
    total_amount = db.Column(db.Float, default=0.0)
    total_items = db.Column(db.Integer, default=0)
    # آمار مشتریان
    new_customers = db.Column(db.Integer, default=0)
    returning_customers = db.Column(db.Integer, default=0)
    # آمار محصولات
    top_products = db.Column(db.Text, nullable=True)  # JSON array of top products
    
    # آمار مکانیک‌ها
    mechanic_orders = db.Column(db.Integer, default=0)
    mechanic_commission = db.Column(db.Float, default=0.0)
    
    # تاریخ‌ها
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<SalesHistory {self.period_type}: {self.period_date}>'

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

class MechanicOrderState(db.Model):
    __tablename__ = 'mechanic_order_states'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, index=True, nullable=False)
    order_id = db.Column(db.Integer, index=True, nullable=False)
    step = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'order_id': self.order_id,
            'step': self.step,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

def ensure_admin_has_all_permissions():
    from app import db
    from app.models import Role, Permission
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        admin_role = Role(name='admin', description='مدیر کل سیستم')
        db.session.add(admin_role)
        db.session.commit()
    all_perms = Permission.query.all()
    for perm in all_perms:
        if perm not in admin_role.permissions:
            admin_role.permissions.append(perm)
    db.session.commit()
