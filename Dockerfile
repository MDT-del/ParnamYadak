# استفاده از Python 3.11 slim image برای کاهش حجم
FROM python:3.11-slim

# تنظیم متغیرهای محیطی
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب وابستگی‌های سیستمی مورد نیاز
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# آپدیت کتابخانه‌های سیستمی (از جمله OpenSSL)
RUN apt-get update && apt-get upgrade -y

# کپی فایل‌های requirements
COPY requirements.txt .

# نصب وابستگی‌های Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# کپی کد اپلیکیشن
COPY . .

# ایجاد دایرکتوری‌های مورد نیاز
RUN mkdir -p logs uploads static/receipts static/product_pics static/mechanic_licenses static/bot_receipts

# تنظیم مجوزها
RUN chmod +x run.py

# کپی اسکریپت entrypoint و اجرایی کردن آن (قبل از تغییر کاربر)
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# ایجاد کاربر غیر root برای امنیت
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app/logs /app/uploads /app/static
USER appuser

# expose کردن پورت
EXPOSE 5000

# اجرای اسکریپت entrypoint برای اجرای migration و سپس اجرای اپلیکیشن
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "run:app"]