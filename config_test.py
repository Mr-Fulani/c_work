import os



class TestConfig:
    SECRET_KEY = 'test_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    TESTING = True
    WTF_CSRF_ENABLED = False  # Отключение CSRF для тестов