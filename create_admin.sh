#!/bin/bash

# اسکریپت ایجاد کاربر ادمین برای پروژه پرنام یدک

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

echo ""
echo -e "${BLUE}👑 ایجاد مدیر سیستم برای پروژه پرنام یدک${NC}"
echo ""

# بررسی وجود Docker Compose
if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose یافت نشد!"
    exit 1
fi

# بررسی وجود فایل seed_admin.py
if [ ! -f "seed_admin.py" ]; then
    print_error "فایل seed_admin.py یافت نشد!"
    exit 1
fi

# بررسی وضعیت کانتینرها
print_info "بررسی وضعیت کانتینرها..."
if ! docker compose ps | grep -q "Up"; then
    print_warning "کانتینرها در حال اجرا نیستند. راه‌اندازی..."
    docker compose up -d
    sleep 10
fi

# بررسی دسترسی به دیتابیس
print_info "بررسی دسترسی به دیتابیس..."
if ! docker compose exec -T db pg_isready > /dev/null 2>&1; then
    print_error "دیتابیس در دسترس نیست!"
    print_info "لطفاً ابتدا سیستم را راه‌اندازی کنید: ./install.sh"
    exit 1
fi

# اجرای اسکریپت ایجاد مدیر سیستم
print_info "اجرای اسکریپت ایجاد مدیر سیستم..."
if docker compose run --rm web python seed_admin.py; then
    echo ""
    print_success "مدیر سیستم با موفقیت ایجاد شد!"
    echo ""
    echo -e "${GREEN}📋 اطلاعات ورود به پنل:${NC}"
    echo "  🌐 آدرس: http://localhost:5000"
    echo "  👤 نام کاربری: admin"
    echo "  🔑 رمز عبور: admin123"
    echo ""
    echo -e "${YELLOW}⚠️ نکات مهم:${NC}"
    echo "  - حتماً رمز عبور را بعد از اولین ورود تغییر دهید"
    echo "  - این کاربر دسترسی کامل به تمام بخش‌های پنل دارد"
    echo "  - می‌توانید از بخش مدیریت کاربران، کاربران جدید ایجاد کنید"
    echo "  - نقش‌های مختلف (Manager, Employee, Support, Inventory) ایجاد شده‌اند"
    echo ""
    echo -e "${BLUE}📋 نقش‌های ایجاد شده:${NC}"
    echo "  👑 Admin - دسترسی کامل (17 مجوز)"
    echo "  👔 Manager - مدیر (11 مجوز)"
    echo "  👤 Employee - کارمند (5 مجوز)"
    echo "  🎧 Support - پشتیبانی (6 مجوز)"
    echo "  👁️ Viewer - بازدیدکننده (5 مجوز)"
    echo ""
else
    print_error "خطا در ایجاد مدیر سیستم!"
    print_info "برای مشاهده جزئیات خطا: docker compose logs web"
    exit 1
fi

print_success "عملیات تکمیل شد!"
