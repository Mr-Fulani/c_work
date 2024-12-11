# app/__init__.py

import logging
import os

from flask import Flask, abort, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail

from app.webhooks import webhook_bp
from config import Config
from flask_migrate import Migrate

# Initialize Limiter for rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

# Initialize Flask extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'
migrate = Migrate()
jwt = JWTManager()
mail = Mail()

def create_app(config_class=Config):
    """
    Factory function to create a Flask application instance.

    The application settings are taken from config_class.
    Initializes extensions: db, bcrypt, login_manager, mail, migrations, JWT.
    Registers blueprints.

    Args:
        config_class (class): The configuration class to use for the application.

    Returns:
        Flask: The initialized Flask application instance.
    """
    app = Flask(__name__, static_url_path='/static')
    app.config.from_object(config_class)

    # Enable Cross-Origin Resource Sharing (CORS)
    CORS(app)

    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.info("Initializing Flask application.")

    # Flask-Mail configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', ('c_work Support', 'noreply@yourdomain.com'))

    # Initialize JWT
    jwt.init_app(app)

    # Initialize other extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Image upload settings
    # Folder where class images will be saved
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'images')
    # Allowed file extensions for uploads
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
    # Maximum file size allowed for uploads: 16 MB
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    from app.routes import main_bp
    from app.admin_routes import admin_bp
    from app.api import api_bp  # Assumes api_bp is defined in app/api.py

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(webhook_bp)

    from app import models  # Import models for Alembic

    # # Enable JWT authentication for API routes
    # @app.before_request
    # def before_request_func():
    #     """
    #     Apply JWT verification only to API routes.
    #     """
    #     if request.path.startswith('/api/'):
    #         try:
    #             verify_jwt_in_request()
    #         except:
    #             abort(403)  # Forbidden

    # Log all registered routes for debugging purposes
    with app.app_context():
        for rule in app.url_map.iter_rules():
            logger.debug(f"Route: {rule.rule} -> {rule.endpoint}")

    return app
