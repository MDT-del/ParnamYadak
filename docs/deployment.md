# 🚀 راهنمای استقرار (Deployment Guide)

این راهنما مراحل نصب و راه‌اندازی پروژه نیکایدک را روی سرور توضیح می‌دهد.

## پیش‌نیازها
- Python 3.10+
- PostgreSQL یا MySQL
- Redis (اختیاری برای کش)
- Git

## نصب روی لینوکس
1. کلون پروژه:
   ```bash
   git clone <repo-url>
   cd NikaYadak
   ```
2. ساخت و فعال‌سازی virtualenv:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. نصب وابستگی‌ها:
   ```bash
   pip install -r requirements.txt
   ```
4. تنظیم فایل env:
   - فایل `env_example` را کپی و مقادیر را تنظیم کنید:
     ```bash
     cp env_example env_local
     nano env_local
     ```
5. راه‌اندازی دیتابیس:
   - ساخت دیتابیس و اجرای migrationها:
     ```bash
     flask db upgrade
     ```
6. اجرای پروژه:
   ```bash
   flask run
   ```

## نصب روی ویندوز
1. کلون پروژه و نصب Python (در صورت نیاز)
2. اجرای دستورات مشابه بالا با PowerShell
3. فعال‌سازی virtualenv:
   ```powershell
   .\venv\Scripts\activate
   ```

## بکاپ و بازیابی دیتابیس
- برای بکاپ:
  ```bash
  pg_dump <db_name> > backup.sql
  # یا برای MySQL:
  mysqldump -u user -p <db_name> > backup.sql
  ```
- برای بازیابی:
  ```bash
  psql <db_name> < backup.sql
  # یا برای MySQL:
  mysql -u user -p <db_name> < backup.sql
  ```

## بروزرسانی و نگهداری
- برای بروزرسانی:
  ```bash
  git pull
  pip install -r requirements.txt
  flask db upgrade
  systemctl restart <your-service>
  ```
- همیشه قبل از بروزرسانی بکاپ بگیرید.

## نکات امنیتی
- فایل env را امن نگه دارید.
- دسترسی به سرور را محدود کنید.
- از HTTPS استفاده کنید. 

## تنظیمات محیطی (Environment Variables)

در فایل `env_local` یا `.env`، متغیرهای زیر را تنظیم کنید:

| متغیر           | توضیح                                  | مقدار نمونه                |
|-----------------|----------------------------------------|----------------------------|
| FLASK_ENV       | حالت اجرا                              | production / development   |
| SECRET_KEY      | کلید امنیتی Flask                      | mysecretkey                |
| DATABASE_URL    | آدرس دیتابیس                           | postgresql://user:pass@localhost/db |
| REDIS_URL       | آدرس Redis (اختیاری)                   | redis://localhost:6379/0   |
| TELEGRAM_TOKEN  | توکن ربات تلگرام                       | 123456:ABC-DEF             |
| ...             | سایر متغیرهای مورد نیاز پروژه           | ...                        |

- پس از هر تغییر در env، سرور را ریستارت کنید.

## مانیتورینگ و پایش (Monitoring)

### ۱. لاگ‌گیری (Logging)
- لاگ‌های پروژه در مسیر logs/nikaydek.log ذخیره می‌شوند (در حالت production).
- برای مشاهده لاگ‌ها:
  ```bash
  tail -f logs/nikaydek.log
  ```
- سطح لاگ را می‌توانید در تنظیمات تغییر دهید (INFO/ERROR).

### ۲. رهگیری خطا (Error Tracking)
- برای رهگیری پیشرفته خطاها می‌توانید از سرویس‌هایی مثل Sentry استفاده کنید:
  1. نصب:
     ```bash
     pip install sentry-sdk
     ```
  2. افزودن به app/__init__.py:
     ```python
     import sentry_sdk
     sentry_sdk.init(dsn="YOUR_SENTRY_DSN")
     ```
- خطاهای مهم به صورت خودکار در جدول AuditLog نیز ثبت می‌شوند.

### ۳. Health Check
- یک route ساده health check در پروژه وجود دارد:
  ```python
  @app.route('/health')
  def health_check():
      return 'OK', 200
  ```
- می‌توانید این endpoint را برای مانیتورینگ سرور (مثلاً UptimeRobot) استفاده کنید.

--- 