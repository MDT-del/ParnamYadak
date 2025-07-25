# ---------------------------------------------
# فایل: security_utils.py
# توضیح: ابزارهای امنیتی پیشرفته برای پروژه
# ---------------------------------------------

import hashlib
import hmac
import secrets
import re
import logging
from functools import wraps
from flask import request, abort, current_app, session
from flask_login import current_user
from werkzeug.utils import secure_filename
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    کلاس اعتبارسنجی امنیتی
    """
    
    # الگوهای امنیتی
    SAFE_FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    PHONE_PATTERN = re.compile(r'^09\d{9}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # فرمت‌های فایل مجاز
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
    
    # حداکثر اندازه فایل‌ها (بایت)
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        بررسی قدرت رمز عبور
        
        Args:
            password: رمز عبور
            
        Returns:
            dict: نتیجه اعتبارسنجی
        """
        result = {
            'is_valid': True,
            'errors': [],
            'score': 0,
            'suggestions': []
        }
        
        if len(password) < 8:
            result['errors'].append('رمز عبور باید حداقل ۸ کاراکتر باشد')
            result['is_valid'] = False
        else:
            result['score'] += 1
            
        if not re.search(r'[A-Z]', password):
            result['errors'].append('رمز عبور باید حداقل یک حرف بزرگ داشته باشد')
            result['suggestions'].append('حروف بزرگ اضافه کنید')
        else:
            result['score'] += 1
            
        if not re.search(r'[a-z]', password):
            result['errors'].append('رمز عبور باید حداقل یک حرف کوچک داشته باشد')
            result['suggestions'].append('حروف کوچک اضافه کنید')
        else:
            result['score'] += 1
            
        if not re.search(r'[0-9]', password):
            result['errors'].append('رمز عبور باید حداقل یک عدد داشته باشد')
            result['suggestions'].append('اعداد اضافه کنید')
        else:
            result['score'] += 1
            
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            result['suggestions'].append('کاراکترهای خاص برای امنیت بیشتر اضافه کنید')
        else:
            result['score'] += 1
            
        # بررسی الگوهای ضعیف
        weak_patterns = [
            r'123456', r'password', r'admin', r'qwerty',
            r'(\w)\1{2,}',  # تکرار کاراکتر
            r'(012|123|234|345|456|567|678|789)',  # دنباله عددی
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password.lower()):
                result['errors'].append('رمز عبور شامل الگوی ضعیف است')
                result['suggestions'].append('از الگوهای قابل حدس اجتناب کنید')
                result['score'] -= 1
                break
                
        if result['errors']:
            result['is_valid'] = False
            
        return result
    
    @staticmethod
    def validate_file_upload(file, file_type: str = 'image') -> Dict[str, Any]:
        """
        اعتبارسنجی فایل آپلود شده
        
        Args:
            file: فایل آپلود شده
            file_type: نوع فایل (image, document)
            
        Returns:
            dict: نتیجه اعتبارسنجی
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not file or not file.filename:
            result['errors'].append('فایل انتخاب نشده است')
            result['is_valid'] = False
            return result
            
        # بررسی نام فایل
        filename = secure_filename(file.filename)
        if not filename:
            result['errors'].append('نام فایل نامعتبر است')
            result['is_valid'] = False
            return result
            
        # بررسی پسوند فایل
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_type == 'image':
            allowed_extensions = SecurityValidator.ALLOWED_IMAGE_EXTENSIONS
            max_size = SecurityValidator.MAX_IMAGE_SIZE
        elif file_type == 'document':
            allowed_extensions = SecurityValidator.ALLOWED_DOCUMENT_EXTENSIONS
            max_size = SecurityValidator.MAX_DOCUMENT_SIZE
        else:
            result['errors'].append('نوع فایل نامعتبر است')
            result['is_valid'] = False
            return result
            
        if file_ext not in allowed_extensions:
            result['errors'].append(f'فرمت فایل مجاز نیست. فرمت‌های مجاز: {", ".join(allowed_extensions)}')
            result['is_valid'] = False
            
        # بررسی اندازه فایل
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > max_size:
            result['errors'].append(f'اندازه فایل بیش از حد مجاز است. حداکثر: {max_size // (1024*1024)}MB')
            result['is_valid'] = False
            
        if file_size == 0:
            result['errors'].append('فایل خالی است')
            result['is_valid'] = False
            
        return result
    
    @staticmethod
    def sanitize_input(input_string: str, max_length: int = 1000) -> str:
        """
        پاک‌سازی ورودی کاربر
        
        Args:
            input_string: رشته ورودی
            max_length: حداکثر طول مجاز
            
        Returns:
            str: رشته پاک‌سازی شده
        """
        if not input_string:
            return ""
            
        # حذف کاراکترهای خطرناک
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r']
        for char in dangerous_chars:
            input_string = input_string.replace(char, '')
            
        # محدود کردن طول
        if len(input_string) > max_length:
            input_string = input_string[:max_length]
            
        return input_string.strip()
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """
        اعتبارسنجی شماره تلفن ایرانی
        """
        return bool(SecurityValidator.PHONE_PATTERN.match(phone))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        اعتبارسنجی ایمیل
        """
        return bool(SecurityValidator.EMAIL_PATTERN.match(email))


