# ---------------------------------------------
# فایل: routes.py
# توضیح: مسیرهای مدیریت انبار - شامل افزودن، ویرایش، جستجو و مدیریت پارت‌ها
# ---------------------------------------------

from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import InventoryProduct, InventoryBatch, db
from app.utils import shamsi_date, shamsi_datetime
from . import inventory_bp
import json
from datetime import datetime, timedelta
import pytz


@inventory_bp.route('/')
@login_required
def index():
    """
    صفحه اصلی مدیریت انبار
    نمایش لیست محصولات با قابلیت جستجو و فیلتر
    """
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    quality = request.args.get('quality', '')
    
    # ساخت کوئری
    query = InventoryProduct.query
    
    # اعمال فیلترهای جستجو
    if search:
        query = query.filter(InventoryProduct.name.ilike(f'%{search}%'))
    
    if quality:
        query = query.filter(InventoryProduct.quality == quality)
    
    # مرتب‌سازی بر اساس تاریخ ایجاد (جدیدترین اول)
    query = query.order_by(InventoryProduct.created_at.desc())
    
    # صفحه‌بندی
    products = query.paginate(
        page=page, per_page=20, error_out=False
    )

    # محاسبه آمار هر محصول بر اساس پارت‌ها
    product_stats = []
    low_stock_count = 0  # تعداد محصولات با موجودی کم (2 یا کمتر)
    total_available_quantity = 0  # جمع موجودی قابل فروش تمام محصولات
    
    for product in products.items:
        batches = product.batches.all()
        total_initial = sum(batch.initial_quantity for batch in batches)
        total_remaining = sum(batch.remaining_quantity for batch in batches)
        total_sold = sum(batch.initial_quantity - batch.remaining_quantity for batch in batches)
        reserved = product.reserved_quantity
        
        # بررسی موجودی کم (2 یا کمتر)
        if total_remaining <= 2:
            low_stock_count += 1
        
        # جمع موجودی قابل فروش
        total_available_quantity += total_remaining
        
        product_stats.append({
            'id': product.id,
            'product_number': product.product_number,
            'name': product.name,
            'quality': product.quality,
            'total_initial': total_initial,
            'total_remaining': total_remaining,
            'total_sold': total_sold,
            'reserved_quantity': reserved,
            'created_at': product.created_at,
        })

    return render_template('index.html', 
                         products=products,
                         product_stats=product_stats,
                         low_stock_count=low_stock_count,
                         total_available_quantity=total_available_quantity,
                         search=search,
                         quality=quality)


