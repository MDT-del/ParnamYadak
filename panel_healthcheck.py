import sys
import os
from app import create_app, db
from app.models import User, License, Product, Notification, BackupFile
from flask import current_app

app = create_app()

SUCCESS = '\033[92m✔\033[0m'
FAIL = '\033[91m✘\033[0m'

errors = []


def check_db():
    try:
        with app.app_context():
            db.session.execute('SELECT 1')
        print(f"{SUCCESS} Database connection: OK")
    except Exception as e:
        print(f"{FAIL} Database connection: {e}")
        errors.append('db')


def check_license():
    try:
        with app.app_context():
            lic = License.query.first()
            assert lic is not None, 'No license record found'
            active = License.query.filter_by(is_active=True).first()
        if active:
            print(f"{SUCCESS} License: Active")
            return True
        else:
            print(f"{SUCCESS} License: Not activated yet (setup phase)")
            return False
    except Exception as e:
        print(f"{FAIL} License: {e}")
        errors.append('license')
        return False


def check_admin():
    try:
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            assert admin is not None, 'No admin user found'
        print(f"{SUCCESS} Admin user: OK")
    except Exception as e:
        print(f"{FAIL} Admin user: {e}")
        errors.append('admin')


def check_product():
    try:
        with app.app_context():
            prod = Product.query.first()
            assert prod is not None, 'No product found'
        print(f"{SUCCESS} Product: OK")
    except Exception as e:
        print(f"{FAIL} Product: {e}")
        errors.append('product')


def check_notification():
    try:
        with app.app_context():
            notif = Notification.query.first()
            assert notif is not None, 'No notification found'
        print(f"{SUCCESS} Notification: OK")
    except Exception as e:
        print(f"{FAIL} Notification: {e}")
        errors.append('notification')


def check_backup():
    try:
        with app.app_context():
            backup = BackupFile.query.first()
            assert backup is not None, 'No backup found'
        print(f"{SUCCESS} Backup: OK")
    except Exception as e:
        print(f"{FAIL} Backup: {e}")
        errors.append('backup')


def main():
    print('--- Panel Healthcheck ---')
    check_db()
    license_active = check_license()
    if not errors and not license_active:
        print(f"\n{SUCCESS} Healthcheck passed for setup phase (before license activation).\nYou can proceed to license setup.")
        sys.exit(0)
    if not errors and license_active:
        check_admin()
        check_product()
        check_notification()
        check_backup()
        if errors:
            print(f"\n{FAIL} Healthcheck failed after license activation. Panel will NOT start.")
            sys.exit(1)
        else:
            print(f"\n{SUCCESS} All checks passed. Panel is healthy.")
            sys.exit(0)
    else:
        print(f"\n{FAIL} Healthcheck failed. Panel will NOT start.")
        sys.exit(1)

if __name__ == '__main__':
    main() 