#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت به‌روزرسانی نوع مشتریان
این اسکریپت اطلاعات اولین سفارش همه مشتریان را به‌روزرسانی می‌کند
"""

import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Person
import logging

def update_all_customers():
    """به‌روزرسانی اطلاعات همه مشتریان"""
    app = create_app()
    
    with app.app_context():
        try:
            # دریافت همه مشتریان
            customers = Person.query.filter_by(person_type='customer').all()
            
            print(f"🔄 شروع به‌روزرسانی {len(customers)} مشتری...")
            
            updated_count = 0
            for customer in customers:
                try:
                    old_type = getattr(customer, 'first_order_type', None)
                    
                    # به‌روزرسانی اطلاعات اولین سفارش
                    customer.update_first_order_info()
                    
                    new_type = getattr(customer, 'first_order_type', None)
                    customer_type = customer.customer_type
                    
                    print(f"✅ {customer.full_name} (ID: {customer.id})")
                    print(f"   📱 Telegram ID: {customer.telegram_id or 'ندارد'}")
                    print(f"   📞 Username: @{customer.username}" if customer.username else "   📞 Username: ندارد")
                    print(f"   🏷️ نوع اولین سفارش: {old_type} → {new_type}")
                    print(f"   👤 نوع مشتری: {customer_type}")
                    print("   " + "-" * 50)
                    
                    updated_count += 1
                    
                except Exception as e:
                    print(f"❌ خطا در به‌روزرسانی {customer.full_name}: {e}")
            
            # ذخیره تغییرات
            db.session.commit()
            print(f"✅ به‌روزرسانی {updated_count} مشتری با موفقیت انجام شد!")
            
        except Exception as e:
            print(f"❌ خطا در به‌روزرسانی: {e}")
            db.session.rollback()

if __name__ == '__main__':
    update_all_customers()