@inventory_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    """
    افزودن محصول جدید به انبار
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        quality = request.form.get('quality', 'ایرانی')
        initial_quantity = request.form.get('initial_quantity', 0, type=int)
        purchase_price = request.form.get('purchase_price', type=float)
        
        # اعتبارسنجی
        if not name:
            flash('نام محصول الزامی است', 'error')
            return render_template('add_product.html')
        
        if initial_quantity < 0:
            flash('موجودی اولیه نمی‌تواند منفی باشد', 'error')
            return render_template('add_product.html')
        
        # بررسی تکراری نبودن نام و کیفیت محصول
        existing_product = InventoryProduct.query.filter_by(name=name, quality=quality).first()
        if existing_product:
            flash('این محصول با این کیفیت قبلاً در انبار ثبت شده است', 'error')
            return render_template('add_product.html')
        
        try:
            # ایجاد محصول جدید
            product = InventoryProduct(
                name=name,
                quality=quality
            )
            
            # تولید شماره محصول
            product.generate_product_number()
            
            db.session.add(product)
            db.session.commit()
            
            # اگر موجودی اولیه وجود دارد، پارت اول ایجاد شود
            if initial_quantity > 0:
                batch = InventoryBatch(
                    product_id=product.id,
                    initial_quantity=initial_quantity,
                    remaining_quantity=initial_quantity,
                    purchase_price=purchase_price,
                    created_by=current_user.id
                )
                
                # تولید شماره پارت
                batch.generate_batch_number()
                
                db.session.add(batch)
                db.session.commit()
                
                # بروزرسانی آمار محصول بر اساس پارت‌ها
                product.update_quantities()
            
            flash('محصول با موفقیت به انبار اضافه شد', 'success')
            return redirect(url_for('inventory.index'))
            
        except Exception as e:
            db.session.rollback()
            flash('خطا در ثبت محصول', 'error')
            return render_template('add_product.html')
    
    return render_template('add_product.html')


@inventory_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    """
    نمایش جزئیات محصول و پارت‌های آن
    """
    product = InventoryProduct.query.get_or_404(product_id)
    
    # دریافت پارت‌های فعال (موجودی > 0)
    active_batches = product.batches.filter(
        InventoryBatch.remaining_quantity > 0
    ).order_by(InventoryBatch.created_at.asc()).all()
    
    # دریافت تمام پارت‌ها
    all_batches = product.batches.order_by(InventoryBatch.created_at.desc()).all()
    
    return render_template('product_detail.html',
                         product=product,
                         active_batches=active_batches,
                         all_batches=all_batches)


@inventory_bp.route('/product/<int:product_id>/add_batch', methods=['POST'])
@login_required
def add_batch(product_id):
    """
    افزودن پارت جدید به محصول
    """
    product = InventoryProduct.query.get_or_404(product_id)
    
    initial_quantity = request.form.get('initial_quantity', 0, type=int)
    purchase_price = request.form.get('purchase_price', type=float)
    
    if initial_quantity <= 0:
        return jsonify({'success': False, 'message': 'موجودی باید بیشتر از صفر باشد'})
    
    try:
        # ایجاد پارت جدید
        batch = InventoryBatch(
            product_id=product.id,
            initial_quantity=initial_quantity,
            remaining_quantity=initial_quantity,
            purchase_price=purchase_price,
            created_by=current_user.id
        )
        
        # تولید شماره پارت
        batch.generate_batch_number()
        
        db.session.add(batch)
        
        # بروزرسانی آمار محصول
        product.update_quantities()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'پارت جدید با موفقیت اضافه شد',
            'batch': {
                'id': batch.id,
                'initial_quantity': batch.initial_quantity,
                'remaining_quantity': batch.remaining_quantity,
                'purchase_price': batch.purchase_price,
                'created_at': shamsi_datetime(batch.created_at),
                'created_by': batch.created_by_user.name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطا در ثبت پارت'})


@inventory_bp.route('/search')
@login_required
def search():
    """
    جستجوی پیشرفته در انبار
    """
    search = request.args.get('search', '')
    quality = request.args.get('quality', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = InventoryProduct.query
    
    # جستجو بر اساس نام
    if search:
        query = query.filter(InventoryProduct.name.ilike(f'%{search}%'))
    
    # فیلتر بر اساس کیفیت
    if quality:
        query = query.filter(InventoryProduct.quality == quality)
    
    # فیلتر بر اساس تاریخ
    if date_from:
        try:
            # تبدیل تاریخ شمسی به میلادی
            from_date = shamsi_date(date_from, reverse=True)
            query = query.filter(InventoryProduct.created_at >= from_date)
        except:
            pass
    
    if date_to:
        try:
            # تبدیل تاریخ شمسی به میلادی
            to_date = shamsi_date(date_to, reverse=True)
            to_date = to_date + timedelta(days=1)  # تا پایان روز
            query = query.filter(InventoryProduct.created_at < to_date)
        except:
            pass
    
    # مرتب‌سازی
    query = query.order_by(InventoryProduct.created_at.desc())
    
    products = query.all()
    
    return render_template('search.html',
                         products=products,
                         search=search,
                         quality=quality,
                         date_from=date_from,
                         date_to=date_to)


@inventory_bp.route('/api/products')
@login_required
def api_products():
    """
    API برای جستجوی محصولات (برای ربات)
    """
    search = request.args.get('search', '')
    limit = request.args.get('limit', 10, type=int)
    
    query = InventoryProduct.query
    
    if search:
        query = query.filter(InventoryProduct.name.ilike(f'%{search}%'))
    
    # نمایش همه محصولات، حتی با موجودی صفر
    products = query.limit(limit).all()
    
    result = []
    for product in products:
        result.append({
            'id': product.id,
            'name': product.name,
            'quality': product.quality,
            'available_quantity': product.available_quantity,
            'total_quantity': product.total_quantity,
            'sold_quantity': product.sold_quantity,
            'is_available': product.available_quantity > 0,
            'status': 'موجود' if product.available_quantity > 0 else 'ناموجود'
        })
    
    return jsonify(result)


@inventory_bp.route('/api/product/<int:product_id>')
@login_required
def api_product_detail(product_id):
    """
    API برای دریافت جزئیات محصول
    """
    product = InventoryProduct.query.get_or_404(product_id)
    
    return jsonify({
        'id': product.id,
        'name': product.name,
        'quality': product.quality,
        'total_quantity': product.total_quantity,
        'available_quantity': product.available_quantity,
        'reserved_quantity': product.reserved_quantity,
        'sold_quantity': product.sold_quantity,
        'is_available': product.available_quantity > 0,
        'status': 'موجود' if product.available_quantity > 0 else 'ناموجود',
        'created_at': shamsi_datetime(product.created_at)
    })


@inventory_bp.route('/api/reserve', methods=['POST'])
@login_required
def api_reserve():
    """
    API برای رزرو موجودی
    """
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 0)
    
    if not product_id or quantity <= 0:
        return jsonify({'success': False, 'message': 'پارامترهای نامعتبر'})
    
    product = InventoryProduct.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'محصول یافت نشد'})
    
    # بررسی موجودی کافی
    if product.available_quantity < quantity:
        return jsonify({
            'success': False,
            'message': f'موجودی کافی نیست. موجودی قابل فروش: {product.available_quantity}',
            'available_quantity': product.available_quantity
        })
    
    if product.can_reserve(quantity):
        product.reserve_quantity(quantity)
        return jsonify({
            'success': True,
            'message': 'موجودی رزرو شد',
            'available_quantity': product.available_quantity
        })
    else:
        return jsonify({
            'success': False,
            'message': 'موجودی کافی نیست',
            'available_quantity': product.available_quantity
        })


@inventory_bp.route('/api/release', methods=['POST'])
@login_required
def api_release():
    """
    API برای آزادسازی رزرو
    """
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 0)
    
    if not product_id or quantity <= 0:
        return jsonify({'success': False, 'message': 'پارامترهای نامعتبر'})
    
    product = InventoryProduct.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'محصول یافت نشد'})
    
    if product.release_reservation(quantity):
        return jsonify({
            'success': True,
            'message': 'رزرو آزاد شد',
            'available_quantity': product.available_quantity
        })
    else:
        return jsonify({
            'success': False,
            'message': 'مقدار رزرو شده کمتر از مقدار درخواستی است'
        }) 

@inventory_bp.route('/api/search_products')
@login_required
def api_search_products():
    """
    جستجوی محصولات برای autocomplete سفارش حضوری
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    products = InventoryProduct.query.filter(InventoryProduct.name.ilike(f'%{query}%')).limit(15).all()
    result = []
    from app.models import InventoryBatch
    for p in products:
        last_batch = p.batches.order_by(InventoryBatch.created_at.desc()).first()
        price = last_batch.purchase_price if last_batch and last_batch.purchase_price else 0
        result.append({
            'id': p.id,
            'name': p.name,
            'quality': p.quality,
            'stock': p.total_quantity,
            'price': price
        })
    return jsonify(result)

