# tests/conftest.py
import os

import pytest
from app import create_app, db, bcrypt
from config_test import TestConfig, TEMP_DB
from app.models import User, Class
from flask_jwt_extended import create_access_token
from datetime import datetime, timedelta

@pytest.fixture(scope='function')
def app():
    """
    Фикстура Flask-приложения с областью действия функции.
    """
    app = create_app(config_class=TestConfig)

    with app.app_context():
        db.create_all()

        # Хеширование паролей перед добавлением в базу данных
        hashed_password1 = bcrypt.generate_password_hash('password1').decode('utf-8')
        hashed_password2 = bcrypt.generate_password_hash('adminpassword').decode('utf-8')

        # Создание тестовых пользователей
        user1 = User(username='testuser1', email='test1@example.com', password=hashed_password1, is_admin=False)
        user2 = User(username='adminuser', email='admin@example.com', password=hashed_password2, is_admin=True)
        db.session.add(user1)
        db.session.add(user2)

        # Создание тестовых классов
        class1 = Class(name='Yoga', description='Morning Yoga Class', schedule=datetime.now() + timedelta(days=1), capacity=10)
        class2 = Class(name='Pilates', description='Evening Pilates Class', schedule=datetime.now() + timedelta(days=1, hours=10), capacity=15)
        db.session.add(class1)
        db.session.add(class2)

        db.session.commit()

        # Отладочный вывод для подтверждения создания классов
        classes = Class.query.all()
        print(f"Classes in DB: {[c.name for c in classes]}")

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """
    Фикстура тестового клиента Flask-приложения.
    """
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """
    Фикстура для вызова команд через Click.
    """
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def access_token(app):
    """
    Фикстура для получения JWT токена для обычного пользователя.
    """
    with app.app_context():
        user = User.query.filter_by(email='test1@example.com').first()
        token = create_access_token(identity=str(user.id))
        print(f"Access token for tests: {token}")
        return token

@pytest.fixture(scope='function')
def admin_access_token(app):
    """
    Фикстура для получения JWT токена для администратора.
    """
    with app.app_context():
        admin = User.query.filter_by(email='admin@example.com').first()
        token = create_access_token(identity=admin.id)
        return token






@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db():
    """
    Удаляет временную базу данных после завершения всех тестов.
    """
    yield  # Выполнение всех тестов

    # Удаление временной базы данных
    try:
        if os.path.exists(TEMP_DB.name):
            os.unlink(TEMP_DB.name)
            print(f"Тестовая база данных {TEMP_DB.name} удалена.")
    except Exception as e:
        print(f"Не удалось удалить временную базу данных: {e}")