# app/__init__.py
import logging
import os

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from config import Config
from flask_migrate import Migrate

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'
mail = Mail()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Разрешение CORS
    CORS(app)

    # Настройка логирования
    logging.basicConfig(level=logging.DEBUG)

    # Настройка JWT
    jwt.init_app(app)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    from app.routes import main_bp
    from app.admin_routes import admin_bp
    from app.api import api_bp  # Предполагается, что api_bp определён в app/api.py

    # Регистрация Blueprint'ов только один раз
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    from app import models  # Импорт моделей для Alembic

    return app