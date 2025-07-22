#!/bin/bash
set -e

# 1. نصب Docker و Docker Compose در صورت نیاز
if ! command -v docker &> /dev/null; then
    echo "[+] Docker نصب نیست. در حال نصب Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker $USER
    echo "[+] لطفا یک بار logout و login کنید تا دسترسی docker فعال شود."
fi

if ! command -v docker compose &> /dev/null; then
    echo "[+] Docker Compose جدید نصب نیست. در حال نصب..."
    sudo mkdir -p /usr/local/lib/docker/cli-plugins
    sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) \
        -o /usr/local/lib/docker/cli-plugins/docker-compose
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

# 2. ساخت فایل env در صورت نبودن
if [ ! -f .env ]; then
    echo "[+] فایل .env وجود ندارد. در حال کپی از env_example..."
    cp env_example .env
    echo "[!] لطفا مقادیر .env را بررسی و در صورت نیاز ویرایش کنید."
fi

# 3. خواندن مقادیر دیتابیس از .env
DB_NAME=$(grep '^POSTGRES_DB=' .env | cut -d '=' -f2)
DB_USER=$(grep '^POSTGRES_USER=' .env | cut -d '=' -f2)
DB_PASS=$(grep '^POSTGRES_PASSWORD=' .env | cut -d '=' -f2)

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
    echo "[!] مقادیر دیتابیس در .env به درستی تنظیم نشده‌اند. لطفا .env را بررسی کنید."
    exit 1
fi

# 4. اجرای docker compose
export POSTGRES_DB="$DB_NAME"
export POSTGRES_USER="$DB_USER"
export POSTGRES_PASSWORD="$DB_PASS"
echo "[+] اجرای docker compose در حالت production..."
docker compose -f docker-compose.yml up -d --build --remove-orphans

# 5. صبر برای آماده شدن دیتابیس
echo "[+] منتظر آماده شدن دیتابیس..."
for i in {1..30}; do
    if docker exec parnamyadak_db pg_isready -U "$DB_USER" > /dev/null 2>&1; then
        echo "[✅] دیتابیس آماده است."
        break
    fi
    echo "⏳ صبر کن، هنوز آماده نیست..."
    sleep 2
done

echo "[🎉] پروژه با موفقیت راه‌اندازی شد!"
echo "[ℹ️] مشاهده لاگ‌ها: docker compose logs -f"
echo "[ℹ️] توقف پروژه: docker compose down"
