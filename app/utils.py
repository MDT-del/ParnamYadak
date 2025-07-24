# ---------------------------------------------
# فایل: utils.py
# توضیح: این فایل شامل توابع کمکی برای بررسی و دریافت اطلاعات لایسنس است.
# ---------------------------------------------

import os
import json
import datetime
from flask import request, url_for

from flask import current_app
from jinja2 import pass_context

try:
    import user_agents
    ua_parse = user_agents.parse
except ImportError:
    ua_parse = None

import jdatetime


def shamsi_date(gregorian_date, reverse=False):
    """
    تبدیل تاریخ میلادی به شمسی
    
    Args:
        gregorian_date: تاریخ میلادی (string یا datetime)
        reverse: اگر True باشد، تاریخ شمسی را به میلادی تبدیل می‌کند
    
    Returns:
        str: تاریخ شمسی در فرمت YYYY/MM/DD
    """
    if not gregorian_date:
        return ""
    
    try:
        if reverse:
            # تبدیل شمسی به میلادی
            if isinstance(gregorian_date, str):
                # فرض: فرمت ورودی YYYY/MM/DD است
                year, month, day = map(int, gregorian_date.split('/'))
                shamsi = jdatetime.date(year, month, day)
                return shamsi.togregorian()
            return gregorian_date
        else:
            # تبدیل میلادی به شمسی
            if isinstance(gregorian_date, str):
                # فرض: فرمت ورودی YYYY-MM-DD است
                gregorian_date = datetime.datetime.strptime(gregorian_date, '%Y-%m-%d').date()
            
            if hasattr(gregorian_date, 'date'):
                # اگر datetime باشد، فقط date را بگیر
                gregorian_date = gregorian_date.date()
            
            shamsi = jdatetime.date.fromgregorian(date=gregorian_date)
            return shamsi.strftime('%Y/%m/%d')
    except Exception as e:
        return str(gregorian_date)


def shamsi_datetime(gregorian_datetime, reverse=False):
    """
    تبدیل تاریخ و زمان میلادی به شمسی
    
    Args:
        gregorian_datetime: تاریخ و زمان میلادی (string یا datetime)
        reverse: اگر True باشد، تاریخ شمسی را به میلادی تبدیل می‌کند
    
    Returns:
        str: تاریخ و زمان شمسی در فرمت YYYY/MM/DD HH:MM
    """
    if not gregorian_datetime:
        return ""
    
    try:
        if reverse:
            # تبدیل شمسی به میلادی
            if isinstance(gregorian_datetime, str):
                # فرض: فرمت ورودی YYYY/MM/DD HH:MM است
                date_part, time_part = gregorian_datetime.split(' ')
                year, month, day = map(int, date_part.split('/'))
                hour, minute = map(int, time_part.split(':'))
                shamsi = jdatetime.datetime(year, month, day, hour, minute)
                return shamsi.togregorian()
            return gregorian_datetime
        else:
            # تبدیل میلادی به شمسی
            if isinstance(gregorian_datetime, str):
                # فرض: فرمت ورودی YYYY-MM-DD HH:MM:SS است
                gregorian_datetime = datetime.datetime.strptime(gregorian_datetime, '%Y-%m-%d %H:%M:%S')
            
            shamsi = jdatetime.datetime.fromgregorian(datetime=gregorian_datetime)
            return shamsi.strftime('%Y/%m/%d %H:%M')
    except Exception as e:
        return str(gregorian_datetime)


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


def is_license_active():
    """
    بررسی فعال بودن لایسنس سیستم
    """
    from app.models import License
    try:
        license_obj = License.query.first()
        if license_obj and license_obj.is_valid():
            return True
        return False
    except:
        return None


def get_license_info():
    """
    دریافت اطلاعات لایسنس فعال
    """
    from app.models import License
    return License.query.filter_by(is_active=True).first()


def from_json(value):
    """
    تبدیل رشته JSON به دیکشنری
    """
    if not value:
        return None
    try:
        return json.loads(value)
    except:
        return None


