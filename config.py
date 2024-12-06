import os
from dotenv import load_dotenv




load_dotenv()



class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Используется Flask для сессий и CSRF
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')  # Используется Flask-JWT-Extended
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
