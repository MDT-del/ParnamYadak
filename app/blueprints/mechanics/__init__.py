# ---------------------------------------------
# فایل: __init__.py
# توضیح: فایل راه‌اندازی blueprint مدیریت مکانیک‌ها
# ---------------------------------------------

from flask import Blueprint

mechanics_bp = Blueprint('mechanics', __name__, url_prefix='/mechanics', template_folder='templates')

from . import routes 