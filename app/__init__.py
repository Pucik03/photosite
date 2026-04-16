from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv
from config import Config
import os

db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = 'admin.login'


def create_app():
    load_dotenv()

    app = Flask(__name__)

    # 🔥 ВАЖНО — загружаем весь config
    app.config.from_object(Config)

    # Если хочешь переопределить через .env:
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", app.config['SECRET_KEY'])

    # Инициализация расширений
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Регистрация blueprints
    from app.routes.public import public_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


from app.models import Admin


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))