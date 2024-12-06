# tests/test_admin.py

from datetime import datetime, timedelta
from app.models import Class
import pytest

def login(client, email, password):
    """
    Вспомогательная функция для входа пользователя.
    """
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

def logout(client):
    """
    Вспомогательная функция для выхода пользователя.
    """
    return client.get('/logout', follow_redirects=True)


def test_admin_access(client, app):
    """
    Тест доступа к админ-панели.
    """
    # Вход как обычный пользователь
    login_response = login(client, 'test1@example.com', 'password1')
    response = client.get('/admin', follow_redirects=True)

    # Проверка статуса ответа
    assert response.status_code == 403, "Ожидался статус код 403 Forbidden"

    # Проверка наличия английского сообщения 'Forbidden' в ответе
    assert 'Forbidden' in response.data.decode('utf-8'), "Ожидалось сообщение 'Forbidden' в ответе"

    logout(client)

    # Вход как администратор с правильным паролем
    login_response = login(client, 'admin@example.com', 'adminpassword')  # Исправленный пароль
    response = client.get('/admin', follow_redirects=True)

    # Проверка статуса ответа
    assert response.status_code == 200, "Ожидался статус код 200 OK для администратора"

    # Проверка наличия строки 'Панель Администратора' или аналогичного сообщения в ответе
    assert 'Панель Администратора' in response.data.decode('utf-8'), "Ожидалось сообщение 'Панель Администратора' в ответе"

    logout(client)


def test_add_class(client, app):
    """
    Тест добавления нового класса администратором.
    """
    # Вход как администратор
    login_response = login(client, 'admin@example.com', 'adminpassword')  # Исправленный пароль

    # Добавление нового класса
    response = client.post('/admin/add_class', data={
        'name': 'Новый Класс',
        'description': 'Описание нового класса.',
        'schedule': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
        'capacity': 10
    }, follow_redirects=True)
    assert 'Новый класс успешно добавлен.' in response.data.decode('utf-8'), "Сообщение об успешном добавлении класса отсутствует"

    # Проверка в базе данных
    with app.app_context():
        new_class = Class.query.filter_by(name='Новый Класс').first()
        assert new_class is not None, "Новый класс не найден в базе данных"

    logout(client)


def test_edit_class(client, app):
    """
    Тест редактирования существующего класса администратором.
    """
    # Вход как администратор
    login_response = login(client, 'admin@example.com', 'adminpassword')  # Исправленный пароль

    # Редактирование существующего класса (предполагается, что класс с id=1 существует)
    response = client.post('/admin/edit_class/1', data={
        'name': 'Отредактированный Класс',
        'description': 'Обновленное описание.',
        'schedule': (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M'),
        'capacity': 8
    }, follow_redirects=True)
    assert 'Класс успешно обновлён.' in response.data.decode('utf-8'), "Сообщение об успешном обновлении класса отсутствует"

    # Проверка изменений в базе данных
    with app.app_context():
        edited_class = Class.query.get(1)
        assert edited_class.name == 'Отредактированный Класс', "Имя класса не было обновлено"
        assert edited_class.capacity == 8, "Вместимость класса не была обновлена"

    logout(client)


def test_delete_class(client, app):
    """
    Тест удаления существующего класса администратором.
    """
    # Вход как администратор
    login_response = login(client, 'admin@example.com', 'adminpassword')  # Исправленный пароль

    # Удаление существующего класса (предполагается, что класс с id=1 существует)
    response = client.post('/admin/delete_class/1', follow_redirects=True)
    assert 'Класс успешно удалён.' in response.data.decode('utf-8'), "Сообщение об успешном удалении класса отсутствует"

    # Проверка удаления в базе данных
    with app.app_context():
        deleted_class = Class.query.get(1)
        assert deleted_class is None, "Класс не был удалён из базы данных"

    logout(client)


