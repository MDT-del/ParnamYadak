# 📚 API Documentation

این مستند، راهنمای کامل استفاده از API پروژه نیکایدک است.

## احراز هویت API (Authentication)

برای استفاده از endpointهای محافظت‌شده، باید هدر زیر را ارسال کنید:

```
Authorization: Bearer testtoken123
```

در نسخه نهایی، این مقدار با JWT جایگزین خواهد شد.

---

## ساختار کلی Endpointها

### مثال:
```
GET /api/products
POST /api/orders
```

---

## لیست Endpointهای اصلی

### محصولات (Products)
- `GET /api/products` : دریافت لیست محصولات
- `GET /api/products/<id>` : دریافت جزئیات یک محصول
- `POST /api/products` : ایجاد محصول جدید
- `PUT /api/products/<id>` : ویرایش محصول
- `DELETE /api/products/<id>` : حذف محصول

#### نمونه درخواست ایجاد محصول
```http
POST /api/products
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "کلاچ پراید",
  "price": 1200000,
  "stock": 10
}
```

#### نمونه پاسخ موفق
```json
{
  "id": 1,
  "name": "کلاچ پراید",
  "price": 1200000,
  "stock": 10
}
```

---

### سفارشات (Orders)
- `GET /api/orders` : لیست سفارشات
- `POST /api/orders` : ثبت سفارش جدید

---

### مشتریان (Customers)
- `GET /api/customers` : لیست مشتریان
- ...

---

## Swagger/OpenAPI
برای مشاهده و تست تعاملی API، مستندات Swagger/OpenAPI به زودی در مسیر `/docs/swagger` در دسترس خواهد بود.

---

## تولید خودکار مستندات با Swagger/OpenAPI

برای تولید و مشاهده مستندات تعاملی API:

1. اطمینان حاصل کنید که پکیج‌های زیر نصب هستند:
   ```bash
   pip install flask-swagger-ui flask-apispec
   ```
2. در فایل اصلی پروژه (مثلاً run.py یا app/__init__.py) کد زیر را اضافه کنید:
   ```python
   from flask_swagger_ui import get_swaggerui_blueprint
   SWAGGER_URL = '/docs/swagger'
   API_URL = '/static/swagger.json'  # یا مسیر فایل OpenAPI شما
   swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
   app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
   ```
3. فایل swagger.json یا openapi.yaml را در مسیر static قرار دهید یا با flask-apispec تولید کنید.
4. حالا می‌توانید مستندات تعاملی را در مسیر `/docs/swagger` مشاهده و تست کنید.

---

## سطوح دسترسی
- برخی endpointها فقط برای ادمین یا نقش‌های خاص فعال هستند. به پیام خطا و کد وضعیت توجه کنید.

---

## خطاها
- تمام خطاها به صورت JSON با کلید `error` بازگردانده می‌شوند.
- مثال:
```json
{
  "error": "دسترسی غیرمجاز"
}
``` 