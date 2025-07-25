# ---------------------------------------------
# فایل: forms.py
# توضیح: این فایل شامل فرم‌های WTForms برای مدیریت داده‌های ورودی کاربران است.
# هر فرم نمایانگر یک عملیات یا صفحه در سیستم می‌باشد.
# ---------------------------------------------

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FloatField, IntegerField, SelectField, SelectMultipleField, DecimalField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Optional, Length, NumberRange, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from .models import Role, Permission, Person, InventoryProduct
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms.fields import DateTimeLocalField as DateTimeField, DateField
import re
import json


def validate_password_strength(form, field):
    """
    اعتبارسنجی قوی بودن رمز عبور
    """
    password = field.data
    if len(password) < 6:
        raise ValidationError('رمز عبور باید حداقل ۶ کاراکتر باشد.')
    if not re.match(r'^[A-Za-z0-9]+$', password):
        raise ValidationError('رمز عبور فقط باید شامل حروف و اعداد باشد (بدون کاراکتر خاص).')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('رمز عبور باید حداقل یک حرف بزرگ داشته باشد.')
    if not re.search(r'[a-z]', password):
        raise ValidationError('رمز عبور باید حداقل یک حرف کوچک داشته باشد.')
    if not re.search(r'[0-9]', password):
        raise ValidationError('رمز عبور باید حداقل یک عدد داشته باشد.')


def validate_username_format(form, field):
    """
    اعتبارسنجی فرمت نام کاربری
    """
    username = field.data
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        raise ValidationError(
            'نام کاربری باید ۳ تا ۲۰ کاراکتر و شامل حروف، اعداد و _ باشد.')


def validate_phone_number(form, field):
    """
    اعتبارسنجی شماره تلفن
    """
    if field.data:
        phone = field.data.replace(' ', '').replace('-', '').replace('+', '')
        if not re.match(r'^09\d{9}$', phone):
            raise ValidationError(
                'شماره تلفن باید با ۰۹ شروع شود و ۱۱ رقم باشد.')


# توابع کمکی برای پر کردن فیلدهای انتخابی
def permission_query():
    return Permission.query.order_by(Permission.id).all()


def role_query():
    # تمام نقش‌ها را نمایش می‌دهیم
    return Role.query.order_by(Role.name).all()


# --- فرم‌های موجود ---


class LoginForm(FlaskForm):
    """
    فرم ورود کاربران
    """
    username = StringField(
        'نام کاربری',
        validators=[DataRequired(message="این فیلد الزامی است.")])
    password = PasswordField(
        'رمز عبور', validators=[DataRequired(message="این فیلد الزامی است.")])
    remember_me = BooleanField('مرا به خاطر بسپار')
    submit = SubmitField('ورود')


class ProductForm(FlaskForm):
    """
    فرم افزودن و ویرایش محصول
    """
    name = StringField('نام محصول',
                       validators=[
                           DataRequired(message="نام محصول الزامی است."),
                           Length(min=2, max=100)
                       ])

    description = TextAreaField('توضیح��ت',
                                validators=[Optional(),
                                            Length(max=1000)])
    price = FloatField('قیمت',
                       validators=[
                           DataRequired(),
                           NumberRange(min=0,
                                       message="قیمت نمی‌تواند منفی باشد.")
                       ])
    stock = IntegerField('موجودی',
                         validators=[
                             DataRequired(),
                             NumberRange(min=0,
                                         message="موجودی نمی‌تواند منفی باشد.")
                         ])
    picture = FileField(
        'عکس محصول (اختیاری)',
        validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'فقط عکس مجاز است!')])
    submit = SubmitField('ثبت محصول')


# --- فرم‌های جدید برای مدیریت کاربران ---


class CreateUserForm(FlaskForm):
    """فرم ساخت کاربر جدید"""
    username = StringField(
        'نام کاربری (انگلیسی)',
        validators=[DataRequired(), validate_username_format])
    name = StringField('نام کامل (فارسی)',
                       validators=[DataRequired(),
                                   Length(min=2, max=100)])
    password = PasswordField(
        'رمز عبور',
        validators=[
            DataRequired(),
            Length(min=4, message='رمز عبور باید حداقل ۴ کاراکتر باشد'),
            validate_password_strength,
            EqualTo('confirm', message='رمزهای عبور باید یکسان باشند')
        ])
    confirm = PasswordField('تکرار رمز عبور')
    roles = QuerySelectMultipleField('نقش‌ها',
                                     query_factory=role_query,
                                     get_label='name',
                                     allow_blank=True)
    submit = SubmitField('ساخت کاربر')


