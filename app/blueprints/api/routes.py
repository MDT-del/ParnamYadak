from flask import jsonify, request, abort
from . import api_bp
from app.models import Product

API_TOKEN = 'testtoken123'  # برای تست، بعداً JWT جایگزین شود

def require_api_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth or not auth.startswith('Bearer '):
            abort(401, description='Missing or invalid token')
        token = auth.split(' ')[1]
        if token != API_TOKEN:
            abort(401, description='Invalid token')
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/health', methods=['GET'])
def api_health():
    return jsonify({'status': 'ok'}), 200

# مثال endpoint محافظت‌شده
@api_bp.route('/protected', methods=['GET'])
@require_api_auth
def protected():
    return jsonify({'message': 'Access granted'}), 200

# CRUD endpoints for User, Product, Order, Customer, ... will be added here
@api_bp.route('/products', methods=['GET'])
@require_api_auth
def get_products():
    products = Product.query.all()
    return jsonify([
        {
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'stock': getattr(p, 'stock', None)
        } for p in products
    ]) 