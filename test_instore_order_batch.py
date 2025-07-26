#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت تست مدل InStoreOrderBatch
"""

import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import InStoreOrderBatch, InStoreOrder, InventoryBatch, InventoryProduct
import logging

def test_instore_order_batch():
    """تست مدل InStoreOrderBatch"""
    app = create_app()

    with app.app_context():
        try:
            # بررسی وجود جدول
            print("🔍 بررسی وجود جدول instore_order_batch...")

            # تست ساده query
            count = InStoreOrderBatch.query.count()
            print(f"✅ جدول موجود است. تعداد رکوردها: {count}")

            # بررسی سفارشات حضوری موجود
            orders = InStoreOrder.query.filter_by(store_stock=True).all()
            print(f"📦 تعداد سفارشات حضوری از انبار: {len(orders)}")

            for order in orders[:3]:  # فقط 3 تای اول
                print(f"\n   سفارش {order.id}: وضعیت={order.status}")
                batches = InStoreOrderBatch.query.filter_by(order_id=order.id).all()
                print(f"   تعداد پارت‌های رزرو شده: {len(batches)}")
                for batch in batches:
                    print(f"     پارت {batch.batch_id}: رزرو={batch.reserved_qty}, فروخته={batch.sold_qty}")

            # بررسی محصولات انبار
            products = InventoryProduct.query.limit(3).all()
            print(f"\n📋 تعداد محصولات انبار: {InventoryProduct.query.count()}")

            for product in products:
                print(f"\n   محصول {product.id} ({product.name}):")
                print(f"     موجودی کل: {product.total_quantity}")
                print(f"     رزرو شده: {product.reserved_quantity}")
                print(f"     قابل فروش: {product.available_quantity}")
                print(f"     فروخته شده: {product.sold_quantity}")

                batches = InventoryBatch.query.filter_by(product_id=product.id).all()
                print(f"     تعداد پارت‌ها: {len(batches)}")
                for batch in batches:
                    print(f"       پارت {batch.id} ({batch.batch_number}):")
                    print(f"         باقی‌مانده: {batch.remaining_quantity}")
                    print(f"         رزرو: {batch.reserved_quantity}")
                    print(f"         فروخته: {batch.sold_quantity}")

            # تست به‌روزرسانی موجودی
            print(f"\n🔄 تست به‌روزرسانی موجودی...")
            for product in products[:1]:  # فقط یکی
                print(f"   قبل از به‌روزرسانی: موجودی={product.total_quantity}, رزرو={product.reserved_quantity}")
                product.update_quantities()
                print(f"   بعد از به‌روزرسانی: موجودی={product.total_quantity}, رزرو={product.reserved_quantity}")

        except Exception as e:
            print(f"❌ خطا: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_instore_order_batch()
