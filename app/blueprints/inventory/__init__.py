# ---------------------------------------------
# فایل: __init__.py
# توضیح: فایل راه‌اندازی blueprint مدیریت انبار
# ---------------------------------------------

from flask import Blueprint

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory', template_folder='templates')

from . import routes 