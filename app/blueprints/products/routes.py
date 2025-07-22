# ---------------------------------------------
# فایل: routes.py (products)
# توضیح: مدیریت محصولات، افزودن، ویرایش، حذف و آپلود اکسل محصولات
# ---------------------------------------------

import os
import secrets
from PIL import Image
from flask import render_template, redirect, url_for, flash, Blueprint, current_app, request
from flask_login import login_required
from app import db
from app.models import Product, Category
from app.forms import ProductForm
from app.decorators import permission_required
import openpyxl

products_bp = Blueprint('products', __name__, template_folder='templates')


def save_picture(form_picture):
    """
    ذخیره عکس محصول آپلود شده و تغییر اندازه آن
    """
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/product_pics',
                                picture_fn)
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)
    output_size = (1000, 1000)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


def find_or_create_category_by_path(path_str):
    """
    یک مسیر دسته‌بندی مثل 'والد > فرزند' یا چند مسیر با کاما دریافت کرده و آن را در دیتابیس پیدا یا ایجاد می‌کند.
    """
    if not path_str:
        return []  # اگر مسیر خالی بود، لیست خالی برگردان

    all_categories = []
    paths = [p.strip() for p in path_str.split(',')]
    for path in paths:
        path_parts = [part.strip() for part in path.split('>')]
        parent = None
        final_category = None
        for part in path_parts:
            category = Category.query.filter_by(name=part,
                                                parent=parent).first()
            if not category:
                category = Category(name=part, parent=parent)
                db.session.add(category)
                db.session.commit()
            final_category = category
            parent = category
        if final_category:
            all_categories.append(final_category)
    return all_categories


@products_bp.route('/', methods=['GET', 'POST'])
@login_required
@permission_required('manage_products')
def index():
    """
    ویو مدیریت محصولات (افزودن و نمایش لیست محصولات)
    """
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(name=form.name.data,
                              description=form.description.data,
                              price=form.price.data,
                              stock=form.stock.data)
        if form.picture.data:
            new_product.image_file = save_picture(form.picture.data)
        new_product.categories = form.categories.data
        db.session.add(new_product)
        db.session.commit()
        flash('محصول جدید با موفقیت اضافه شد!', 'success')
        return redirect(url_for('products.index'))
    all_products = Product.query.order_by(Product.id.desc()).all()
    return render_template('products.html',
                           form=form,
                           products=all_products,
                           title="مدیریت محصولات")


# ⬇️ تابع آپلود اکسل با منطق جدید و پیشرفته‌تر ⬇️
def find_or_create_category(path_str):
    """
    یک مسیر دسته‌بندی مثل 'والد > فرزند' دریافت کرده و آن را در دیتابیس پیدا یا ایجاد می‌کند.
    """
    path_parts = [part.strip() for part in path_str.split('>')]
    parent = None
    final_category = None
    for part in path_parts:
        category = Category.query.filter_by(name=part, parent=parent).first()
        if not category:
            category = Category(name=part, parent=parent)
            db.session.add(category)
            db.session.commit(
            )  # Commit immediately to get the ID for the next parent
        final_category = category
        parent = category
    return final_category


@products_bp.route('/upload-excel', methods=['POST'])
@login_required
@permission_required('manage_products')
def upload_excel():
    """
    ویو آپلود فایل اکسل برای افزودن یا به‌روزرسانی محصولات
    """
    if 'excel_file' not in request.files:
        flash('هیچ فایلی انتخاب نشده است.', 'danger')
        return redirect(url_for('products.index'))
    file = request.files['excel_file']
    if file.filename == '':
        flash('هیچ فایلی انتخاب نشده است.', 'danger')
        return redirect(url_for('products.index'))
    if file and file.filename.endswith('.xlsx'):
        try:
            workbook = openpyxl.load_workbook(file)
            sheet = workbook.active
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if not any(row):
                    continue

                name, description, price, stock, category_path = row[:5]
                product = Product.query.filter_by(name=name).first()
                if not product:
                    product = Product(name=name)
                    db.session.add(product)

                product.description = description
                product.price = float(price) if price is not None else 0
                product.stock = int(stock) if stock is not None else 0

                if category_path:
                    product.categories = find_or_create_category_by_path(
                        category_path)

            db.session.commit()
            flash('فایل اکسل با موفقیت پردازش شد و محصولات آپدیت شدند.',
                  'success')
        except Exception as e:
            db.session.rollback()
            flash(f'خطا در پردازش فایل: {e}', 'danger')
        return redirect(url_for('products.index'))
    else:
        flash('فرمت فایل باید .xlsx باشد.', 'danger')
        return redirect(url_for('products.index'))


@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@permission_required('manage_products')
def edit_product(product_id):
    """
    ویو ویرایش اطلاعات یک محصول خاص
    """
    product_to_edit = db.session.get(Product, product_id)
    if not product_to_edit:
        flash('محصول مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('products.index'))
    form = ProductForm(obj=product_to_edit)
    if form.validate_on_submit():
        if form.picture.data:
            product_to_edit.image_file = save_picture(form.picture.data)
        product_to_edit.name = form.name.data
        product_to_edit.description = form.description.data
        product_to_edit.price = form.price.data
        product_to_edit.stock = form.stock.data
        product_to_edit.categories = form.categories.data
        db.session.commit()
        flash('محصول با موفقیت ویرایش شد.', 'success')
        return redirect(url_for('products.index'))
    # مقداردهی اولیه فیلد دسته‌بندی‌ها برای نمایش صحیح در فرم ویرایش
    form.categories.data = product_to_edit.categories
    return render_template('edit_product.html',
                           form=form,
                           product=product_to_edit,
                           title="ویرایش محصول")


@products_bp.route('/delete/<int:product_id>', methods=['POST'])
@login_required
@permission_required('manage_products')
def delete_product(product_id):
    """
    ویو حذف یک محصول خاص
    """
    product_to_delete = db.session.get(Product, product_id)
    if not product_to_delete:
        flash('محصول مورد نظر یافت نشد.', 'danger')
        return redirect(url_for('products.index'))
    db.session.delete(product_to_delete)
    db.session.commit()
    flash('محصول با موفقیت حذف شد.', 'success')
    return redirect(url_for('products.index'))