class EditUserForm(FlaskForm):
    """فرم ویرایش کاربر"""
    username = StringField(
        'نام کاربری (انگلیسی)',
        validators=[DataRequired(), validate_username_format])
    name = StringField('نام کامل (فارسی)',
                       validators=[DataRequired(),
                                   Length(min=2, max=100)])
    password = PasswordField(
        'رمز عبور جدید (اختیاری)',
        validators=[
            Optional(),
            Length(min=4, message='رمز عبور باید حداقل ۴ کاراکتر باشد'),
            validate_password_strength,
            EqualTo('confirm', message='رمزهای عبور باید یکسان باشند')
        ])
    confirm = PasswordField('تکرار رمز عبور جدید')
    unlock_account = BooleanField('آنلاک حساب کاربر')
    roles = QuerySelectMultipleField('نقش‌ها',
                                     query_factory=role_query,
                                     get_label='name',
                                     allow_blank=True)
    submit = SubmitField('ذخیره تغییرات')


class RoleForm(FlaskForm):
    """فرم افزودن و ویرایش نقش"""
    name = StringField('نام نقش (انگلیسی)', validators=[DataRequired()])
    description = StringField('توضیحات (فارسی)', validators=[DataRequired()])
    permissions = QuerySelectMultipleField(
        'مجوزها',
        query_factory=permission_query,
        get_label='description',
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput())
    submit = SubmitField('ثبت نقش')


class ChangePasswordForm(FlaskForm):
    """فرم تغییر رمز عبور کاربر"""
    current_password = PasswordField('رمز عبور فعلی',
                                     validators=[DataRequired()])
    new_password = PasswordField(
        'رمز عبور جدید',
        validators=[
            DataRequired(),
            Length(min=8, message='رمز عبور باید حداقل ۸ کاراکتر باشد'),
            validate_password_strength,
            EqualTo('confirm', message='رمزهای عبور باید یکسان باشند')
        ])
    confirm = PasswordField('تکرار رمز عبور جدید')
    submit = SubmitField('تغییر رمز عبور')


class CouponForm(FlaskForm):
    """فرم افزودن و ویرایش کوپن تخفیf"""
    code = StringField('کد تخفیف (مثال: EID1404)', validators=[DataRequired()])
    description = StringField('توضیحات (اختیاری)')

    discount_type = SelectField('نوع تخفیف',
                                choices=[('percent', 'درصدی'),
                                         ('fixed', 'مبلغ ثابت')],
                                validators=[DataRequired()])
    discount_value = FloatField(
        'مقدار تخفیف', validators=[DataRequired(),
                                   NumberRange(min=0)])

    max_usage = IntegerField('حداکثر تعداد استفاده',
                             validators=[DataRequired(),
                                         NumberRange(min=1)],
                             default=1)

    start_date = DateField('تاریخ شروع (اختیاری)',
                           format='%Y-%m-%d',
                           validators=[Optional()])
    end_date = DateField('تاریخ انقضا (اختیاری)',
                         format='%Y-%m-%d',
                         validators=[Optional()])

    is_active = BooleanField('فعال باشد', default=True)
    submit = SubmitField('ثبت کوپن')


