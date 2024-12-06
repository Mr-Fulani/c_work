from datetime import datetime, timezone

import pytest
from app.models import Booking, Class
from app import db


def test_api_login_success(client):
    """
    Тест успешного получения JWT токена
    """
    response = client.post('/api/v1/login', json={
        'email': 'test1@example.com',
        'password': 'password1'  # Пароль должен соответствовать фикстуре
    })
    assert response.status_code == 200, f"Ожидался статус код 200, получен {response.status_code}"
    json_data = response.get_json()
    assert 'access_token' in json_data, "Поле 'access_token' отсутствует в ответе"


def test_api_login_wrong_credentials(client):
    """
    Тест получения JWT токена с неверными учетными данными
    """
    response = client.post('/api/v1/login', json={
        'email': 'test1@example.com',
        'password': 'WrongPassword'
    })
    assert response.status_code == 401, f"Ожидался статус код 401, получен {response.status_code}"
    json_data = response.get_json()
    assert json_data['message'] == 'Invalid credentials', f"Ожидалось сообщение 'Invalid credentials', получено '{json_data.get('message')}'"


def test_create_booking(client, access_token):
    """
    Тест создания нового бронирования через API
    """
    class_ = Class.query.filter_by(name='Yoga').first()
    assert class_ is not None, "Класс 'Yoga' не найден в базе данных"
    class_id = class_.id

    response = client.post('/api/v1/bookings', json={
        'class_id': class_id,
        'status': 'confirmed',
        'booking_date': datetime.now(timezone.utc).isoformat()
    }, headers={
        'Authorization': f'Bearer {access_token}'
    })

    assert response.status_code == 201, f"Ожидался статус код 201, получен {response.status_code}. Данные ответа: {response.get_json()}"
    json_data = response.get_json()
    assert json_data['message'] == 'Booking created', "Сообщение о создании бронирования отсутствует"
    assert 'booking_id' in json_data, "Поле 'booking_id' отсутствует в ответе"

    booking = Booking.query.get(json_data['booking_id'])
    assert booking is not None, "Бронирование не найдено в базе данных"
    assert booking.class_id == class_id, "class_id бронирования не совпадает"
    assert booking.status == 'confirmed', "Статус бронирования не совпадает"