@inventory_bp.route('/batch/<int:batch_id>/edit_price', methods=['POST'])
@login_required
def edit_batch_price(batch_id):
    """
    ویرایش قیمت خرید پارت (فقط اگر قبلاً ثبت نشده باشد)
    """
    batch = InventoryBatch.query.get_or_404(batch_id)
    data = request.get_json()
    new_price = data.get('purchase_price')
    if batch.purchase_price:
        return jsonify({'success': False, 'message': 'قیمت خرید قبلاً ثبت شده است.'})
    if new_price is None or float(new_price) < 0:
        return jsonify({'success': False, 'message': 'قیمت خرید معتبر وارد کنید.'})
    try:
        batch.purchase_price = float(new_price)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطا در ثبت قیمت خرید.'})

@inventory_bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    """
    حذف محصول فقط اگر هیچ رزروی روی آن انجام نشده باشد
    """
    product = InventoryProduct.query.get_or_404(product_id)
    if product.reserved_quantity > 0:
        return jsonify({'success': False, 'message': 'محصول قابل حذف نیست (مقداری رزرو شده است).'}), 400
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطا در حذف محصول.'}), 500

# ویرایش در حذف پارت: اگر محصول رزرو شده داشت، حذف نشود
@inventory_bp.route('/batch/<int:batch_id>/delete', methods=['POST'])
@login_required
def delete_batch(batch_id):
    """
    حذف پارت فقط اگر هیچ فروشی یا رزروی روی آن انجام نشده باشد و محصول رزرو نشده باشد
    """
    batch = InventoryBatch.query.get_or_404(batch_id)
    product = batch.product
    if batch.remaining_quantity != batch.initial_quantity:
        return jsonify({'success': False, 'message': 'پارت قابل حذف نیست (مقداری فروخته یا رزرو شده است).'}), 400
    if product.reserved_quantity > 0:
        return jsonify({'success': False, 'message': 'پارت قابل حذف نیست چون محصول رزرو شده دارد.'}), 400
    try:
        db.session.delete(batch)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'خطا در حذف پارت.'}), 500