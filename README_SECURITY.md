# 🔐 راهنمای امنیت پروژه پرنام یدک

## 📋 خلاصه تغییرات امنیتی

این مستند تغییرات امنیتی اعمال شده بر روی پروژه پرنام یدک را شرح می‌دهد.

---

## ✅ مشکلات برطرف شده

### 1. **مدیریت SECRET_KEY بهبود یافته**

#### ❌ مشکل قبلی:
```python
SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
```

#### ✅ راه‌حل جدید:
- تابع `get_secure_secret_key()` در `config.py`
- هشدار امنیتی در صورت عدم تنظیم متغیر محیطی
- تولید کلید 512 بیتی (64 بایت) به جای 256 بیت
- ذخیره کلید در فایل موقت برای consistency در development

```python
def get_secure_secret_key():
    secret_key = os.environ.get('SECRET_KEY')
    
    if not secret_key:
        warnings.warn("SECRET_KEY environment variable is not set!")
        secret_key = secrets.token_urlsafe(64)  # 512 بیت
        # ذخیره در فایل موقت
```

### 2. **تنظیمات CSRF پیشرفته**

#### ✅ بهبودهای اعمال شده:
```python
# تنظیمات CSRF قوی‌تر
WTF_CSRF_TIME_LIMIT = 1800  # 30 دقیقه (کاهش از 1 ساعت)
WTF_CSRF_ENABLED = True
WTF_CSRF_SSL_STRICT = True
WTF_CSRF_CHECK_DEFAULT = True
WTF_CSRF_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
```

### 3. **مدیریت Session پیشرفته**

#### ❌ مشکل قبلی:
- کد پیچیده و غیرقابل نگهداری در `__init__.py`
- عدم مدیریت صحیح timeout
- نبود پاک‌سازی خودکار session های منقضی

#### ✅ راه‌حل جدید: `SessionManager`

**فایل جدید:** `app/session_manager.py`

**ویژگی‌های کلیدی:**
- کلاس `SessionManager` برای مدیریت مرکزی
- timeout های قابل تنظیم
- پاک‌سازی خودکار session های منقضی
- مدیریت چندین session همزمان
- لاگ‌گیری دقیق

```python
class SessionManager:
    DEFAULT_SESSION_TIMEOUT = 1800  # 30 دقیقه
    MAX_INACTIVE_TIME = 900  # 15 دقیقه بی‌فعالیتی
    
    @staticmethod
    def create_session(user, ip_address=None, user_agent=None, device_id=None):
        # ایجاد session امن
    
    @staticmethod
    def is_session_valid(session_id=None):
        # بررسی اعتبار session
    
    @staticmethod
    def cleanup_expired_sessions():
        # پاک‌سازی خودکار
```

---

## 🛡️ ماژول‌های امنیتی جدید

### 1. **SecurityValidator**

**فایل:** `app/security_utils.py`

**قابلیت‌ها:**
- اعتبارسنجی قدرت رمز عبور
- اعتبارسنجی فایل‌های آپلود شده
- پاک‌سازی ورودی کاربر
- اعتبارسنجی شماره تلفن و ایمیل

```python
# مثال استفاده
result = SecurityValidator.validate_password_strength("MyPassword123")
if result['is_valid']:
    # رمز عبور قوی است
```

### 2. **CSRFProtection**

**قابلیت‌ها:**
- تولید توکن CSRF امن
- اعتبارسنجی توکن با `hmac.compare_digest`

### 3. **IPSecurityManager**

**قابلیت‌ها:**
- مدیریت IP های مسدود شده
- شناسایی IP های مشکوک
- دریافت IP واقعی کلاینت (پشت proxy/CDN)

### 4. **SecurityHeaders**

**هدرهای امنیتی اضافه شده:**
```http
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

---

## 🔧 تنظیمات امنیتی بهبود یافته

### 1. **Content Security Policy (CSP)**

```python
csp = {
    'default-src': "'self'",
    'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
    'style-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
    'font-src': "'self' https://fonts.gstatic.com",
    'img-src': "'self' data: https:",
    'connect-src': "'self'",
}
```

### 2. **Session Security**

```python
# تنظیمات امنیتی Session
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # 'Strict' در production
SESSION_PERMANENT = False
PERMANENT_SESSION_LIFETIME = 1800  # 30 دقیقه
```

### 3. **File Upload Security**

```python
# محدودیت اندازه فایل
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# فرمت‌های مجاز
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
```

---

## 📝 فایل .env.example بهبود یافته

**فایل جدید:** `.env.example`

**شامل:**
- راهنمای کامل تنظیمات امنیتی
- نکات امنیتی مهم
- تنظیمات production و development

**نکات کلیدی:**
```bash
# کلید امنیتی قوی (حداقل 64 کاراکتر)
SECRET_KEY=your-super-secret-key-here-minimum-64-characters

# فعال‌سازی HTTPS برای کوکی‌ها
SESSION_COOKIE_SECURE=true  # فقط در production

# کلید امنیتی لایسنس
LICENSE_SECRET_KEY=your-license-secret-key-here
```

---

## 🚀 نحوه استفاده

### 1. **تنظیم متغیرهای محیطی**

```bash
# کپی فایل نمونه
cp .env.example .env

# ویرایش فایل .env
nano .env
```

### 2. **تنظیم SECRET_KEY قوی**

```bash
# تولید کلید امنیتی قوی
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3. **فعال‌سازی HTTPS در Production**

```bash
SESSION_COOKIE_SECURE=true
WTF_CSRF_SSL_STRICT=true
```

---

## ⚠️ نکات مهم امنیتی

### 1. **برای Production:**
- حتماً `SECRET_KEY` قوی تنظیم کنید
- `SESSION_COOKIE_SECURE=true` قرار دهید
- از HTTPS استفاده کنید
- دیتابیس قوی‌تر از SQLite استفاده کنید

### 2. **مانیتورینگ:**
- لاگ‌های امنیتی را بررسی کنید
- IP های مشکوک را پیگیری کنید
- session های غیرعادی را بررسی کنید

### 3. **ب��‌آپ:**
- بک‌آپ منظم از دیتابیس
- بک‌آپ از فایل‌های تنظیمات
- تست بازیابی

---

## 📊 بهبودهای عملکرد

### 1. **Session Management:**
- کاهش overhead بررسی session
- پاک‌سازی خودکار session های منقضی
- بهینه‌سازی کوئری‌های دیتابیس

### 2. **Security Checks:**
- بررسی‌های امنیتی بهینه شده
- کش کردن نتایج بررسی IP
- کاهش تعداد کوئری‌های دیتابیس

---

## 🔍 تست امنیت

### 1. **تست Session:**
```python
# تست timeout session
# تست concurrent sessions
# تست cleanup
```

### 2. **تست CSRF:**
```python
# تست توکن CSRF
# تست انقضای توکن
```

### 3. **تست File Upload:**
```python
# تست فرمت‌های مختلف فایل
# تست اندازه فایل
# تست فایل‌های مخرب
```

---

## 📚 منابع اضافی

- [OWASP Security Guidelines](https://owasp.org/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Security Guidelines](https://python.org/dev/security/)

---

## 🆔 نسخه

**نسخه:** 2.0.0
**تاریخ:** 2024
**وضعیت:** فعال و آماده استفاده

---

**نکته:** این تغییرات امنیتی باعث بهبود قابل توجه امنیت پروژه شده‌اند. برای اطمینان کامل، توصیه می‌شود تست‌های امنیتی جامع انجام دهید.