def test_create_booking_no_slots(client, access_token):
    """
    Тест создания бронирования, когда места закончились
    """
    class_ = Class.query.filter_by(name='Yoga').first()
    assert class_ is not None, "Класс 'Yoga' не найден в базе данных"

    original_capacity = class_.capacity
    class_.capacity = 1
    db.session.commit()

    booking = Booking(user_id=1, class_id=class_.id, status='confirmed', booking_date=datetime.now(timezone.utc))
    db.session.add(booking)
    db.session.commit()

    response = client.post('/api/v1/bookings', json={
        'class_id': class_.id,
        'status': 'confirmed',
        'booking_date': datetime.now(timezone.utc).isoformat()
    }, headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 400, f"Ожидался статус код 400, получен {response.status_code}. Данные ответа: {response.get_json()}"
    json_data = response.get_json()
    assert json_data['message'] == 'No available slots for this class', f"Ожидалось сообщение 'No available slots for this class', получено '{json_data.get('message')}'"

    class_.capacity = original_capacity
    db.session.commit()


def test_get_bookings(client, access_token):
    """
    Тест получения списка бронирований текущего пользователя через API
    """
    booking = Booking.query.filter_by(user_id=1, class_id=1).first()
    if not booking:
        booking = Booking(user_id=1, class_id=1, status='confirmed', booking_date=datetime.now(timezone.utc))
        db.session.add(booking)
        db.session.commit()

    response = client.get('/api/v1/bookings', headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 200, f"Ожидался статус код 200, получен {response.status_code}"
    json_data = response.get_json()
    assert isinstance(json_data, list), "Ожидался список бронирований"
    assert len(json_data) >= 1, "Ожидалось хотя бы одно бронирование"


def test_get_specific_booking(client, access_token):
    """
    Тест получения деталей конкретного бронирования через API
    """
    booking = Booking(user_id=1, class_id=2, status='confirmed', booking_date=datetime.now(timezone.utc))
    db.session.add(booking)
    db.session.commit()

    response = client.get(f'/api/v1/bookings/{booking.id}', headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 200, f"Ожидался статус код 200, получен {response.status_code}"
    json_data = response.get_json()
    assert json_data['id'] == booking.id, "ID бронирования не совпадает"
    assert json_data['class_id'] == 2, "class_id бронирования не совпадает"
    assert json_data['status'] == 'confirmed', "Статус бронирования не совпадает"


def test_update_booking(client, access_token):
    """
    Тест обновления статуса бронирования через API
    """
    booking = Booking(user_id=1, class_id=2, status='confirmed', booking_date=datetime.now(timezone.utc))
    db.session.add(booking)
    db.session.commit()

    response = client.put(f'/api/v1/bookings/{booking.id}', json={
        'status': 'cancelled'
    }, headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 200, f"Ожидался статус код 200, получен {response.status_code}"
    json_data = response.get_json()
    assert json_data['message'] == 'Booking updated', "Сообщение об обновлении бронирования отсутствует"

    updated_booking = Booking.query.get(booking.id)
    assert updated_booking.status == 'cancelled', "Статус бронирования не был обновлён"


def test_delete_booking(client, access_token):
    """
    Тест удаления бронирования через API
    """
    booking = Booking(user_id=1, class_id=2, status='confirmed', booking_date=datetime.now(timezone.utc))
    db.session.add(booking)
    db.session.commit()

    response = client.delete(f'/api/v1/bookings/{booking.id}', headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 200, f"Ожидался статус код 200, получен {response.status_code}"
    json_data = response.get_json()
    assert json_data['message'] == 'Booking deleted', "Сообщение об удалении бронирования отсутствует"

    deleted_booking = Booking.query.get(booking.id)
    assert deleted_booking is None, "Бронирование не было удалено из базы данных"


def test_api_access_without_token(client):
    """
    Тест доступа к API без JWT токена
    """
    response = client.get('/api/v1/bookings', headers={
        'Authorization': 'Bearer '  # Отправляем пустой токен
    })
    assert response.status_code == 422, f"Ожидался статус код 422, получен {response.status_code}"
    json_data = response.get_json()
    assert json_data['msg'] == 'Not enough segments', f"Ожидалось сообщение 'Not enough segments', получено '{json_data.get('msg')}'"


def test_api_access_with_invalid_token(client):
    """
    Тест доступа к API с неверным JWT токеном
    """
    response = client.get('/api/v1/bookings', headers={
        'Authorization': 'Bearer invalidtoken'
    })
    assert response.status_code == 422, f"Ожидался статус код 422, получен {response.status_code}"
    json_data = response.get_json()
    assert json_data['msg'] == 'Not enough segments', f"Ожидалось сообщение 'Not enough segments', получено '{json_data.get('msg')}'"


def test_api_admin_access(client, admin_access_token):
    """
    Тест доступа администратора к бронированиям других пользователей
    """
    booking = Booking(user_id=1, class_id=2, status='confirmed', booking_date=datetime.now(timezone.utc))
    db.session.add(booking)
    db.session.commit()

    response = client.get(f'/api/v1/bookings/{booking.id}', headers={
        'Authorization': f'Bearer {admin_access_token}'
    })
    assert response.status_code == 200, f"Ожидался статус код 200, получен {response.status_code}"
    json_data = response.get_json()
    assert json_data['id'] == booking.id, "ID бронирования не совпадает"
    assert json_data['user_id'] == 1, "user_id бронирования не совпадает"


def test_api_non_admin_access_to_others_booking(client, access_token):
    """
    Тест попытки пользователя получить бронирование другого пользователя
    """
    booking = Booking(user_id=2, class_id=2, status='confirmed', booking_date=datetime.now(timezone.utc))
    db.session.add(booking)
    db.session.commit()

    response = client.get(f'/api/v1/bookings/{booking.id}', headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 403, f"Ожидался статус код 403, получен {response.status_code}"
    json_data = response.get_json()
    assert json_data['message'] == 'Access denied', f"Ожидалось сообщение 'Access denied', получено '{json_data.get('message')}'"
