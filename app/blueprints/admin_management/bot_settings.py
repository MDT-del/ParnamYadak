# ---------------------------------------------
# فایل: bot_settings.py (admin_management)
# توضیح: تنظیمات ربات تلگرام
# ---------------------------------------------

from flask import render_template, redirect, url_for, flash, Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User
from app.decorators import permission_required
import os
import json

bot_settings_bp = Blueprint('bot_settings', __name__, template_folder='templates')

# مسیر فایل تنظیمات ربات
BOT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'bot', 'bot_config.env')

def read_bot_config():
    """خواندن تنظیمات ربات از فایل"""
    config = {}
    try:
        if os.path.exists(BOT_CONFIG_PATH):
            with open(BOT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error reading bot config: {e}")
    return config

def write_bot_config(config):
    """نوشتن تنظیمات ربات به فایل"""
    try:
        lines = []
        
        # خواندن فایل موجود برای حفظ کامنت‌ها
        existing_lines = []
        if os.path.exists(BOT_CONFIG_PATH):
            with open(BOT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # پردازش خطوط موجود
        for line in existing_lines:
            line = line.rstrip()
            if line.startswith('#') or not line or '=' not in line:
                # حفظ کامنت‌ها و خطوط خالی
                lines.append(line)
            else:
                # بررسی اینکه آیا این کلید در config جدید وجود دارد
                key = line.split('=', 1)[0].strip()
                if key in config:
                    lines.append(f"{key}={config[key]}")
                    del config[key]  # حذف از config تا در انتها اضافه نشود
                else:
                    lines.append(line)
        
        # اضافه کردن کلیدهای جدید
        for key, value in config.items():
            lines.append(f"{key}={value}")
        
        # نوشتن به فایل
        with open(BOT_CONFIG_PATH, 'w', encoding='utf-8') as f:
            for line in lines:
                f.write(line + '\n')
        
        return True
    except Exception as e:
        print(f"Error writing bot config: {e}")
        return False

@bot_settings_bp.route('/bot-settings')
@login_required
@permission_required('manage_admins')
def bot_settings():
    """صفحه تنظیمات ربات"""
    config = read_bot_config()
    return render_template('bot_settings.html', 
                         config=config, 
                         title="تنظیمات ربات تلگرام")

@bot_settings_bp.route('/bot-settings/save', methods=['POST'])
@login_required
@permission_required('manage_admins')
def save_bot_settings():
    """ذخیره تنظیمات ربات"""
    try:
        # دریافت داده‌های فرم
        config = {}
        
        # تنظیمات اصلی
        config['TELEGRAM_BOT_TOKEN'] = request.form.get('bot_token', '').strip()
        config['PANEL_API_BASE_URL'] = request.form.get('panel_api_url', '').strip()
        
        # تنظیمات webhook/polling
        use_webhook = request.form.get('use_webhook') == 'on'
        config['USE_WEBHOOK'] = 'True' if use_webhook else 'False'
        config['WEBHOOK_URL'] = request.form.get('webhook_url', '').strip()
        config['WEBHOOK_PATH'] = request.form.get('webhook_path', '/webhook').strip()
        config['WEBHOOK_HOST'] = request.form.get('webhook_host', '0.0.0.0').strip()
        config['WEBHOOK_PORT'] = request.form.get('webhook_port', '8080').strip()
        
        # تنظیمات لاگ
        config['LOG_LEVEL'] = request.form.get('log_level', 'INFO').strip()
        
        # اعتبارسنجی
        if not config['TELEGRAM_BOT_TOKEN']:
            flash('توکن ربات الزامی است.', 'error')
            return redirect(url_for('bot_settings.bot_settings'))
        
        if not config['PANEL_API_BASE_URL']:
            flash('آدرس API پنل الزامی است.', 'error')
            return redirect(url_for('bot_settings.bot_settings'))
        
        if use_webhook and not config['WEBHOOK_URL']:
            flash('در صورت استفاده از webhook، آدرس webhook الزامی است.', 'error')
            return redirect(url_for('bot_settings.bot_settings'))
        
        # ذخیره تنظیمات
        if write_bot_config(config):
            flash('تنظیمات ربات با موفقیت ذخیره شد.', 'success')
            
            # ثبت لاگ تغییرات
            from app.models import AuditLog
            audit = AuditLog()
            audit.user_id = current_user.id
            audit.action = 'update_bot_settings'
            audit.description = f'بروزرسانی تنظیمات ربات - Webhook: {use_webhook}'
            audit.ip_address = request.remote_addr
            db.session.add(audit)
            db.session.commit()
        else:
            flash('خطا در ذخیره تنظیمات ربات.', 'error')
    
    except Exception as e:
        flash(f'خطا در ذخیره تنظیمات: {str(e)}', 'error')
    
    return redirect(url_for('bot_settings.bot_settings'))

@bot_settings_bp.route('/bot-settings/test-webhook', methods=['POST'])
@login_required
@permission_required('manage_admins')
def test_webhook():
    """تست اتصال webhook"""
    try:
        webhook_url = request.json.get('webhook_url', '').strip()
        
        if not webhook_url:
            return jsonify({'success': False, 'message': 'آدرس webhook الزامی است.'})
        
        # تست ساده اتصال
        import requests
        import time
        
        test_url = f"{webhook_url}/health"
        start_time = time.time()
        
        try:
            response = requests.get(test_url, timeout=10)
            response_time = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                return jsonify({
                    'success': True, 
                    'message': f'اتصال موفق - زمان پاسخ: {response_time}ms'
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': f'خطا در اتصال - کد: {response.status_code}'
                })
        except requests.exceptions.Timeout:
            return jsonify({'success': False, 'message': 'زمان اتصال به پایان رسید'})
        except requests.exceptions.ConnectionError:
            return jsonify({'success': False, 'message': 'خطا در اتصال به سرور'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'خطا: {str(e)}'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطا در تست: {str(e)}'})

@bot_settings_bp.route('/bot-settings/restart-bot', methods=['POST'])
@login_required
@permission_required('manage_admins')
def restart_bot():
    """راه‌اندازی مجدد ربات"""
    try:
        # این قسمت بعداً پیاده‌سازی می‌شود
        # می‌توان از systemctl یا docker restart استفاده کرد
        
        # ثبت لاگ
        from app.models import AuditLog
        audit = AuditLog()
        audit.user_id = current_user.id
        audit.action = 'restart_bot'
        audit.description = 'درخواست راه‌اندازی مجدد ربات'
        audit.ip_address = request.remote_addr
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'درخواست راه‌اندازی مجدد ربات ارسال شد.'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطا: {str(e)}'})
