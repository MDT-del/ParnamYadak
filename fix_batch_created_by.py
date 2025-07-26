#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت اصلاح فیلد created_by در پارت‌های انبار
این اسکریپت پارت‌هایی که created_by ندارند یا به person اشاره می‌کنند را اصلاح می‌کند
"""

import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import InventoryBatch, User, Person
import logging

def fix_batch_created_by():
    """اصلاح فیلد created_by در پارت‌های انبار"""
    app = create_app()
    
    with app.app_context():
        try:
            # دریافت همه پارت‌ها
            batches = InventoryBatch.query.all()
            
            print(f"🔄 شروع بررسی {len(batches)} پارت...")
            
            fixed_count = 0
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User.query.first()
            
            for batch in batches:
                try:
                    # بررسی اینکه آیا created_by معتبر است
                    user_exists = False
                    if batch.created_by:
                        user_exists = User.query.get(batch.created_by) is not None
                    
                    if not batch.created_by or not user_exists:
                        print(f"🔧 اصلاح پارت {batch.batch_number}")
                        print(f"   📦 محصول: {batch.product.name}")
                        print(f"   🔢 created_by قبلی: {batch.created_by}")
                        
                        # تنظیم به admin یا اولین کاربر
                        if admin_user:
                            batch.created_by = admin_user.id
                            print(f"   ✅ created_by جدید: {admin_user.id} ({admin_user.name})")
                        else:
                            print(f"   ❌ هیچ کاربری یافت نشد!")
                            continue
                        
                        fixed_count += 1
                    else:
                        user = User.query.get(batch.created_by)
                        print(f"✅ پارت {batch.batch_number} - ثبت‌کننده: {user.name if user else 'نامشخص'}")
                    
                except Exception as e:
                    print(f"❌ خطا در بررسی پارت {batch.id}: {e}")
            
            # ذخیره تغییرات
            if fixed_count > 0:
                db.session.commit()
                print(f"✅ {fixed_count} پارت اصلاح شد!")
            else:
                print("✅ همه پارت‌ها درست هستند!")
            
        except Exception as e:
            print(f"❌ خطا در اصلاح: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_batch_created_by()
