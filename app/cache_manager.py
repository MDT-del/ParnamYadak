# ---------------------------------------------
# فایل: cache_manager.py
# توضیح: مدیریت کش با Redis برای بهبود عملکرد سیستم
# ---------------------------------------------

import json
import pickle
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import current_app, request, render_template_string
import redis
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    کلاس مدیریت کش با Redis
    """
    
    def __init__(self, app=None):
        self.redis_client = None
        self.default_timeout = 3600  # 1 ساعت
        self.prefix = "pernamyadak:"
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        راه‌اندازی اتصال Redis
        """
        try:
            redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # تست اتصال
            self.redis_client.ping()
            logger.info("اتصال Redis با موفقیت برقرار شد")
            
        except Exception as e:
            logger.error(f"خطا در اتصال به Redis: {e}")
            self.redis_client = None
    
    def _get_key(self, key):
        """
        تولید کلید کامل با پیشوند
        """
        return f"{self.prefix}{key}"
    
    def set(self, key, value, timeout=None):
        """
        ذخیره مقدار در کش
        
        Args:
            key (str): کلید
            value: مقدار (قابل تبدیل به JSON)
            timeout (int): زمان انقضا (ثانیه)
        """
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_key(key)
            timeout = timeout or self.default_timeout
            
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)
            
            self.redis_client.setex(full_key, timeout, serialized_value)
            logger.debug(f"مقدار در کش ذخیره شد: {key}")
            return True
            
        except Exception as e:
            logger.error(f"خطا در ذخیره کش {key}: {e}")
            return False
    
    def get(self, key, default=None):
        """
        دریافت مقدار از کش
        
        Args:
            key (str): کلید
            default: مقدار پیش‌فرض در صورت عدم وجود
        
        Returns:
            مقدار ذخیره شده یا default
        """
        if not self.redis_client:
            return default
        
        try:
            full_key = self._get_key(key)
            value = self.redis_client.get(full_key)
            
            if value is None:
                return default
            
            # تلاش برای تبدیل به JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
                
        except Exception as e:
            logger.error(f"خطا در دریافت کش {key}: {e}")
            return default
    
    def delete(self, key):
        """
        حذف مقدار از کش
        
        Args:
            key (str): کلید
        """
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_key(key)
            result = self.redis_client.delete(full_key)
            logger.debug(f"مقدار از کش حذف شد: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"خطا در حذف کش {key}: {e}")
            return False
    
    def exists(self, key):
        """
        بررسی وجود کلید در کش
        
        Args:
            key (str): کلید
        
        Returns:
            bool: True اگر وجود دارد
        """
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_key(key)
            return self.redis_client.exists(full_key) > 0
            
        except Exception as e:
            logger.error(f"خطا در بررسی وجود کش {key}: {e}")
            return False
    
    def expire(self, key, timeout):
        """
        تنظیم زمان انقضا برای کلید
        
        Args:
            key (str): کلید
            timeout (int): زمان انقضا (ثانیه)
        """
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_key(key)
            return self.redis_client.expire(full_key, timeout)
            
        except Exception as e:
            logger.error(f"خطا در تنظیم انقضای کش {key}: {e}")
            return False
    
    def clear_pattern(self, pattern):
        """
        حذف تمام کلیدهای مطابق با الگو
        
        Args:
            pattern (str): الگوی کلیدها
        """
        if not self.redis_client:
            return False
        
        try:
            full_pattern = self._get_key(pattern)
            keys = self.redis_client.keys(full_pattern)
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"{deleted} کلید با الگوی {pattern} حذف شد")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"خطا در حذف الگوی کش {pattern}: {e}")
            return False
    
    def get_stats(self):
        """
        دریافت آمار کش
        
        Returns:
            dict: آمار کش
        """
        if not self.redis_client:
            return {}
        
        try:
            info = self.redis_client.info()
            return {
                'total_keys': info.get('db0', {}).get('keys', 0),
                'memory_usage': info.get('used_memory_human', '0B'),
                'connected_clients': info.get('connected_clients', 0),
                'uptime': info.get('uptime_in_seconds', 0)
            }
            
        except Exception as e:
            logger.error(f"خطا در دریافت آمار کش: {e}")
            return {}


