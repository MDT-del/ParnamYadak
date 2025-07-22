# ---------------------------------------------
# فایل: image_optimizer.py
# توضیح: بهینه‌سازی تصاویر محصولات برای بهبود عملکرد و کاهش حجم
# ---------------------------------------------

import os
import uuid
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class ImageOptimizer:
    """
    کلاس بهینه‌سازی تصاویر محصولات
    """
    
    # تنظیمات پیش‌فرض
    DEFAULT_MAX_SIZE = (800, 800)  # حداکثر اندازه تصویر
    THUMBNAIL_SIZE = (200, 200)    # اندازه تصویر بندانگشتی
    QUALITY = 85                   # کیفیت JPEG
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    @staticmethod
    def allowed_file(filename):
        """
        بررسی مجاز بودن پسوند فایل
        """
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ImageOptimizer.ALLOWED_EXTENSIONS
    
    @staticmethod
    def generate_unique_filename(original_filename):
        """
        تولید نام فایل یکتا
        """
        ext = original_filename.rsplit('.', 1)[1].lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}.{ext}"
    
    @staticmethod
    def optimize_image(image_path, output_path=None, max_size=None, quality=None):
        """
        بهینه‌سازی تصویر اصلی
        
        Args:
            image_path (str): مسیر تصویر ورودی
            output_path (str): مسیر خروجی (اختیاری)
            max_size (tuple): حداکثر اندازه (عرض، ارتفاع)
            quality (int): کیفیت JPEG (1-100)
        
        Returns:
            str: مسیر فایل بهینه‌سازی شده
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"تصویر {image_path} یافت نشد")
            
            # تنظیمات پیش‌فرض
            max_size = max_size or ImageOptimizer.DEFAULT_MAX_SIZE
            quality = quality or ImageOptimizer.QUALITY
            
            # باز کردن تصویر
            with Image.open(image_path) as img:
                # تبدیل به RGB اگر RGBA باشد
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # تغییر اندازه با حفظ نسبت
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # تعیین مسیر خروجی
                if output_path is None:
                    output_path = image_path
                
                # ذخیره تصویر بهینه‌سازی شده
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                logger.info(f"تصویر {image_path} با موفقیت بهینه‌سازی شد")
                return output_path
                
        except Exception as e:
            logger.error(f"خطا در بهینه‌سازی تصویر {image_path}: {e}")
            raise
    
    @staticmethod
    def create_thumbnail(image_path, thumbnail_path, size=None):
        """
        ایجاد تصویر بندانگشتی
        
        Args:
            image_path (str): مسیر تصویر اصلی
            thumbnail_path (str): مسیر تصویر بندانگشتی
            size (tuple): اندازه بندانگشتی (عرض، ارتفاع)
        
        Returns:
            str: مسیر تصویر بندانگشتی
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"تصویر {image_path} یافت نشد")
            
            size = size or ImageOptimizer.THUMBNAIL_SIZE
            
            # باز کردن تصویر
            with Image.open(image_path) as img:
                # تبدیل به RGB اگر RGBA باشد
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # ایجاد بندانگشتی با حفظ نسبت
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # ذخیره بندانگشتی
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                
                logger.info(f"بندانگشتی {thumbnail_path} با موفقیت ایجاد شد")
                return thumbnail_path
                
        except Exception as e:
            logger.error(f"خطا در ایجاد بندانگشتی {image_path}: {e}")
            raise
    
    @staticmethod
    def process_uploaded_image(file, product_id=None):
        """
        پردازش تصویر آپلود شده
        
        Args:
            file: فایل آپلود شده
            product_id (int): شناسه محصول (اختیاری)
        
        Returns:
            dict: اطلاعات فایل‌های پردازش شده
        """
        try:
            if not file or not ImageOptimizer.allowed_file(file.filename):
                raise ValueError("فایل نامعتبر")
            
            # تولید نام فایل یکتا
            original_filename = secure_filename(file.filename)
            unique_filename = ImageOptimizer.generate_unique_filename(original_filename)
            
            # مسیرهای فایل
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/product_pics')
            os.makedirs(upload_folder, exist_ok=True)
            
            original_path = os.path.join(upload_folder, unique_filename)
            thumbnail_path = os.path.join(upload_folder, f"thumb_{unique_filename}")
            
            # ذخیره فایل اصلی
            file.save(original_path)
            
            # بهینه‌سازی تصویر اصلی
            optimized_path = ImageOptimizer.optimize_image(original_path)
            
            # ایجاد بندانگشتی
            thumbnail_path = ImageOptimizer.create_thumbnail(optimized_path, thumbnail_path)
            
            # حذف فایل اصلی غیربهینه
            if original_path != optimized_path:
                os.remove(original_path)
            
            return {
                'original_filename': original_filename,
                'filename': unique_filename,
                'thumbnail_filename': f"thumb_{unique_filename}",
                'file_size': os.path.getsize(optimized_path),
                'thumbnail_size': os.path.getsize(thumbnail_path)
            }
            
        except Exception as e:
            logger.error(f"خطا در پردازش تصویر آپلود شده: {e}")
            raise
    
    @staticmethod
    def delete_product_images(filename):
        """
        حذف تصاویر محصول
        
        Args:
            filename (str): نام فایل تصویر
        """
        try:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/product_pics')
            
            # مسیرهای فایل
            image_path = os.path.join(upload_folder, filename)
            thumbnail_path = os.path.join(upload_folder, f"thumb_{filename}")
            
            # حذف فایل‌ها
            if os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"تصویر {image_path} حذف شد")
            
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                logger.info(f"بندانگشتی {thumbnail_path} حذف شد")
                
        except Exception as e:
            logger.error(f"خطا در حذف تصاویر محصول {filename}: {e}")
            raise
    
    @staticmethod
    def get_image_info(image_path):
        """
        دریافت اطلاعات تصویر
        
        Args:
            image_path (str): مسیر تصویر
        
        Returns:
            dict: اطلاعات تصویر
        """
        try:
            if not os.path.exists(image_path):
                return None
            
            with Image.open(image_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'size_bytes': os.path.getsize(image_path)
                }
                
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات تصویر {image_path}: {e}")
            return None
    
    @staticmethod
    def batch_optimize_images(folder_path, max_size=None, quality=None):
        """
        بهینه‌سازی دسته‌ای تصاویر
        
        Args:
            folder_path (str): مسیر پوشه تصاویر
            max_size (tuple): حداکثر اندازه
            quality (int): کیفیت JPEG
        
        Returns:
            dict: آمار بهینه‌سازی
        """
        stats = {
            'total_files': 0,
            'optimized_files': 0,
            'errors': 0,
            'total_saved_bytes': 0
        }
        
        try:
            if not os.path.exists(folder_path):
                raise FileNotFoundError(f"پوشه {folder_path} یافت نشد")
            
            for filename in os.listdir(folder_path):
                if ImageOptimizer.allowed_file(filename):
                    stats['total_files'] += 1
                    file_path = os.path.join(folder_path, filename)
                    
                    try:
                        # اندازه فایل قبل از بهینه‌سازی
                        original_size = os.path.getsize(file_path)
                        
                        # بهینه‌سازی
                        ImageOptimizer.optimize_image(file_path, max_size=max_size, quality=quality)
                        
                        # اندازه فایل بعد از بهینه‌سازی
                        optimized_size = os.path.getsize(file_path)
                        saved_bytes = original_size - optimized_size
                        
                        stats['optimized_files'] += 1
                        stats['total_saved_bytes'] += saved_bytes
                        
                        logger.info(f"تصویر {filename} بهینه‌سازی شد. صرفه‌جویی: {saved_bytes} بایت")
                        
                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f"خطا در بهینه‌سازی {filename}: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"خطا در بهینه‌سازی دسته‌ای: {e}")
            raise


# توابع کمکی
def get_image_url(filename, thumbnail=False):
    """
    دریافت URL تصویر
    
    Args:
        filename (str): نام فایل
        thumbnail (bool): آیا بندانگشتی باشد
    
    Returns:
        str: URL تصویر
    """
    if not filename:
        return None
    
    if thumbnail:
        filename = f"thumb_{filename}"
    
    return f"/static/product_pics/{filename}"


def validate_image_file(file):
    """
    اعتبارسنجی فایل تصویر
    
    Args:
        file: فایل آپلود شده
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not file:
        return False, "فایل انتخاب نشده است"
    
    if not ImageOptimizer.allowed_file(file.filename):
        return False, "فرمت فایل پشتیبانی نمی‌شود"
    
    # بررسی اندازه فایل (حداکثر 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    file.seek(0, 2)  # رفتن به انتهای فایل
    file_size = file.tell()
    file.seek(0)  # بازگشت به ابتدای فایل
    
    if file_size > max_size:
        return False, "حجم فایل بیش از 5 مگابایت است"
    
    return True, None 