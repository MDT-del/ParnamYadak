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

# بررسی وجود پوشه migrations
if [ ! -d "migrations" ]; then
    echo "پوشه migrations وجود ندارد. در حال ساخت migrations..."
    flask db init

    # تلاش برای ایجاد migration اولیه
    echo "ایجاد migration اولیه..."
    if ! flask db migrate -m "initial migration"; then
        echo "خطا در ایجاد migration. تلاش برای حل مشکل..."

        # حذف پوشه migrations و تلاش مجدد
        rm -rf migrations
        flask db init

        # ایجاد جداول به صورت دستی
        python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    try:
        # ایجاد جداول
        db.create_all()
        print('✅ جداول با موفقیت ایجاد شدند!')
    except Exception as e:
        print(f'❌ خطا در ایجاد جداول: {e}')
        raise
"

        # ایجاد migration برای وضعیت فعلی
        flask db stamp head
        echo "✅ Migration اولیه با موفقیت تنظیم شد!"
    fi
else
    echo "پوشه migrations موجود است. اجرای upgrade..."
fi

# اجرای upgrade
if ! flask db upgrade; then
    echo "خطا در اجرای migration. تلاش برای حل مشکل..."

    # بررسی وضعیت دیتابیس
    python -c "
from app import create_app, db
from sqlalchemy import inspect
app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'جداول موجود: {tables}')

    if not tables:
        print('هیچ جدولی وجود ندارد. ایجاد جداول...')
        db.create_all()
        print('✅ جداول ایجاد شدند!')
    else:
        print('جداول موجود هستند.')
"
fi

# ایجاد دایرکتوری‌های مورد نیاز (در صورت عدم وجود)
mkdir -p uploads logs static/receipts static/product_pics static/mechanic_licenses static/bot_receipts

# مجوزها در Dockerfile تنظیم شده‌اند
echo "✅ دایرکتوری‌ها آماده هستند"

echo "راه‌اندازی کامل شد. شروع اپلیکیشن..."

# اجرای دستور ارسال شده
exec "$@"