class BroadcastMessageForm(FlaskForm):
    """فرم پیام همگانی"""
    title = StringField('عنوان پیام',
                        validators=[
                            DataRequired(message='عنوان پیام الزامی است'),
                            Length(
                                min=3,
                                max=200,
                                message='عنوان باید بین 3 تا 200 کاراکتر باشد')
                        ])

    message = TextAreaField(
        'متن پیام',
        validators=[
            DataRequired(message='متن پیام الزامی است'),
            Length(min=10,
                   max=4000,
                   message='متن پیام باید بین 10 تا 4000 کاراکتر باشد')
        ])

    message_type = SelectField('نوع پیام',
                               choices=[('text', 'متن'), ('photo', 'عکس'),
                                        ('video', 'ویدیو'),
                                        ('document', 'فایل')],
                               default='text')

    target_type = SelectField('نوع هدف',
        choices=[('all', 'همه مشتریان'),
                 ('mechanic_all', 'همه مکانیک‌ها'),
                 ('vip', 'مشتریان VIP'),
                 ('specific', 'مشتری خاص'),
                 ('mechanic_specific', 'مکانیک خاص')],
        default='all')

    target_customers = StringField('مشتریان خاص (JSON)',
                                   validators=[Optional()])

    status = SelectField('وضعیت',
                         choices=[('draft', 'پیش‌نویس'),
                                  ('scheduled', 'زمان‌بندی شده'),
                                  ('sent', 'ارسال ��ده')],
                         default='draft')

    scheduled_at = DateTimeField('زمان ارسال',
                                 validators=[Optional()],
                                 format='%Y-%m-%d %H:%M')

    submit = SubmitField('ذخیره پیام')

    def validate_target_customers(self, field):
        """اعتبارسنجی لیست مشتریان یا مکانیک‌های خاص"""
        if self.target_type.data in ['specific', 'mechanic_specific'] and field.data:
            try:
                ids = json.loads(field.data)
                if not isinstance(ids, list):
                    raise ValueError("فرمت نامعتبر")

                # بررسی وجود مشتری یا مکانیک
                if self.target_type.data == 'specific':
                    existing = Person.query.filter(Person.id.in_(ids), Person.person_type == 'customer').count()
                else:
                    existing = Person.query.filter(Person.id.in_(ids), Person.person_type == 'mechanic').count()

                if existing != len(ids):
                    raise ValidationError('برخی از گیرندگان یافت نشدند')

            except (json.JSONDecodeError, ValueError):
                raise ValidationError('فرمت JSON نامعتبر است')


class TicketReplyForm(FlaskForm):
    """فرم پاسخ به تیکت"""
    message = TextAreaField(
        'پاسخ',
        validators=[
            DataRequired(message='متن پاسخ الزامی است'),
            Length(min=5,
                   max=2000,
                   message='پاسخ باید بین 5 تا 2000 کاراکتر باشد')
        ])

    submit = SubmitField('ارسال پاسخ')


class TicketFilterForm(FlaskForm):
    """فرم فیلتر تیکت‌ها"""
    status = SelectField('وضعیت',
                         choices=[('all', 'همه'), ('باز', 'باز'),
                                  ('در حال بررسی', 'در حال بررسی'),
                                  ('بسته', 'بسته')],
                         default='all')

    priority = SelectField('اولویت',
                           choices=[('all', 'همه'), ('کم', 'کم'),
                                    ('عادی', 'عادی'), ('بالا', 'بالا'),
                                    ('بحرانی', 'بحرانی')],
                           default='all')

    category = SelectField('دسته‌بندی',
                           choices=[('all', 'همه'), ('عمومی', 'عمومی'),
                                    ('فنی', 'فنی'), ('مالی', 'مالی'),
                                    ('سفارش', 'سفارش'), ('شکایت', 'شکایت')],
                           default='all')

    submit = SubmitField('اعمال فیلتر')


class FinancialReportForm(FlaskForm):
    """فرم گزارش‌های مالی"""
    start_date = DateField('تاریخ شروع',
                           validators=[Optional()],
                           format='%Y-%m-%d')
    end_date = DateField('تاریخ پایان',
                         validators=[Optional()],
                         format='%Y-%m-%d')

    period = SelectField('دوره',
                         choices=[('daily', 'روزانه'), ('weekly', 'هفتگی'),
                                  ('monthly', 'ماهانه'), ('yearly', 'سالانه')],
                         default='monthly')

    report_type = SelectField('نوع گزارش',
                              choices=[('sales', 'گزارش فروش'),
                                       ('customers', 'گزارش مشتریان'),
                                       ('products', 'گزارش محصولات'),
                                       ('coupons', 'گزارش کوپن‌ها')],
                              default='sales')

    submit = SubmitField('نمایش گزارش')


