# __init__.py
from flask import Flask # type: ignore
from flask_sqlalchemy import SQLAlchemy # type: ignore
from flask_login import LoginManager # type: ignore
from flask_mail import Mail  # type: ignore # 🛑 الإضافة 1: استيراد مكتبة البريد
from .db import db
from .models import User, Role
from .auth import auth_bp
from .admin import admin_bp
from .views import views_bp
from .utils import ensure_seed_data, create_backup

# 🛑 الإضافة 2: إنشاء كائن Mail (يتم استخدامه لاحقاً في auth.py)
mail = Mail() 

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    # يجب التأكد أن config.py موجود في المجلد الأب
    app.config.from_pyfile("../config.py") 

    # تهيئة الإضافات
    db.init_app(app)
    mail.init_app(app) # 🛑 الإضافة 3: تهيئة Mail مع التطبيق

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # استرجاع المستخدم من قاعدة البيانات
        return User.query.get(int(user_id))

    # تسجيل المخططات (Blueprints)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(views_bp)

    # إنشاء الجداول والبيانات الأولية
    with app.app_context():
        db.create_all()
        ensure_seed_data()

    return app

def backup_database(app):
    with app.app_context():
        create_backup()