class CSRFProtection:
    """
    محافظت پیشرفته در برابر CSRF
    """
    
    @staticmethod
    def generate_csrf_token() -> str:
        """
        تولید توکن CSRF
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_csrf_token(token: str) -> bool:
        """
        اعتبارسنجی توکن CSRF
        """
        session_token = session.get('csrf_token')
        if not session_token or not token:
            return False
            
        return hmac.compare_digest(session_token, token)


class IPSecurityManager:
    """
    مدیریت امنیت IP
    """
    
    # لیست IP های مشکوک (می‌تواند از دیتابیس یا فایل خوانده شود)
    BLOCKED_IPS = set()
    SUSPICIOUS_IPS = set()
    
    @staticmethod
    def is_ip_blocked(ip_address: str) -> bool:
        """
        بررسی مسدود بودن IP
        """
        return ip_address in IPSecurityManager.BLOCKED_IPS
    
    @staticmethod
    def is_ip_suspicious(ip_address: str) -> bool:
        """
        بررسی مشکوک بودن IP
        """
        return ip_address in IPSecurityManager.SUSPICIOUS_IPS
    
    @staticmethod
    def block_ip(ip_address: str, reason: str = "security_violation"):
        """
        مسدود کردن IP
        """
        IPSecurityManager.BLOCKED_IPS.add(ip_address)
        logger.warning(f"IP {ip_address} blocked. Reason: {reason}")
    
    @staticmethod
    def get_client_ip() -> str:
        """
        دریافت IP واقعی کلاینت
        """
        # بررسی هدرهای مختلف برای IP واقعی
        headers_to_check = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Forwarded-Proto',
            'CF-Connecting-IP',  # Cloudflare
        ]
        
        for header in headers_to_check:
            ip = request.headers.get(header)
            if ip:
                # اولین IP در صورت وجود چندین IP
                return ip.split(',')[0].strip()
                
        return request.remote_addr or 'unknown'


def require_ip_whitelist(allowed_ips: List[str]):
    """
    دکوراتور برای محدود کردن دسترسی به IP های خاص
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = IPSecurityManager.get_client_ip()
            
            if client_ip not in allowed_ips:
                logger.warning(f"Unauthorized IP access attempt: {client_ip}")
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def block_suspicious_requests(f):
    """
    دکوراتور برای مسدود کردن درخواست‌های مشکوک
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = IPSecurityManager.get_client_ip()
        
        # بررسی IP مسدود شده
        if IPSecurityManager.is_ip_blocked(client_ip):
            logger.warning(f"Blocked IP access attempt: {client_ip}")
            abort(403)
            
        # بررسی User-Agent مشکوک
        user_agent = request.headers.get('User-Agent', '').lower()
        suspicious_agents = ['bot', 'crawler', 'spider', 'scraper']
        
        if any(agent in user_agent for agent in suspicious_agents):
            logger.warning(f"Suspicious User-Agent from {client_ip}: {user_agent}")
            # می‌توان IP را مشکوک علامت‌گذاری کرد
            IPSecurityManager.SUSPICIOUS_IPS.add(client_ip)
            
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_by_ip(max_requests: int = 100, window_minutes: int = 60):
    """
    دکوراتور برای محدود کردن تعداد درخواست بر اساس IP
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # این قسمت می‌تواند با Redis یا دیتابیس پیاده‌سازی شود
            # فعلاً فقط ساختار را نشان می‌دهیم
            client_ip = IPSecurityManager.get_client_ip()
            
            # بررسی تعداد درخواست‌ها (باید با Redis پیاده‌سازی شود)
            # if check_rate_limit(client_ip, max_requests, window_minutes):
            #     abort(429)  # Too Many Requests
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


class SecurityHeaders:
    """
    مدیریت هدرهای امنیتی
    """
    
    @staticmethod
    def add_security_headers(response):
        """
        اضافه کردن هدرهای امنیتی به پاسخ
        """
        # جلوگیری از clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # جلوگیری از MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # فعال‌سازی XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


def init_security_utils(app):
    """
    راه‌اندا��ی ابزارهای امنیتی در اپلیکیشن
    """
    
    @app.after_request
    def add_security_headers(response):
        return SecurityHeaders.add_security_headers(response)
    
    @app.before_request
    def security_checks():
        """
        بررسی‌های امنیتی قبل از هر درخواست
        """
        client_ip = IPSecurityManager.get_client_ip()
        
        # بررسی IP مسدود شده
        if IPSecurityManager.is_ip_blocked(client_ip):
            logger.warning(f"Blocked IP access attempt: {client_ip}")
            abort(403)
            
        # بررسی اندازه درخواست
        if request.content_length and request.content_length > app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024):
            logger.warning(f"Large request from {client_ip}: {request.content_length} bytes")
            abort(413)  # Request Entity Too Large
    
    logger.info("Security utilities initialized")