def create_database_backup():
    """
    تهیه بک‌آپ از دیتابیس و ثبت آن در مدل BackupFile
    """
    import shutil
    from flask import current_app
    from app import db
    from app.models import BackupFile, AuditLog
    # مسیر ذخیره بک‌آپ
    backup_dir = os.path.join(current_app.root_path, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f'db_backup_{timestamp}.sqlite3'
    filepath = os.path.join(backup_dir, filename)
    # فرض: دیتابیس SQLite است و مسیر آن در config مشخص است
    db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI',
                                     '').replace('sqlite:///', '')
    if not db_path or not os.path.exists(db_path):
        raise Exception('Database file not found!')
    # کپی فایل دیتابیس
    shutil.copy2(db_path, filepath)
    # ثبت در مدل BackupFile
    backup = BackupFile(filename=filename, filepath=filepath)
    db.session.add(backup)
    db.session.commit()
    # ثبت لاگ
    audit = AuditLog()
    audit.user_id = None
    audit.action = 'create_backup'
    audit.description = f'تهیه بک‌آپ دیتابیس: {filename}'
    audit.ip_address = None
    db.session.add(audit)
    db.session.commit()
    return backup


def get_os_name(user_agent):
    if not user_agent:
        return '-'
    if ua_parse:
        ua = ua_parse(user_agent)
        return ua.os.family or '-'
    # روش ساده fallback
    ua = user_agent.lower()
    if 'windows' in ua:
        return 'Windows'
    if 'android' in ua:
        return 'Android'
    if 'iphone' in ua or 'ios' in ua:
        return 'iOS'
    if 'mac' in ua:
        return 'MacOS'
    if 'linux' in ua:
        return 'Linux'
    return '-'


def get_browser_name(user_agent):
    if not user_agent:
        return '-'
    if ua_parse:
        ua = ua_parse(user_agent)
        return ua.browser.family or '-'
    # روش ساده fallback
    ua = user_agent.lower()
    if 'chrome' in ua:
        return 'Chrome'
    if 'firefox' in ua:
        return 'Firefox'
    if 'safari' in ua and 'chrome' not in ua:
        return 'Safari'
    if 'edge' in ua:
        return 'Edge'
    if 'opera' in ua:
        return 'Opera'
    if 'msie' in ua or 'trident' in ua:
        return 'Internet Explorer'
    return '-'


def get_pagination_info(pagination):
    """
    ایجاد اطلاعات pagination برای استفاده در قالب‌ها
    
    Args:
        pagination: شیء pagination از SQLAlchemy
        
    Returns:
        dict: اطلاعات pagination
    """
    return {
        'items': pagination.items,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_num': pagination.prev_num,
        'next_num': pagination.next_num,
        'iter_pages': pagination.iter_pages()
    }


def get_page_from_request(default=1):
    """
    دریافت شماره صفحه از درخواست
    
    Args:
        default (int): شماره صفحه پیش‌فرض
        
    Returns:
        int: شماره صفحه
    """
    try:
        return int(request.args.get('page', default))
    except (ValueError, TypeError):
        return default


def get_per_page_from_request(default=20, max_per_page=100):
    """
    دریافت تعداد آیتم در هر صفحه از درخواست
    
    Args:
        default (int): تعداد پیش‌فرض
        max_per_page (int): حداکثر تعداد مجاز
        
    Returns:
        int: تعداد آیتم در هر صفحه
    """
    try:
        per_page = int(request.args.get('per_page', default))
        return min(per_page, max_per_page)
    except (ValueError, TypeError):
        return default


# ثبت فیلترها برای Jinja
@pass_context
def os_name(ctx, user_agent):
    return get_os_name(user_agent)


@pass_context
def browser_name(ctx, user_agent):
    return get_browser_name(user_agent)


def digits_to_persian(value):
    """
    تبدیل ارقام انگلیسی به فارسی برای نمایش اعداد
    """
    en_to_fa = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return str(value).translate(en_to_fa)

# فیلتر جدید برای فرمت مبلغ

def format_price(value):
    """
    فرمت مبلغ: سه رقم سه رقم با کاما و حذف .0 انتها
    """
    try:
        value = float(value)
        if value.is_integer():
            value = int(value)
            return f"{value:,}"
        else:
            formatted = f"{value:,.2f}"
            if formatted.endswith('.00'):
                formatted = formatted[:-3]
            return formatted
    except Exception:
        return value


def fa_to_en_digits(s):
    if not s:
        return s
    fa = '۰۱۲۳۴۵۶۷۸۹'
    en = '0123456789'
    trans = str.maketrans(fa, en)
    return str(s).translate(trans)


def register_jinja_filters(app):
    app.jinja_env.filters['os_name'] = os_name
    app.jinja_env.filters['browser_name'] = browser_name
    app.jinja_env.filters['format_price'] = format_price
    # ثبت فیلتر to_shamsi حذف شد (در __init__.py ثبت می‌شود)
