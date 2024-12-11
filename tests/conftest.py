# tests/conftest.py

import pytest
from flask_jwt_extended import create_access_token
from app import create_app, db, bcrypt
from config_test import TestConfig
from app.models import User, Class
from datetime import datetime, timedelta

@pytest.fixture(scope='function')
def app():
    """
    Фикстура Flask приложения с функцией области действия.
    """
    app = create_app(config_class=TestConfig)

    with app.app_context():
        db.create_all()

        # Хеширование паролей
        hashed_password1 = bcrypt.generate_password_hash('password1').decode('utf-8')
        hashed_password2 = bcrypt.generate_password_hash('adminpassword').decode('utf-8')

        # Создание тестовых пользователей
        user1 = User(username='testuser1', email='test1@example.com', password=hashed_password1, is_admin=False)
        user2 = User(username='adminuser', email='admin@example.com', password=hashed_password2, is_admin=True)
        db.session.add(user1)
        db.session.add(user2)

        # Создание тестовых классов
        class1 = Class(
            name='Yoga',
            description='Morning Yoga Class',
            schedule=datetime.now() + timedelta(days=1),
            capacity=10,
            days_of_week='Monday,Wednesday'  # Заполнение обязательного поля
        )
        class2 = Class(
            name='Pilates',
            description='Evening Pilates Class',
            schedule=datetime.now() + timedelta(days=1, hours=10),
            capacity=15,
            days_of_week='Tuesday,Thursday'  # Заполнение обязательного поля
        )
        db.session.add(class1)
        db.session.add(class2)

        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()



@pytest.fixture(scope='function')
def client(app):
    """
    Фикстура клиентского приложения для тестирования.
    """
    return app.test_client()



@pytest.fixture(scope='function')
def user_access_token(app):
    """
    Фикстура для генерации JWT-токена для обычного пользователя.
    """
    with app.app_context():
        user = User.query.filter_by(email='test1@example.com').first()
        if not user:
            # Создание пользователя, если он не существует
            hashed_password = bcrypt.generate_password_hash('password1').decode('utf-8')
            user = User(username='testuser1', email='test1@example.com', password=hashed_password, is_admin=False)
            db.session.add(user)
            db.session.commit()

        # Генерация токена с идентификатором пользователя как строкой
        token = create_access_token(identity=str(user.id))
        return token

@pytest.fixture(scope='function')
def admin_access_token(app):
    """
    Фикстура для генерации JWT-токена для администратора.
    """
    with app.app_context():
        admin_user = User.query.filter_by(email='admin@example.com').first()
        if not admin_user:
            # Создание администратора, если он не существует
            hashed_password = bcrypt.generate_password_hash('adminpassword').decode('utf-8')
            admin_user = User(username='adminuser', email='admin@example.com', password=hashed_password, is_admin=True)
            db.session.add(admin_user)
            db.session.commit()

        # Генерация токена с идентификатором администратора как строкой
        token = create_access_token(identity=str(admin_user.id))
        return token





