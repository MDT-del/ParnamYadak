from flask import Blueprint

license_bp = Blueprint('license', __name__)

from . import routes 