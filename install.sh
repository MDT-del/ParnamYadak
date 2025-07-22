#!/bin/bash
set -e

echo ""
echo "[🚀] شروع نصب و راه‌اندازی پروژه پرنام یدک..."

# 1. بررسی نصب docker
if ! command -v docker &> /dev/null; then
    echo "[+] در حال نصب Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker $USER
    echo "[!] لطفاً یک بار logout و login کنید."
    exit 0
fi

# 2. بررسی نصب docker compose جدید
if ! command -v docker compose &> /dev/null; then
    echo "[+] در حال نصب Docker Compose جدید..."
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# 3. بررسی وجود فایل .env
if [ ! -f .env ]; then
    echo "[+] فایل .env پیدا نشد. کپی از env_example..."
    cp env_example .env
    echo "[⚠️] لطفاً فایل .env را ویرایش و سپس اسکریپت را دوباره اجرا کنید."
    exit 1
fi

# 4. استخراج و بررسی مقادیر دیتابیس
DB_NAME=$(grep '^POSTGRES_DB=' .env | cut -d '=' -f2)
DB_USER=$(grep '^POSTGRES_USER=' .env | cut -d '=' -f2)
DB_PASS=$(grep '^POSTGRES_PASSWORD=' .env | cut -d '=' -f2)

echo "[ℹ️] مقدار متغیرهای دیتابیس:"
echo "    POSTGRES_DB=$DB_NAME"
echo "    POSTGRES_USER=$DB_USER"
echo "    POSTGRES_PASSWORD=$DB_PASS"

echo "[ℹ️] مقدار DATABASE_URL: $(grep '^DATABASE_URL=' .env | cut -d '=' -f2)"

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
    echo "[❌] مقادیر دیتابیس در فایل .env ناقص هستند."
    exit 1
fi

# 5. پاک‌سازی محیط قبلی
echo "[🧹] پاک‌سازی docker و volumes..."
docker compose down -v --remove-orphans
docker volume prune -f || true

# 6. بیلد از صفر
echo "[🔨] در حال build مجدد پروژه..."
docker compose build --no-cache

# 7. اجرای پروژه
echo "[📦] اجرای docker compose..."
docker compose up -d

# 8. صبر برای آماده شدن دیتابیس
echo "[⏳] صبر برای آماده شدن دیتابیس..."
for i in {1..30}; do
    if docker exec parnamyadak_db pg_isready -U "$DB_USER" > /dev/null 2>&1; then
        echo "[✅] دیتابیس آماده است."
        break
    fi
    echo "⏳ منتظر دیتابیس... ($i/30)"
    sleep 2
done
if [ $i -eq 30 ]; then
    echo "[❌] دیتابیس آماده نشد. لطفاً لاگ‌ها را بررسی کنید."
    exit 1
fi

# 9. تنظیم دسترسی پوشه‌های داخل کانتینر (در صورت نیاز)
echo "[🔧] تنظیم دسترسی پوشه‌های static, logs, uploads..."
docker exec -u root parnamyadak_app chmod -R 777 /app/logs /app/uploads /app/static || true

echo ""
echo "[🎉] پروژه پرنام یدک با موفقیت اجرا شد!"
echo "[ℹ️] مشاهده لاگ‌ها: docker compose logs -f"
echo "[🛑] توقف پروژه: docker compose down"
