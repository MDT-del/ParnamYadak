# ---------------------------------------------
# فایل: __init__.py
# توضیح: فایل راه‌اندازی blueprint سفارشات ربات
# ---------------------------------------------

from flask import Blueprint

bot_orders_bp = Blueprint('bot_orders', __name__, url_prefix='/bot-orders', template_folder='templates')

from . import routes