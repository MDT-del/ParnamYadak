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

# 3. بررسی وجود فایل nginx.conf
if [ ! -f nginx.conf ]; then
    echo "[+] فایل nginx.conf پیدا نشد. یک نمونه اولیه ساخته می‌شود..."
    cat > nginx.conf <<EOL
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    server_name _;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    location / {
        proxy_pass http://app:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOL
    echo "[⚠️] لطفاً فایل nginx.conf را متناسب با دامنه و نیاز خود ویرایش کنید."
fi

# 4. بررسی وجود فایل env ربات
if [ ! -f ./ParnamYadak_bot/bot_config.env ]; then
    echo "[❌] فایل bot_config.env برای ربات پیدا نشد. لطفاً آن را ایجاد و مقداردهی کنید."
    exit 1
fi

# 5. بررسی وجود گواهی SSL
if [ ! -d /etc/letsencrypt ] || [ ! -f /etc/letsencrypt/live/example.com/fullchain.pem ]; then
    echo "[⚠️] گواهی SSL پیدا نشد. اگر دامنه و SSL دارید، مطمئن شوید مسیر صحیح است."
    echo "[ℹ️] برای تست می‌توانید از certbot یا راهنمای nginx استفاده کنید."
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

# 10. تنظیم دسترسی پوشه‌های Nginx (در صورت نیاز)
echo "[🔧] تنظیم دسترسی پوشه‌های Nginx و static..."
docker exec -u root parnamyadak_proxy chmod -R 755 /etc/nginx /etc/letsencrypt || true

echo ""
echo "[🎉] پروژه پرنام یدک با موفقیت اجرا شد!"
echo "[ℹ️] مشاهده لاگ‌ها: docker compose logs -f"
echo "[🛑] توقف پروژه: docker compose down"
