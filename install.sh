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

if ! command -v docker-compose &> /dev/null; then
    echo "[+] Docker Compose نصب نیست. در حال نصب Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
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

# 4. اجرای docker-compose
export POSTGRES_DB="$DB_NAME"
export POSTGRES_USER="$DB_USER"
export POSTGRES_PASSWORD="$DB_PASS"
echo "[+] اجرای docker-compose در حالت production..."
docker-compose -f docker-compose.yml up -d --build

echo "[+] منتظر آماده شدن دیتابیس..."
# صبر برای آماده شدن دیتابیس (تا 60 ثانیه)
for i in {1..30}; do
    if docker exec $(docker ps -qf "name=postgres") pg_isready -U "$DB_USER"; then
        echo "[+] دیتابیس آماده است."
        break
    fi
    sleep 2
done

echo "[+] پروژه با موفقیت راه‌اندازی شد!"
echo "[i] برای مشاهده لاگ‌ها: docker-compose logs -f"
echo "[i] برای توقف: docker-compose down" 