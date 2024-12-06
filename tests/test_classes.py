# tests/test_classes.py

import pytest

from app import db
from app.models import Booking, Class

def login(client, email, password):
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

def test_view_classes(client, app):
    # Вход пользователя
    login(client, 'test1@example.com', 'password1')

    # Просмотр классов
    response = client.get('/classes')
    assert response.status_code == 200
    assert "Yoga" in response.data.decode('utf-8')
    assert "Morning Yoga Class" in response.data.decode('utf-8')

    logout(client)

def test_book_class(client, app):
    # Вход пользователя
    login(client, 'test1@example.com', 'password1')

    # Бронирование класса (предполагается, что class_id=1 соответствует 'Yoga')
    response = client.post('/book/1', follow_redirects=True)
    assert 'Бронирование успешно создано!' in response.data.decode('utf-8')

    # Проверка бронирования в базе данных
    booking = Booking.query.filter_by(user_id=1, class_id=1).first()  # user_id=1 соответствует 'test1@example.com'
    assert booking is not None
    assert booking.status == 'confirmed'

    logout(client)

def test_overbooking(client, app):
    # Вход пользователя
    login(client, 'test1@example.com', 'password1')

    # Устанавливаем вместимость класса 1 на 1 для теста переполнения
    class_ = Class.query.get(1)
    class_.capacity = 1
    db.session.commit()

    # Бронирование класса до заполнения
    for i in range(5):
        response = client.post('/book/1', follow_redirects=True)
        if i < 0:  # Поскольку capacity=1, только первый запрос должен пройти
            assert 'Бронирование успешно создано!' in response.data.decode('utf-8')
        else:
            assert 'Извините, места на этот класс уже заполнены.' in response.data.decode('utf-8')

    logout(client)