#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
فایل تست ساده برای بررسی عملکرد ماژول‌های امنیتی
"""

import sys
import os

# اضافه کردن مسیر پروژه به Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """تست import کردن ماژول‌ها"""
    print("Testing imports...")
    
    try:
        from app.security_utils import SecurityValidator
        print("✅ SecurityValidator imported successfully")
    except Exception as e:
        print(f"❌ Error importing SecurityValidator: {e}")
        return False
    
    try:
        from app.security_utils import CSRFProtection
        print("✅ CSRFProtection imported successfully")
    except Exception as e:
        print(f"❌ Error importing CSRFProtection: {e}")
        return False
    
    try:
        from config import get_secure_secret_key
        print("✅ get_secure_secret_key imported successfully")
    except Exception as e:
        print(f"❌ Error importing get_secure_secret_key: {e}")
        return False
    
    return True

def test_password_validation():
    """تست اعتبارسنجی رمز عبور"""
    try:
        from app.security_utils import SecurityValidator
        
        print("\nTesting password validation...")
        
        # تست رمز ضعیف
        weak_result = SecurityValidator.validate_password_strength("123456")
        print(f"Weak password test: {'PASS' if not weak_result['is_valid'] else 'FAIL'}")
        
        # تست رمز قوی
        strong_result = SecurityValidator.validate_password_strength("MyStrongPass123!")
        print(f"Strong password test: {'PASS' if strong_result['is_valid'] else 'FAIL'}")
        
        return True
    except Exception as e:
        print(f"❌ Error in password validation test: {e}")
        return False

def test_phone_validation():
    """تست اعتبارسنجی شماره تلفن"""
    try:
        from app.security_utils import SecurityValidator
        
        print("\nTesting phone validation...")
        
        # تست شماره معتبر
        valid_phone = SecurityValidator.validate_phone_number("09123456789")
        print(f"Valid phone test: {'PASS' if valid_phone else 'FAIL'}")
        
        # تست شماره نامعتبر
        invalid_phone = SecurityValidator.validate_phone_number("123456789")
        print(f"Invalid phone test: {'PASS' if not invalid_phone else 'FAIL'}")
        
        return True
    except Exception as e:
        print(f"❌ Error in phone validation test: {e}")
        return False

def test_csrf_token():
    """تست تولید توکن CSRF"""
    try:
        from app.security_utils import CSRFProtection
        
        print("\nTesting CSRF token generation...")
        
        token1 = CSRFProtection.generate_csrf_token()
        token2 = CSRFProtection.generate_csrf_token()
        
        print(f"Token 1 length: {len(token1)}")
        print(f"Token 2 length: {len(token2)}")
        print(f"Tokens are unique: {'PASS' if token1 != token2 else 'FAIL'}")
        
        return True
    except Exception as e:
        print(f"❌ Error in CSRF token test: {e}")
        return False

def main():
    """اجرای تمام تست‌ها"""
    print("=" * 50)
    print("Security Modules Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_password_validation,
        test_phone_validation,
        test_csrf_token
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")

if __name__ == "__main__":
    main()