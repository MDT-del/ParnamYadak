#!/bin/bash

# اسکریپت راه‌اندازی برای کانتینر Docker

set -e

echo "شروع راه‌اندازی اپلیکیشن پرنام یدک..."

# انتظار برای آماده شدن دیتابیس
echo "انتظار برای آماده شدن دیتابیس..."
while ! nc -z db 5432; do
  sleep 1
done
echo "دیتابیس آماده است!"

# اجرای migration های دیتابیس
echo "اجرای migration های دیتابیس..."
if [ ! -d "migrations" ]; then
    echo "پوشه migrations وجود ندارد. در حال ساخت migrations..."
    flask db init
    flask db migrate -m "initial"
fi
flask db upgrade

# ایجاد دایرکتوری‌های مورد نیاز
mkdir -p uploads logs static/receipts static/product_pics static/mechanic_licenses static/bot_receipts

# تنظیم مجوزها
chmod -R 755 uploads logs static

echo "راه‌اندازی کامل شد. شروع اپلیکیشن..."

# اجرای دستور ارسال شده
exec "$@"