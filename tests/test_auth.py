# tests/test_auth.py

import pytest
from app import create_app, db
from app.models import User
from flask import url_for


@pytest.fixture
def app():
    app = create_app(config_class='config_test.TestConfig')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_register(client):
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password'
    }, follow_redirects=True)
    assert b'Ваш аккаунт создан!' in response.data
    user = User.query.filter_by(email='test@example.com').first()
    assert user is not None


def test_login_logout(client):
    # Сначала зарегистрируем пользователя
    client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password'
    }, follow_redirects=True)

    # Входим
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'password'
    }, follow_redirects=True)
    assert b'Вы вошли в систему!' in response.data

    # Выходим
    response = client.get('/logout', follow_redirects=True)
    assert b'Добро пожаловать!' in response.data