class CustomerSegmentForm(FlaskForm):
    """فرم تقسیم‌بندی مشتریان"""
    name = StringField('نام تقسیم‌بندی',
                       validators=[
                           DataRequired(message='نام تقسیم‌بندی الزامی است'),
                           Length(min=3,
                                  max=100,
                                  message='نام باید بین 3 تا 100 کاراکتر باشد')
                       ])

    description = TextAreaField('توضیحات',
                                validators=[
                                    Optional(),
                                    Length(
                                        max=500,
                                        message='توضیحات حداکثر 500 کاراکتر')
                                ])

    criteria = StringField(
        'معیارها (JSON)',
        validators=[DataRequired(message='معیارها الزامی است')])

    submit = SubmitField('ذخیره تقسیم‌بندی')

    def validate_criteria(self, field):
        """اعتبارسنجی معیارهای تقسیم‌بندی"""
        try:
            criteria = json.loads(field.data)
            if not isinstance(criteria, dict):
                raise ValueError("فرمت نامعتبر")

            # بررسی معیارهای مجاز
            allowed_criteria = [
                'customer_level', 'total_orders', 'total_spent',
                'registration_date', 'last_order_date'
            ]
            for key in criteria.keys():
                if key not in allowed_criteria:
                    raise ValidationError(f'معیار {key} مجاز نیست')

        except json.JSONDecodeError:
            raise ValidationError('فرمت JSON نامعتبر است')


class InvoiceForm(FlaskForm):
    """فرم فاکتور"""
    customer_id = SelectField(
        'مشتری',
        coerce=int,
        validators=[DataRequired(message='انتخاب مشتری الزامی است')])

    items = StringField(
        'موارد فاکتور (JSON)',
        validators=[DataRequired(message='موارد فاکتور الزامی است')])

    discount_amount = FloatField(
        'مبلغ تخفیف',
        validators=[
            Optional(),
            NumberRange(min=0, message='مبلغ تخفیف نمی‌تواند منفی باشد')
        ],
        default=0.0)

    tax_amount = FloatField('مبلغ مالیات',
                            validators=[
                                Optional(),
                                NumberRange(
                                    min=0,
                                    message='مبلغ مالیات نمی‌تواند منفی باشد')
                            ],
                            default=0.0)

    shipping_cost = FloatField(
        'هزینه ارسال',
        validators=[
            Optional(),
            NumberRange(min=0, message='هزینه ارسال نمی‌تواند منفی باشد')
        ],
        default=0.0)

    payment_method = SelectField('روش پرداخت',
                                 choices=[('نقدی', 'نقدی'),
                                          ('کارت بانکی', 'کارت بانکی'),
                                          ('آنلاین', 'آنلاین'), ('چک', 'چک')],
                                 default='نقدی')

    submit = SubmitField('ایجاد فاکتور')

    def __init__(self, *args, **kwargs):
        super(InvoiceForm, self).__init__(*args, **kwargs)
        # پر کردن لیست مشتریان
        self.customer_id.choices = [(c.id, c.full_name)
                                    for c in Person.query.filter_by(person_type='customer').all()]

    def validate_items(self, field):
        """اعتبارسنجی موارد فاکتور"""
        try:
            items = json.loads(field.data)
            if not isinstance(items, list):
                raise ValueError("فرمت نامعتبر")

            for item in items:
                if not isinstance(item, dict):
                    raise ValidationError('هر مورد باید یک شیء باشد')

                required_fields = ['product_id', 'quantity', 'price_per_unit']
                for field_name in required_fields:
                    if field_name not in item:
                        raise ValidationError(f'فیلد {field_name} الزامی است')

                # بررسی وجود محصول
                product = InventoryProduct.query.get(item['product_id'])
                if not product:
                    raise ValidationError(
                        f'محصول با شناسه {item["product_id"]} یافت نشد')

                # بررسی موجودی
                if item['quantity'] > product.available_quantity:
                    raise ValidationError(
                        f'موجودی محصول {product.name} کافی نیست')

        except json.JSONDecodeError:
            raise ValidationError('فرمت JSON نامعتبر است')


