# 🚗 پنل مدیریت پرنام یدک

**سیستم جامع مدیریت کسب‌وکار قطعات یدکی و خدمات خودرویی**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-Custom-red.svg)](#)

---

## 📋 فهرست مطالب

- [ویژگی‌های کلیدی](#-ویژگیهای-کلیدی)
- [قابلیت‌های سیستم](#-قابلیتهای-سیستم)
- [ساختار پروژه](#️-ساختار-پروژه)
- [راه‌اندازی سریع](#-راهاندازی-سریع)
- [مدیریت کاربران](#-مدیریت-کاربران)
- [امنیت و پایداری](#-امنیت-و-پایداری)
- [API و مستندات](#-api-و-مستندات)
- [تست و کیفیت](#-تست-و-کیفیت)
- [مشخصات طراح](#-مشخصات-طراح)

---

## ⭐ ویژگی‌های کلیدی

### 🏗️ **معماری مدرن و مقیاس‌پذیر**
- **Flask Blueprints** برای جداسازی کامل ماژول‌ها
- **PostgreSQL** برای ذخیره‌سازی قدرتمند داده‌ها
- **Redis** برای کش و بهبود عملکرد
- **Docker** برای استقرار آسان و سازگار

### 🔒 **امنیت پیشرفته**
- **Role-Based Access Control (RBAC)** با 17 مجوز مختلف
- **Session Management** پیشرفته با timeout خودکار
- **CSRF Protection** و **Security Headers**
- **Rate Limiting** برای جلوگیری از حملات
- **Input Validation** و **SQL Injection Prevention**

### 🚀 **عملکرد بهینه**
- **Query Optimization** با eager loading
- **Database Indexing** برای جستجوی سریع
- **Image Optimization** برای تصاویر محصولات
- **Caching Strategy** با Redis
- **Pagination** برای لیست‌های بزرگ

### 📱 **ربات تلگرام یکپارچه**
- **ارتباط مستقیم** با پنل مدیریت
- **مدیریت سفارشات** از طریق ربات
- **اعلان‌های Real-time** به مدیران
- **منوی تعاملی** برای مشتریان

### 📊 **گزارش‌گیری پیشرفته**
- **داشبورد تحلیلی** با نمودارهای زنده
- **گزارش‌های مالی** تفصیلی
- **آمار فروش** و **موجودی انبار**
- **تحلیل رفتار مشتریان**

---

## 🏗️ ساختار پروژه

```
ParnamYadak/
├── app/
│   ├── blueprints/      # ماژول‌های اصلی (auth, orders, products, ... , telegram_bot)
│   ├── models.py        # مدل‌های دیتابیس
│   ├── forms.py         # فرم‌ها و اعتبارسنجی
│   ├── static/          # فایل‌های استاتیک (css, js, images)
│   └── templates/       # قالب‌های Jinja2
├── docs/                # مستندات (API, Deployment, Developer Guide)
├── requirements.txt     # وابستگی‌های پایتون
├── docker-compose.yml   # استقرار سریع با Docker
├── Dockerfile           # ساخت image داکر
└── ...
```

---

## 🚀 راه‌اندازی سریع

### با Docker (پیشنهادی)

1. **تنظیم متغیرهای محیطی:**
   - فایل `env_example` را کپی و مقادیر را تنظیم کنید:
     ```bash
     cp env_example .env
     nano .env
     ```

2. **Build و اجرای سرویس‌ها:**
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

3. **دسترسی به پنل:**
   - آدرس: `https://<دامنه-شما>/`
   - health check: `https://<دامنه-شما>/health`

### نصب دستی (بدون Docker)

راهنمای کامل در [docs/deployment.md](docs/deployment.md) موجود است.

---

## 🔒 امنیت و پایداری

- **HTTPS و SSL:**  
  پشتیبانی کامل از گواهینامه SSL و سازگاری با کلودفلر
- **Rate Limiting و Session Management**
- **پشتیبانی از Sentry و لاگ‌گیری حرفه‌ای**
- **Health Check Endpoint**

---

## 📚 مستندات و توسعه

- [مستندات API](docs/api.md)
- [راهنمای استقرار](docs/deployment.md)
- [راهنمای توسعه‌دهندگان](docs/developer_guide.md)

---

## 🧩 قابلیت‌های ماژولار

- مدیریت کاربران و نقش‌ها
- مدیریت سفارشات و محصولات
- گزارش‌های مالی و تراکنش‌ها
- سیستم اعلان و نوتیفیکیشن
- ربات تلگرام متصل به پنل
- پشتیبانی از کش Redis و بهینه‌سازی کوئری‌ها
- مدیریت فایل و تصویر با ابزارهای اختصاصی

---

## 🧪 تست و کیفیت

- تست‌های واحد و یکپارچه با pytest
- پوشش تست بالا
- استانداردهای کدنویسی و کامیت

---

## 💡 توسعه و همکاری

- ساختار کد تمیز و قابل توسعه
- مستندسازی کامل برای توسعه‌دهندگان
- پذیرای Pull Request و Issueهای جدید

---

## 📝 نمونه متغیرهای محیطی

```env
SECRET_KEY=your-super-secret-key
DATABASE_URL=postgresql://user:pass@db:5432/parnamyadak
REDIS_URL=redis://redis:6379/0
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
PANEL_API_BASE_URL=https://panel.parnamyadak.ir
LOG_LEVEL=WARNING
...
```

---

## 📈 نقاط قوت ویژه

- **امنیت و مقیاس‌پذیری بالا**
- **پشتیبانی از DevOps و استقرار سریع**
- **مستندسازی کامل و توسعه‌پذیری عالی**
- **پشتیبانی از ربات تلگرام و API مدرن**
- **بهینه‌سازی عملکرد و کش**
- **مانیتورینگ و health check داخلی**

---

## 🎯 قابلیت‌های کامل سیستم

### 👥 **مدیریت کاربران و دسترسی‌ها**
- **سیستم نقش‌محور (RBAC)** با 5 نقش پیش‌فرض:
  - 👑 **Admin** - دسترسی کامل (17 مجوز)
  - 👔 **Manager** - مدیر (11 مجوز)
  - 👤 **Employee** - کارمند (5 مجوز)
  - 🎧 **Support** - پشتیبانی (6 مجوز)
  - 👁️ **Viewer** - بازدیدکننده (5 مجوز)
- **17 مجوز مختلف** برای کنترل دقیق دسترسی‌ها
- **مدیریت session** با timeout خودکار
- **لاگ فعالیت‌ها** برای audit trail
- **ویرایش و حذف کاربران** با کنترل امنیت

### 🛒 **مدیریت محصولات و موجودی**
- **دسته‌بندی محصولات** با ساختار درختی
- **مدیریت تصاویر** با بهینه‌سازی خودکار
- **ردیابی موجودی** Real-time با سیستم batch
- **قیمت‌گذاری پیشرفته** با تخفیف‌ها
- **جستجوی پیشرفته** در محصولات
- **مدیریت انبار** با تاریخچه تغییرات

### 📋 **مدیریت سفارشات**
- **سفارشات تلگرام** از طریق ربات یکپارچه
- **سفارشات حضوری** در فروشگاه
- **سفارشات ربات** با API اختصاصی
- **پیش‌سفارش** برای محصولات ناموجود
- **ردیابی وضعیت** سفارش در تمام مراحل
- **مدیریت batch** برای کنترل موجودی FIFO

### 👤 **مدیریت مشتریان**
- **پروفایل کامل مشتریان** با تاریخچه خرید
- **سطح‌بندی مشتریان** بر اساس میزان خرید
- **آدرس‌های متعدد** برای هر مشتری
- **ویرایش و حذف مشتریان** با کنترل امنیت
- **جستجوی پیشرفته** در مشتریان
- **تحلیل رفتار خرید** مشتریان

### 💰 **مدیریت مالی**
- **گزارش‌های فروش** تفصیلی و تحلیلی
- **تحلیل سود و زیان** ماهانه/سالانه
- **مدیریت تراکنش‌های مالی** کامل
- **فاکتورسازی خودکار** با شماره‌گذاری
- **گزارش‌های مالی** قابل export
- **تحلیل روندهای فروش**

### 🔧 **مدیریت تعمیرکاران**
- **ثبت‌نام تعمیرکاران** با فرآیند تایید
- **مدیریت مجوزها** و مدارک فنی
- **سیستم امتیازدهی** بر اساس عملکرد
- **تخصیص کار** و پروژه‌ها
- **پروفایل تخصصی** هر تعمیرکار
- **ردیابی فعالیت‌ها** و کارکرد

### 📢 **سیستم اعلان‌ها و پیام‌رسانی**
- **پیام‌های همگانی** به گروه‌های مختلف
- **اعلان‌های شخصی‌سازی شده** بر اساس سگمنت
- **ارسال از طریق تلگرام** و پنل
- **قالب‌بندی پیام‌ها** با HTML
- **برنامه‌ریزی ارسال** پیام‌ها
- **گزارش تحویل** پیام‌ها
- **سیستم اعلان محلی** بدون نیاز به SocketIO

### 🎫 **مدیریت پشتیبانی**
- **سیستم تیکت‌ها** برای پشتیبانی مشتریان
- **دسته‌بندی مشکلات** و اولویت‌بندی
- **تخصیص به کارشناسان** مختلف
- **پیگیری وضعیت** و تاریخچه تیکت‌ها
- **پاسخ‌های آماده** برای مشکلات رایج
- **ارزیابی کیفیت** پشتیبانی

### 📊 **داشبورد و گزارش‌گیری**
- **داشبورد تحلیلی** با نمودارهای زنده
- **آمار فروش** Real-time
- **تحلیل موجودی انبار** و پیش‌بینی
- **گزارش‌های قابل تنظیم** و export
- **نمودارهای تعاملی** با Chart.js
- **KPI های کلیدی** کسب‌وکار

---

## 🛠️ تکنولوژی‌ها و ابزارها

### **Backend**
- **Flask 2.3+** - فریمورک وب سبک و قدرتمند
- **SQLAlchemy** - ORM پیشرفته برای مدیریت دیتابیس
- **Flask-Migrate** - مدیریت migration های دیتابیس
- **Flask-Login** - مدیریت احراز هویت کاربران
- **Flask-WTF** - مدیریت فرم‌ها و CSRF protection
- **Flask-Limiter** - Rate limiting برای امنیت API

### **Database**
- **PostgreSQL 13+** - دیتابیس اصلی (پیشنهادی)
- **MySQL 8+** - پشتیبانی کامل (جایگزین)
- **Redis** - کش و session storage

### **Frontend**
- **Jinja2** - موتور template
- **Tailwind CSS** - فریمورک CSS مدرن
- **Alpine.js** - JavaScript reactive framework
- **Chart.js** - نمودارها و گراف‌ها

### **DevOps & Deployment**
- **Docker & Docker Compose** - کانتینرسازی
- **Gunicorn** - WSGI server برای production
- **Nginx** - Reverse proxy و static files
- **Supervisor** - Process management

---

## 🔐 امنیت پیشرفته

### **مدیریت Session**
- **SessionManager** کلاس برای مدیریت مرکزی
- **Timeout خودکار** (30 دقیقه)
- **پاک‌سازی خودکار** session های منقضی
- **مدیریت چندین session** همزمان

### **CSRF Protection**
- **تنظیمات CSRF قوی‌تر** با timeout 30 دقیقه
- **SSL Strict mode** برای production
- **اعتبارسنجی توکن** با hmac.compare_digest

### **Security Headers**
```http
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

### **Input Validation**
- **SecurityValidator** برای اعتبارسنجی ورودی‌ها
- **File Upload Security** با محدودیت فرمت و اندازه
- **Password Strength** validation
- **IP Security Management**

---

## 📊 بهینه‌سازی عملکرد

### **Database Optimization**
- **Query Optimizer** برای کوئری‌های N+1
- **Database Indexing** برای فیلدهای پرکاربرد
- **Eager Loading** برای روابط
- **Pagination** برای لیست‌های بزرگ

### **Caching Strategy**
- **Redis Cache** برای داده‌های پرتکرار
- **Cache Manager** برای مدیریت مرکزی
- **Query Result Caching**
- **Static File Caching**

### **Image Optimization**
- **Image Optimizer** با Pillow
- **تبدیل فرمت** به WebP
- **فشرده‌سازی خودکار**
- **Thumbnail Generation**

---

## 🚀 API و مستندات

### **RESTful API**
- **طراحی استاندارد** برای تمام مدل‌ها
- **Authentication** با Bearer Token
- **Validation** و Error Handling
- **Swagger/OpenAPI** documentation

### **Endpoints اصلی**
```
GET    /api/products       # لیست محصولات
POST   /api/products       # ایجاد محصول
GET    /api/orders         # لیست سفارشات
POST   /api/customers      # ثبت مشتری
```

### **مستندات کامل**
- 📚 **API Documentation** - مستندات کامل در این فایل موجود است
- 🚀 **Deployment Guide** - راهنمای استقرار در بخش "راه‌اندازی سریع"
- 👨‍💻 **Developer Guide** - راهنمای توسعه‌دهندگان در بخش "تست و کیفیت"

---

## 🧪 تست و کیفیت

### **Test Coverage**
- **تست‌های واحد** برای مدل‌ها و توابع
- **تست‌های یکپارچگی** برای authentication
- **CRUD Operations** testing
- **Coverage > 80%** هدف‌گذاری شده

### **Code Quality**
- **PEP8 Standards** رعایت شده
- **Type Hints** برای توابع مهم
- **Docstrings** برای مستندسازی
- **Clean Code** principles

### **اجرای تست‌ها**
```bash
# اجرای تمام تست‌ها
pytest

# مشاهده coverage
pytest --cov=app

# تست‌های مشخص
pytest tests/test_models.py
```

---

## 📈 مانیتورینگ و لاگینگ

### **Logging System**
- **سطح WARNING** و بالاتر در production
- **فایل‌های لاگ** منظم
- **Error Tracking** با Sentry
- **Audit Trail** برای فعالیت‌های مهم

### **Health Monitoring**
- **Health Check Endpoint** (`/health`)
- **Database Connection** monitoring
- **Redis Connection** monitoring
- **Performance Metrics**

### **Error Handling**
- **Custom Error Pages** (404, 500)
- **Exception Logging** جامع
- **User-Friendly Messages**
- **Developer Debug Info**

---

## 🔄 سیستم Batch Management

### **InStore Order Batch**
- **مدیریت دقیق موجودی** با روش FIFO
- **رزرو موجودی** برای سفارشات
- **ردیابی فروش** و مرجوعی
- **تاریخچه کامل** تغییرات

### **وضعیت‌های سفارش**
- **در انتظار** - سفارش ثبت شده
- **آماده تحویل** - موجودی رزرو شده
- **تحویل داده شده** - فروش نهایی
- **لغو شده** - آزادسازی رزرو
- **مرجوع شده** - بازگشت موجودی

---

## 🎨 طراحی UI/UX

### **Modern Design**
- **Tailwind CSS** برای استایل مدرن
- **Dark/Light Theme** پشتیبانی
- **Responsive Design** برای موبایل
- **Persian RTL** پشتیبانی کامل

### **User Experience**
- **Toast Notifications** برای بازخورد
- **Loading States** برای عملیات طولانی
- **Form Validation** Real-time
- **Keyboard Shortcuts** برای کاربران حرفه‌ای

### **Accessibility**
- **ARIA Labels** برای screen readers
- **Keyboard Navigation** پشتیبانی
- **Color Contrast** مناسب
- **Font Size** قابل تنظیم

---

## 📝 مشخصات طراح

### 👨‍💻 **طراح و توسعه‌دهنده**
**نام:** مجید طیبی
**تخصص:** Full-Stack Developer & System Architect
**شماره تماس:** [۰۹۳۵۷۰۱۰۹۷۷](tel:+989357010977)
**سال طراحی:** ۲۰۲۵

### 🎯 **ویژگی‌های طراحی**
- **معماری مقیاس‌پذیر** برای رشد کسب‌وکار
- **امنیت پیشرفته** با استانداردهای روز
- **عملکرد بهینه** با تکنیک‌های مدرن
- **کد تمیز و قابل نگهداری**
- **مستندسازی کامل** برای توسعه آینده

### 🏆 **نقاط قوت پروژه**
- ✅ **امنیت بالا** - RBAC, CSRF, Session Management
- ✅ **عملکرد عالی** - Caching, Query Optimization
- ✅ **مقیاس‌پذیری** - Docker, Microservices Ready
- ✅ **تست شده** - Unit & Integration Tests
- ✅ **مستندسازی کامل** - API, Deployment, Developer Guides

---

**© ۲۰۲۵ - طراحی و توسعه توسط مجید طیبی**
**تمامی حقوق محفوظ است • سیستم تحت مجوز اختصاصی**