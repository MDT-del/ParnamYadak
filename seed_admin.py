#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فایل: seed_admin.py
توضیح: ایجاد مدیر سیستم اولیه با تمام مجوزهای پنل
"""

import os
import sys
from flask import Flask
from app import create_app, db
from app.models import User, Role, Permission

def create_admin_user():
    """ایجاد مدیر سیستم اولیه با تمام مجوزها"""
    
    print("🚀 شروع ایجاد مدیر سیستم...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 1. ایجاد تمام مجوزهای پنل
            print("📋 ایجاد مجوزهای پنل...")
            permissions_data = {
                'view_dashboard': 'مشاهده داشبورد',
                'manage_products': 'مدیریت کامل محصولات',
                'manage_categories': 'مدیریت کامل دسته‌بندی‌ها',
                'manage_orders': 'مدیریت کامل سفارشات',
                'manage_pre_orders': 'مدیریت کامل پیش‌سفارش‌ها',
                'manage_instore_orders': 'مدیریت سفارشات حضوری',
                'manage_customers': 'مدیریت کامل مشتریان',
                'manage_roles': 'مدیریت کامل نقش‌ها و دسترسی‌ها',
                'manage_admins': 'مدیریت کامل کاربران پنل',
                'view_financial_reports': 'مشاهده گزارش‌های مالی',
                'manage_broadcasts': 'مدیریت پیام‌های همگانی',
                'manage_support': 'مدیریت تیکت‌های پشتیبانی',
                'manage_tasks': 'مدیریت کارتابل و وظایف',
                'manage_inventory': 'مدیریت انبار و موجودی',
                'manage_bot_orders': 'مدیریت سفارشات ربات',
                'manage_mechanics': 'مدیریت تعمیرکاران',
                'manage_commissions': 'مدیریت کمیسیون‌ها',
                'manage_notifications': 'مدیریت اعلان‌ها',
                'manage_backups': 'مدیریت پشتیبان‌گیری',
                'manage_settings': 'مدیریت تنظیمات سیستم',
                'view_audit_logs': 'مشاهده لاگ‌های سیستم',
                'manage_licenses': 'مدیریت لایسنس‌ها',
                'export_data': 'خروجی گرفتن از داده‌ها',
                'import_data': 'وارد کردن داده‌ها'
            }
            
            created_permissions = []
            for perm_name, perm_desc in permissions_data.items():
                permission = Permission.query.filter_by(name=perm_name).first()
                if not permission:
                    permission = Permission(name=perm_name, description=perm_desc)
                    db.session.add(permission)
                    created_permissions.append(perm_name)
                    print(f"  ✅ مجوز '{perm_desc}' ایجاد شد")
                else:
                    print(f"  ⚠️ مجوز '{perm_desc}' از قبل موجود است")
            
            # 2. ایجاد نقش ادمین
            print("👑 ایجاد نقش مدیر سیستم...")
            admin_role = Role.query.filter_by(name='Admin').first()
            if not admin_role:
                admin_role = Role(
                    name='Admin',
                    description='مدیر کل سیستم - دسترسی کامل به تمام بخش‌های پنل'
                )
                db.session.add(admin_role)
                print("  ✅ نقش مدیر سیستم ایجاد شد")
            else:
                print("  ⚠️ نقش مدیر سیستم از قبل موجود است")
            
            # 3. اختصاص تمام مجوزها به نقش ادمین
            print("🔑 اختصاص مجوزها به نقش مدیر سیستم...")
            all_permissions = Permission.query.all()
            for permission in all_permissions:
                if permission not in admin_role.permissions:
                    admin_role.permissions.append(permission)
                    print(f"  ✅ مجوز '{permission.description}' به مدیر اختصاص یافت")
            
            # 4. ایجاد کاربر مدیر سیستم
            print("🔐 ایجاد کاربر مدیر سیستم...")
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    name='مدیر کل سیستم'
                )
                admin_user.set_password('admin123')  # رمز پیش‌فرض
                db.session.add(admin_user)
                print("  ✅ کاربر مدیر سیستم ایجاد شد")
                print("  📝 نام کاربری: admin")
                print("  🔑 رمز عبور: admin123")
            else:
                print("  ⚠️ کاربر مدیر سیستم از قبل موجود است")
                print("  📝 نام کاربری: admin")
                print("  🔑 رمز عبور فعلی حفظ شد")
            
            # 5. اختصاص نقش ادمین به کاربر
            print("🎭 اختصاص نقش مدیر سیستم به کاربر...")
            if admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)
                print("  ✅ نقش مدیر سیستم به کاربر اختصاص یافت")
            else:
                print("  ⚠️ نقش مدیر سیستم از قبل به کاربر اختصاص یافته")
            
            # 6. ایجاد نقش‌های اضافی برای پنل
            print("📋 ایجاد نقش‌های اضافی...")
            additional_roles = [
                {
                    'name': 'Manager',
                    'description': 'مدیر - دسترسی به اکثر بخش‌های پنل',
                    'permissions': [
                        'view_dashboard', 'manage_products', 'manage_orders',
                        'manage_customers', 'view_financial_reports', 'manage_inventory',
                        'manage_instore_orders', 'manage_bot_orders'
                    ]
                },
                {
                    'name': 'Employee',
                    'description': 'کارمند - دسترسی محدود به بخش‌های عملیاتی',
                    'permissions': [
                        'view_dashboard', 'manage_orders', 'manage_customers',
                        'manage_instore_orders'
                    ]
                },
                {
                    'name': 'Support',
                    'description': 'پشتیبانی - مدیریت تیکت‌ها و پشتیبانی مشتریان',
                    'permissions': [
                        'view_dashboard', 'manage_support', 'manage_customers',
                        'manage_notifications'
                    ]
                },
                {
                    'name': 'Inventory',
                    'description': 'انباردار - مدیریت انبار و موجودی',
                    'permissions': [
                        'view_dashboard', 'manage_inventory', 'manage_products'
                    ]
                }
            ]
            
            for role_data in additional_roles:
                role = Role.query.filter_by(name=role_data['name']).first()
                if not role:
                    role = Role(
                        name=role_data['name'],
                        description=role_data['description']
                    )
                    db.session.add(role)
                    
                    # اختصاص مجوزها
                    for perm_name in role_data['permissions']:
                        permission = Permission.query.filter_by(name=perm_name).first()
                        if permission and permission not in role.permissions:
                            role.permissions.append(permission)
                    
                    print(f"  ✅ نقش '{role_data['description']}' ایجاد شد")
                else:
                    print(f"  ⚠️ نقش '{role_data['description']}' از قبل موجود است")
            
            # 7. ذخیره تغییرات
            db.session.commit()
            
            print("\n🎉 ایجاد مدیر سیستم با موفقیت تکمیل شد!")
            print("\n📋 اطلاعات ورود به پنل:")
            print("  🌐 آدرس: http://localhost:5000")
            print("  👤 نام کاربری: admin")
            print("  🔑 رمز عبور: admin123")
            print("\n⚠️ نکات مهم:")
            print("  - حتماً رمز عبور را بعد از اولین ورود تغییر دهید")
            print("  - این کاربر دسترسی کامل به تمام بخش‌های پنل دارد")
            print("  - می‌توانید از بخش مدیریت کاربران، کاربران جدید ایجاد کنید")
            print("  - نقش‌های مختلف برای انواع کاربران ایجاد شده است")
            
            return True
            
        except Exception as e:
            print(f"❌ خطا در ایجاد مدیر سیستم: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

def main():
    """تابع اصلی"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("استفاده:")
        print("  python seed_admin.py")
        print("  docker compose run --rm web python seed_admin.py")
        return
    
    success = create_admin_user()
    if success:
        print("\n✅ عملیات با موفقیت انجام شد!")
        sys.exit(0)
    else:
        print("\n❌ عملیات با خطا مواجه شد!")
        sys.exit(1)

if __name__ == "__main__":
    main()