class PreOrderForm(FlaskForm):
    """
    فرم پیش‌سفارش - برای ثبت و ویرایش پیش‌سفارش‌ها
    """
    customer_name = StringField(
        'نام مشتری',
        validators=[
            DataRequired(message='نام مشتری الزامی است'),
            Length(min=2,
                   max=100,
                   message='نام باید بین 2 تا 100 کاراکتر باشد')
        ])

    customer_phone = StringField(
        'شماره تلفن',
        validators=[
            DataRequired(message='شماره تلفن الزامی است'),
            Length(min=10,
                   max=20,
                   message='شماره تلفن باید بین 10 تا 20 کاراکتر باشد')
        ])

    shipping_required = BooleanField('��رسال پستی')

    province = StringField(
        'استان',
        validators=[
            Optional(),
            Length(max=50,
                   message='نام استان نمی‌تواند بیشتر از 50 کاراکتر باشد')
        ])

    city = StringField(
        'شهرستان',
        validators=[
            Optional(),
            Length(max=50,
                   message='نام شهرستان نمی‌تواند بیشتر از 50 کاراکتر باشد')
        ])

    address = TextAreaField(
        'آدرس کامل',
        validators=[
            Optional(),
            Length(max=500, message='آدرس نمی‌تواند بیشتر از 500 کاراکتر باشد')
        ])

    postal_code = StringField('کد پستی',
                              validators=[
                                  Optional(),
                                  Length(min=10,
                                         max=10,
                                         message='کد پستی باید 10 رقم باشد')
                              ])

    products_info = HiddenField(
        'اطلاعات محصولا��',
        validators=[DataRequired(message='اطلاعات محصولات الزامی است')])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # اگر اطلاعات محصولات JSON است، آن را استخراج کن
        if self.products_info.data and self.products_info.data.startswith('{'):
            try:
                import json
                data = json.loads(self.products_info.data)
                if 'description' in data:
                    self.products_info.data = data['description']
            except:
                pass

    total_price = DecimalField('قیمت کل',
                               validators=[
                                   Optional(),
                                   NumberRange(
                                       min=0,
                                       message='قیمت نمی‌تواند منفی باشد')
                               ])

    status = SelectField('وضعیت',
                         choices=[('درحال پیگیری', 'درحال پیگیری'),
                                  ('خریداری شده', 'خریداری شده'),
                                  ('تحویل داده شده', 'تحویل داده شده'),
                                  ('لغو شده', 'لغو شده')],
                         validators=[DataRequired(message='وضعیت الزامی است')])

    notes = TextAreaField(
        'یادداشت‌ها',
        validators=[
            Optional(),
            Length(max=1000,
                   message='یادداشت نمی‌تواند بیشتر از 1000 کاراکتر باشد')
        ])

    submit = SubmitField('ثبت پیش‌سفارش')

    def validate(self, extra_validators=None):
        """اعتبارسنجی سفارشی برای فرم"""
        # اجرای اعتبارسنج‌های پیش‌فرض
        initial_validation = super(PreOrderForm,
                                   self).validate(extra_validators)
        if not initial_validation:
            return False

        # ۱. بررسی فیلدهای آدرس در صورت نیاز به ارسال پستی
        if self.shipping_required.data:
            if not self.province.data:
                self.province.errors.append('استان الزامی است.')
            if not self.city.data:
                self.city.errors.append('شهرستان الزامی است.')
            if not self.address.data:
                self.address.errors.append('آدرس کامل الزامی است.')
            if not self.postal_code.data:
                self.postal_code.errors.append('کد پستی الزامی است.')

        # ۲. بررسی قیمت کل در وضعیت "خریداری شده"
        if self.status.data == 'خریداری شده' and not self.total_price.data:
            self.total_price.errors.append('قیمت کل در این وضعیت الزامی است.')

        # اگر خطایی اضافه شده باشد، اعتبارسنجی ناموفق است
        return not (self.province.errors or self.city.errors
                    or self.address.errors or self.postal_code.errors
                    or self.total_price.errors)

    def validate_products_info(self, field):
        """
        اعتبارسنجی اطلاعات محصولات
        """
        try:
            products = json.loads(field.data)
            if not isinstance(products, list) or len(products) == 0:
                raise ValidationError('حداقل یک محصول باید وارد شود.')
            for p in products:
                if not isinstance(p, dict) or not p.get('name') or not p.get(
                        'qty') or not p.get('price'):
                    raise ValidationError('همه فیلدهای محصولات باید پر شوند.')
        except Exception:
            raise ValidationError('فرمت اطلاعات محصولات معتبر نیست.')