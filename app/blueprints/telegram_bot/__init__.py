# ---------------------------------------------
# فایل: __init__.py
# توضیح: بلوپرینت API های ربات تلگرام برای اتصال به سیستم فروش
# ---------------------------------------------

from flask import Blueprint

telegram_bot_bp = Blueprint('telegram_bot', __name__)

from . import routes 