import os
import tempfile


# Создаем временный файл для базы данных
TEMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)


class TestConfig:
    SECRET_KEY = 'test_secret_key'
    JWT_SECRET_KEY = 'test_jwt_secret_key'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEMP_DB.name}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True  # Включает вывод SQL-запросов для отладки
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER', 'test_email_user')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS', 'test_email_pass')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'test_stripe_secret_key')
    TESTING = True
    WTF_CSRF_ENABLED = False  # Отключение CSRF для тестов