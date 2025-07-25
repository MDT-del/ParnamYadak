#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
فایل تست برای بررسی عملکرد ماژول‌های امنیتی
"""

import sys
import os

# اضافه کردن مسیر پروژه به Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.security_utils import SecurityValidator, CSRFProtection, IPSecurityManager
from config import get_secure_secret_key


def test_password_validation():
    """تست اعتبارسنجی رمز عبور"""
    print("🔐 تست اعتبارسنجی رمز عبور:")
    
    # رمزهای عبور مختلف برای تست
    passwords = [
        "123456",           # ضعیف
        "password",         # ضعیف
        "MyPass123",        # متوسط
        "MyStrongPass123!", # قوی
        "abc",              # خیلی ضعیف
        "ABCDEfgh123@"      # قوی
    ]
    
    for password in passwords:
        result = SecurityValidator.validate_password_strength(password)
        status = "✅ قوی" if result['is_valid'] else "❌ ضعیف"
        print(f"  {password:<20} -> {status} (امتیاز: {result['score']}/5)")
        if result['errors']:
            print(f"    خطاها: {', '.join(result['errors'])}")
        if result['suggestions']:
            print(f"    پیشنهادات: {', '.join(result['suggestions'])}")
        print()


def test_phone_validation():
    """تست اعتبارسنجی شماره تلفن"""
    print("📱 تست اعتبارسنجی شماره تلفن:")
    
    phones = [
        "09123456789",  # معتبر
        "9123456789",   # نامعتبر (بدون 0)
        "091234567890", # نامعتبر (طولانی)
        "0912345678",   # نامعتبر (کوتاه)
        "02123456789",  # نامعتبر (تلفن ثابت)
        "09987654321"   # معتبر
    ]
    
    for phone in phones:
        is_valid = SecurityValidator.validate_phone_number(phone)
        status = "✅ معتبر" if is_valid else "❌ نامعتبر"
        print(f"  {phone:<15} -> {status}")


def test_email_validation():
    """تست اعتبارسنجی ایمیل"""
    print("📧 تست اعتبارسنجی ایمیل:")
    
    emails = [
        "user@example.com",     # معتبر
        "test.email@gmail.com", # معتبر
        "invalid-email",        # نامعتبر
        "user@",                # نامعتبر
        "@example.com",         # نامعتبر
        "user@example",         # نامعتبر
        "user.name+tag@example.co.uk"  # معتبر
    ]
    
    for email in emails:
        is_valid = SecurityValidator.validate_email(email)
        status = "✅ معتبر" if is_valid else "❌ نامعتبر"
        print(f"  {email:<30} -> {status}")


def test_input_sanitization():
    """تست پاک‌سازی ورودی"""
    print("🧹 تست پاک‌سازی ورودی:")
    
    inputs = [
        "سلام دنیا",
        "<script>alert('xss')</script>",
        "نام کاربر & شرکت",
        'تست "نقل قول" و \'آپستروف\'',
        "متن عادی بدون مشکل",
        "متن خیلی طولانی " * 100  # تست محدودیت طول
    ]
    
    for input_text in inputs:
        sanitized = SecurityValidator.sanitize_input(input_text, max_length=50)
        print(f"  ورودی: {input_text[:30]}...")
        print(f"  خروجی: {sanitized}")
        print()


def test_csrf_token():
    """تست تولید توکن CSRF"""
    print("🛡️ تست توکن CSRF:")
    
    # تولید چند توکن
    tokens = [CSRFProtection.generate_csrf_token() for _ in range(3)]
    
    for i, token in enumerate(tokens, 1):
        print(f"  توکن {i}: {token[:20]}... (طول: {len(token)})")
    
    # بررسی یکتا بودن
    if len(set(tokens)) == len(tokens):
        print("  ✅ تمام توکن‌ها یکتا هستند")
    else:
        print("  ❌ توکن‌های تکراری یافت شد")


def test_ip_security():
    """تست مدیریت امنیت IP"""
    print("🌐 تست مدیریت امنیت IP:")
    
    test_ip = "192.168.1.100"
    
    # بررسی وضعیت اولیه
    print(f"  IP {test_ip} مسدود است: {IPSecurityManager.is_ip_blocked(test_ip)}")
    print(f"  IP {test_ip} مشکوک است: {IPSecurityManager.is_ip_suspicious(test_ip)}")
    
    # مسدود کردن IP
    IPSecurityManager.block_ip(test_ip, "تست امنیتی")
    print(f"  بعد از مسدود کردن - IP {test_ip} مسدود است: {IPSecurityManager.is_ip_blocked(test_ip)}")


def test_secret_key():
    """تست تولید کلید امنیتی"""
    print("🔑 تست تولید کلید امنیتی:")
    
    try:
        secret_key = get_secure_secret_key()
        print(f"  کلید تولید شد: {secret_key[:20]}... (طول: {len(secret_key)})")
        
        if len(secret_key) >= 64:
            print("  ✅ طول کلید مناسب است (حداقل 64 کاراکتر)")
        else:
            print("  ⚠️ طول کلید کمتر از حد توصیه شده است")
            
    except Exception as e:
        print(f"  ❌ خطا در تولید کلید: {e}")


def main():
    """اجرای تمام تست‌ها"""
    print("=" * 60)
    print("🧪 تست ماژول‌های امنیتی پروژه پرنام یدک")
    print("=" * 60)
    print()
    
    try:
        test_password_validation()
        print("-" * 60)
        
        test_phone_validation()
        print("-" * 60)
        
        test_email_validation()
        print("-" * 60)
        
        test_input_sanitization()
        print("-" * 60)
        
        test_csrf_token()
        print("-" * 60)
        
        test_ip_security()
        print("-" * 60)
        
        test_secret_key()
        print("-" * 60)
        
        print("✅ تمام تست‌ها با موفقیت اجرا شدند!")
        
    except Exception as e:
        print(f"❌ خطا در اجرای تست‌ها: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()