# نمونه سراسری
cache_manager = CacheManager()


# دکوراتور برای کش کردن توابع
def cached(timeout=None, key_prefix=None):
    """
    دکوراتور برای کش کردن نتایج توابع
    
    Args:
        timeout (int): زمان انقضا (ثانیه)
        key_prefix (str): پیشوند کلید
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # تولید کلید کش
            if key_prefix:
                cache_key = f"{key_prefix}:{func.__name__}"
            else:
                # تولید کلید بر اساس نام تابع و آرگومان‌ها
                key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # تلاش برای دریافت از کش
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"نتیجه از کش دریافت شد: {cache_key}")
                return cached_result
            
            # اجرای تابع و ذخیره در کش
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, timeout)
            logger.debug(f"نتیجه در کش ذخیره شد: {cache_key}")
            
            return result
        return wrapper
    return decorator


# کلاس‌های کش برای بخش‌های مختلف سیستم
class ProductCache:
    """کش محصولات"""
    
    @staticmethod
    def get_product_key(product_id):
        return f"product:{product_id}"
    
    @staticmethod
    def get_products_list_key(page=1, category_id=None, search=None):
        params = f"page:{page}"
        if category_id:
            params += f":cat:{category_id}"
        if search:
            params += f":search:{search}"
        return f"products_list:{params}"
    
    @staticmethod
    def cache_product(product):
        """کش کردن محصول"""
        if product:
            cache_manager.set(
                ProductCache.get_product_key(product.id),
                product.to_dict(),
                timeout=1800  # 30 دقیقه
            )
    
    @staticmethod
    def get_cached_product(product_id):
        """دریافت محصول از کش"""
        return cache_manager.get(ProductCache.get_product_key(product_id))
    
    @staticmethod
    def invalidate_product(product_id):
        """باطل کردن کش محصول"""
        cache_manager.delete(ProductCache.get_product_key(product_id))
        # باطل کردن لیست محصولات
        cache_manager.clear_pattern("products_list:*")


class CustomerCache:
    """کش مشتریان"""
    
    @staticmethod
    def get_customer_key(customer_id):
        return f"customer:{customer_id}"
    
    @staticmethod
    def get_customer_by_phone_key(phone):
        return f"customer_phone:{phone}"
    
    @staticmethod
    def cache_customer(customer):
        """کش کردن مشتری"""
        if customer:
            cache_manager.set(
                CustomerCache.get_customer_key(customer.id),
                customer.to_dict(),
                timeout=3600  # 1 ساعت
            )
            # کش کردن بر اساس شماره تلفن
            if customer.phone_number:
                cache_manager.set(
                    CustomerCache.get_customer_by_phone_key(customer.phone_number),
                    customer.id,
                    timeout=3600
                )
    
    @staticmethod
    def get_cached_customer(customer_id):
        """دریافت مشتری از کش"""
        return cache_manager.get(CustomerCache.get_customer_key(customer_id))
    
    @staticmethod
    def get_customer_id_by_phone(phone):
        """دریافت شناسه مشتری بر اساس شماره تلفن"""
        return cache_manager.get(CustomerCache.get_customer_by_phone_key(phone))
    
    @staticmethod
    def invalidate_customer(customer_id, phone=None):
        """باطل کردن کش مشتری"""
        cache_manager.delete(CustomerCache.get_customer_key(customer_id))
        if phone:
            cache_manager.delete(CustomerCache.get_customer_by_phone_key(phone))


class OrderCache:
    """کش سفارشات"""
    
    @staticmethod
    def get_order_key(order_id):
        return f"order:{order_id}"
    
    @staticmethod
    def get_orders_list_key(page=1, status=None, customer_id=None):
        params = f"page:{page}"
        if status:
            params += f":status:{status}"
        if customer_id:
            params += f":customer:{customer_id}"
        return f"orders_list:{params}"
    
    @staticmethod
    def cache_order(order):
        """کش کردن سفارش"""
        if order:
            cache_manager.set(
                OrderCache.get_order_key(order.id),
                order.to_dict(),
                timeout=1800  # 30 دقیقه
            )
    
    @staticmethod
    def get_cached_order(order_id):
        """دریافت سفارش از کش"""
        return cache_manager.get(OrderCache.get_order_key(order_id))
    
    @staticmethod
    def invalidate_order(order_id):
        """باطل کردن کش سفارش"""
        cache_manager.delete(OrderCache.get_order_key(order_id))
        # باطل کردن لیست سفارشات
        cache_manager.clear_pattern("orders_list:*")


class DashboardCache:
    """کش داشبورد"""
    
    @staticmethod
    def get_stats_key(period='today'):
        return f"dashboard_stats:{period}"
    
    @staticmethod
    def get_recent_activities_key():
        return f"dashboard_activities:recent"
    
    @staticmethod
    def cache_dashboard_stats(stats, period='today'):
        """کش کردن آمار داشبورد"""
        cache_manager.set(
            DashboardCache.get_stats_key(period),
            stats,
            timeout=300  # 5 دقیقه
        )
    
    @staticmethod
    def get_cached_stats(period='today'):
        """دریافت آمار از کش"""
        return cache_manager.get(DashboardCache.get_stats_key(period))
    
    @staticmethod
    def cache_recent_activities(activities):
        """کش کردن فعالیت‌های اخیر"""
        cache_manager.set(
            DashboardCache.get_recent_activities_key(),
            activities,
            timeout=600  # 10 دقیقه
        )
    
    @staticmethod
    def get_cached_activities():
        """دریافت فعالیت‌های اخیر از کش"""
        return cache_manager.get(DashboardCache.get_recent_activities_key())
    
    @staticmethod
    def invalidate_dashboard():
        """باطل کردن کش داشبورد"""
        cache_manager.clear_pattern("dashboard_stats:*")
        cache_manager.clear_pattern("dashboard_activities:*")


# کلاس‌های جدید برای کش کردن کوئری‌های پرکاربرد
class QueryCache:
    """کش کوئری‌های پرکاربرد"""
    
    @staticmethod
    def get_analytics_key(analytics_type, params=None):
        """تولید کلید برای کش تحلیل‌ها"""
        key = f"analytics:{analytics_type}"
        if params:
            key += f":{hashlib.md5(str(params).encode()).hexdigest()}"
        return key
    
    @staticmethod
    def cache_product_analytics(data, timeout=1800):
        """کش کردن تحلیل محصولات"""
        cache_manager.set(
            QueryCache.get_analytics_key('products'),
            data,
            timeout=timeout
        )
    
    @staticmethod
    def get_cached_product_analytics():
        """دریافت تحلیل محصولات از کش"""
        return cache_manager.get(QueryCache.get_analytics_key('products'))
    
    @staticmethod
    def cache_customer_analytics(data, timeout=1800):
        """کش کردن تحلیل مشتریان"""
        cache_manager.set(
            QueryCache.get_analytics_key('customers'),
            data,
            timeout=timeout
        )
    
    @staticmethod
    def get_cached_customer_analytics():
        """دریافت تحلیل مشتریان از کش"""
        return cache_manager.get(QueryCache.get_analytics_key('customers'))
    
    @staticmethod
    def cache_sales_report(data, start_date=None, end_date=None, timeout=3600):
        """کش کردن گزارش فروش"""
        params = {'start': start_date, 'end': end_date}
        cache_manager.set(
            QueryCache.get_analytics_key('sales', params),
            data,
            timeout=timeout
        )
    
    @staticmethod
    def get_cached_sales_report(start_date=None, end_date=None):
        """دریافت گزارش فروش از کش"""
        params = {'start': start_date, 'end': end_date}
        return cache_manager.get(QueryCache.get_analytics_key('sales', params))
    
    @staticmethod
    def invalidate_analytics():
        """باطل کردن تمام کش تحلیل‌ها"""
        cache_manager.clear_pattern("analytics:*")


class StaticPageCache:
    """کش صفحات استاتیک"""
    
    @staticmethod
    def get_page_key(page_name, params=None):
        """تولید کلید برای کش صفحات"""
        key = f"page:{page_name}"
        if params:
            key += f":{hashlib.md5(str(params).encode()).hexdigest()}"
        return key
    
    @staticmethod
    def cache_page(page_name, content, params=None, timeout=3600):
        """کش کردن محتوای صفحه"""
        cache_manager.set(
            StaticPageCache.get_page_key(page_name, params),
            content,
            timeout=timeout
        )
    
    @staticmethod
    def get_cached_page(page_name, params=None):
        """دریافت محتوای صفحه از کش"""
        return cache_manager.get(StaticPageCache.get_page_key(page_name, params))
    
    @staticmethod
    def cache_dashboard_page(content, user_id=None, timeout=300):
        """کش کردن صفحه داشبورد"""
        params = {'user_id': user_id} if user_id else None
        StaticPageCache.cache_page('dashboard', content, params, timeout)
    
    @staticmethod
    def get_cached_dashboard_page(user_id=None):
        """دریافت صفحه داشبورد از کش"""
        params = {'user_id': user_id} if user_id else None
        return StaticPageCache.get_cached_page('dashboard', params)
    
    @staticmethod
    def cache_products_page(content, page=1, category_id=None, search=None, timeout=1800):
        """کش کردن صفحه محصولات"""
        params = {
            'page': page,
            'category_id': category_id,
            'search': search
        }
        StaticPageCache.cache_page('products', content, params, timeout)
    
    @staticmethod
    def get_cached_products_page(page=1, category_id=None, search=None):
        """دریافت صفحه محصولات از کش"""
        params = {
            'page': page,
            'category_id': category_id,
            'search': search
        }
        return StaticPageCache.get_cached_page('products', params)
    
    @staticmethod
    def invalidate_page(page_name):
        """باطل کردن کش صفحه خاص"""
        cache_manager.clear_pattern(f"page:{page_name}:*")
    
    @staticmethod
    def invalidate_all_pages():
        """باطل کردن تمام کش صفحات"""
        cache_manager.clear_pattern("page:*")


# توابع کمکی برای کش کردن
def cache_query_result(query_func, cache_key, timeout=1800):
    """
    کش کردن نتیجه کوئری
    
    Args:
        query_func: تابع کوئری
        cache_key: کلید کش
        timeout: زمان انقضا
    """
    # تلاش برای دریافت از کش
    cached_result = cache_manager.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # اجرای کوئری و ذخیره در کش
    result = query_func()
    cache_manager.set(cache_key, result, timeout)
    return result


def cache_template(template_name, context=None, timeout=1800):
    """
    کش کردن قالب HTML
    
    Args:
        template_name: نام قالب
        context: متغیرهای قالب
        timeout: زمان انقضا
    """
    if context is None:
        context = {}
    
    # تولید کلید کش
    context_str = json.dumps(context, sort_keys=True)
    cache_key = f"template:{template_name}:{hashlib.md5(context_str.encode()).hexdigest()}"
    
    # تلاش برای دریافت از کش
    cached_content = cache_manager.get(cache_key)
    if cached_content is not None:
        return cached_content
    
    # رندر کردن قالب و ذخیره در کش
    try:
        from flask import render_template
        content = render_template(template_name, **context)
        cache_manager.set(cache_key, content, timeout)
        return content
    except Exception as e:
        logger.error(f"خطا در رندر کردن قالب {template_name}: {e}")
        return None


# توابع کمکی
def clear_all_cache():
    """پاک کردن تمام کش"""
    if cache_manager.redis_client:
        cache_manager.redis_client.flushdb()
        logger.info("تمام کش پاک شد")


def get_cache_info():
    """دریافت اطلاعات کش"""
    return cache_manager.get_stats()


def cache_function_result(func_name, *args, **kwargs):
    """
    کش کردن نتیجه تابع با کلید سفارشی
    
    Args:
        func_name (str): نام تابع
        *args: آرگومان‌های تابع
        **kwargs: آرگومان‌های کلیدی تابع
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*func_args, **func_kwargs):
            # تولید کلید کش
            key_data = f"{func_name}:{str(func_args)}:{str(sorted(func_kwargs.items()))}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # تلاش برای دریافت از کش
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # اجرای تابع و ذخیره در کش
            result = func(*func_args, **func_kwargs)
            cache_manager.set(cache_key, result, timeout=1800)  # 30 دقیقه
            
            return result
        return wrapper
    return decorator 