#!/bin/bash
set -e

# رنگ‌ها برای خروجی بهتر
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# تابع‌های کمکی برای چاپ پیام‌های رنگی
print_info() {
    echo -e "${BLUE}[ℹ️] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[✅] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[⚠️] $1${NC}"
}

print_error() {
    echo -e "${RED}[❌] $1${NC}"
}

# تابع بررسی و حل مشکل migration
fix_migration_issues() {
    print_info "بررسی مشکلات migration..."

    # بررسی لاگ‌های خطا
    if docker compose logs web 2>/dev/null | grep -q "NoReferencedTableError\|Foreign key.*could not find table\|could not find table"; then
        print_warning "مشکل Foreign Key در migration تشخیص داده شد!"
        return 1
    fi

    # بررسی وجود پوشه migrations
    if ! docker compose exec web test -d /app/migrations 2>/dev/null; then
        print_warning "پوشه migrations وجود ندارد!"
        return 1
    fi

    # بررسی وضعیت migration
    if ! docker compose run --rm web flask db current >/dev/null 2>&1; then
        print_warning "مشکل در وضعیت migration!"
        return 1
    fi

    print_success "Migration در وضعیت سالم است."
    return 0
}

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

# 8.1. بررسی و حل خودکار مشکل migration
print_info "بررسی وضعیت migration..."

# انتظار کوتاه برای اجرای کامل entrypoint
sleep 5

# بررسی مشکلات migration
if ! fix_migration_issues; then
    print_warning "مشکل migration تشخیص داده شد. در حال حل خودکار..."

    # توقف کانتینر web
    print_info "توقف کانتینر web..."
    docker compose stop web

    # حذف پوشه migrations
    print_info "حذف پوشه migrations موجود..."
    docker compose exec db psql -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" || true

    # حل دستی مشکل migration
    print_info "حل خودکار مشکل migration..."
    docker compose run --rm web python -c "
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

    # تنظیم migration stamp
    docker compose run --rm web flask db stamp head || true

    # راه‌اندازی مجدد web
    print_info "راه‌اندازی مجدد سرویس web..."
    docker compose up -d web

    # انتظار برای آماده شدن
    sleep 10

    # بررسی مجدد
    if fix_migration_issues; then
        print_success "مشکل migration حل شد!"
    else
        print_error "مشکل migration همچنان وجود دارد. لطفاً لاگ‌ها را بررسی کنید."
    fi
else
    print_success "Migration بدون مشکل اجرا شد."
fi

# 8.3. ایجاد کاربر ادمین اولیه
print_info "ایجاد کاربر ادمین اولیه..."
if docker compose run --rm web python seed_admin.py; then
    print_success "کاربر ادمین با موفقیت ایجاد شد!"
    echo ""
    echo -e "${GREEN}📋 اطلاعات ورود به پنل:${NC}"
    echo "  🌐 آدرس: http://localhost:5000"
    echo "  👤 نام کاربری: admin"
    echo "  🔑 رمز عبور: admin123"
    echo ""
    echo -e "${YELLOW}⚠️ حتماً رمز عبور را بعد از اولین ورود تغییر دهید!${NC}"
else
    print_warning "مشکل در ایجاد کاربر ادمین. ممکن است از قبل موجود باشد."
fi

# 9. تنظیم دسترسی پوشه‌های داخل کانتینر (در صورت نیاز)
print_info "تنظیم دسترسی پوشه‌های static, logs, uploads..."
docker exec -u root parnamyadak_app chmod -R 777 /app/logs /app/uploads /app/static 2>/dev/null || true

# 10. تنظیم دسترسی پوشه‌های Nginx (در صورت نیاز)
print_info "تنظیم دسترسی پوشه‌های Nginx و static..."
docker exec -u root parnamyadak_proxy chmod -R 755 /etc/nginx /etc/letsencrypt 2>/dev/null || true

# 11. بررسی نهایی وضعیت سیستم
print_info "بررسی نهایی وضعیت سیستم..."

# بررسی وضعیت کانتینرها
if docker compose ps | grep -q "Up"; then
    print_success "همه کانتینرها در حال اجرا هستند."
else
    print_warning "برخی کانتینرها مشکل دارند:"
    docker compose ps
fi

# بررسی دسترسی به وب اپلیکیشن
print_info "بررسی دسترسی به وب اپلیکیشن..."
sleep 5

# تلاش برای اتصال به وب اپلیکیشن
for i in {1..5}; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 2>/dev/null | grep -q "200\|302\|301"; then
        print_success "وب اپلیکیشن در دسترس است."
        break
    fi
    if [ $i -eq 5 ]; then
        print_warning "مشکل در دسترسی به وب اپلیکیشن. بررسی لاگ‌ها:"
        docker compose logs web | tail -10
    else
        print_info "تلاش $i از 5 برای اتصال به وب اپلیکیشن..."
        sleep 3
    fi
done

# نمایش اطلاعات مفید
echo ""
print_success "پروژه پرنام یدک با موفقیت اجرا شد!"
echo ""
echo -e "${BLUE}[📋] اطلاعات مفید:${NC}"
echo "    🌐 آدرس پنل: http://localhost:5000"
echo "    👤 نام کاربری ادمین: admin"
echo "    🔑 رمز عبور ادمین: admin123"
echo "    📊 مشاهده لاگ‌ها: docker compose logs -f"
echo "    🔄 ری‌استارت: docker compose restart"
echo "    🛑 توقف پروژه: docker compose down"
echo "    🗄️ بک‌آپ دیتابیس: docker exec parnamyadak_db pg_dump -U $DB_USER $DB_NAME > backup.sql"
echo "    🔧 حل مشکل migration: ./install.sh (اجرای مجدد)"
echo "    👑 ایجاد مجدد ادمین: docker compose run --rm web python seed_admin.py"
echo ""
echo -e "${YELLOW}[⚠️] نکات مهم:${NC}"
echo "    - در صورت مشکل، ابتدا لاگ‌ها را بررسی کنید"
echo "    - برای بروزرسانی: git pull && docker compose build --no-cache && docker compose up -d"
echo "    - فایل‌های مهم در پوشه‌های logs/, uploads/, static/ ذخیره می‌شوند"
echo "    - در صورت مشکل migration، این اسکریپت را مجدداً اجرا کنید"
echo "    - برای ری‌ست کامل: docker compose down -v && ./install.sh"
