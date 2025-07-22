# ---------------------------------------------
# فایل: run.py
# توضیح: نقطه ورود اصلی برنامه برای اجرای اپلیکیشن Flask
# ---------------------------------------------

from app import create_app, socketio
from flask import send_from_directory

# ساخت اپلیکیشن Flask
app = create_app()

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

if __name__ == '__main__':
    # اجرای اپلیکیشن با پشتیبانی از WebSocket
    socketio.run(app, host='0.0.0.0', port=5000)
