# tests/test_bookings.py

import pytest
from app.models import Booking, Class, User
from flask_jwt_extended import create_access_token
from datetime import datetime, timezone
from app import db, bcrypt  # Правильный импорт

@pytest.fixture
def sample_class(app):
    """
    Фикстура для предоставления доступных классов.
    """
    with app.app_context():
        yoga_class = Class.query.filter_by(name='Yoga').first()
        pilates_class = Class.query.filter_by(name='Pilates').first()
        return yoga_class, pilates_class

@pytest.fixture
def sample_booking(app, user_access_token, sample_class):
    """
    Фикстура для создания тестового бронирования.
    Возвращает booking_id вместо booking instance.
    """
    with app.app_context():
        user = User.query.filter_by(email='test1@example.com').first()
        yoga_class, pilates_class = sample_class
        booking = Booking(
            user_id=int(user.id),
            class_id=yoga_class.id,
            status='confirmed',
            day=yoga_class.schedule.strftime('%A'),  # Установка дня
            booking_date=datetime.now(timezone.utc)
        )
        db.session.add(booking)
        db.session.commit()
        return booking.id  # Return booking_id

def test_get_bookings_user(client, user_access_token, app):
    """
    Тестирование получения списка бронирований для обычного пользователя.
    """
    with app.app_context():
        # Создаём бронирования для пользователя
        user = User.query.filter_by(email='test1@example.com').first()
        yoga_class = Class.query.filter_by(name='Yoga').first()
        pilates_class = Class.query.filter_by(name='Pilates').first()

        booking1 = Booking(
            user_id=int(user.id),
            class_id=yoga_class.id,
            status='confirmed',
            day=yoga_class.schedule.strftime('%A'),  # Установка дня
            booking_date=datetime.now(timezone.utc)
        )
        booking2 = Booking(
            user_id=int(user.id),
            class_id=pilates_class.id,
            status='pending',
            day=pilates_class.schedule.strftime('%A'),  # Установка дня
            booking_date=datetime.now(timezone.utc)
        )
        db.session.add(booking1)
        db.session.add(booking2)
        db.session.commit()

        booking1_id = booking1.id
        booking2_id = booking2.id

    response = client.get(
        "/api/v1/bookings",
        headers={
            "Authorization": f"Bearer {user_access_token}"
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    # Проверяем, что как минимум два бронирования существуют
    assert len(data) >= 2
    # Проверяем наличие наших бронирований в ответе
    booking_ids = [booking['id'] for booking in data]
    assert booking1_id in booking_ids
    assert booking2_id in booking_ids

def test_create_booking_success(client, user_access_token, sample_class, app):
    """
    Тестирование успешного создания бронирования.
    """
    yoga_class, pilates_class = sample_class

    response = client.post(
        "/api/v1/bookings",
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        },
        json={
            "class_id": yoga_class.id,
            "status": "confirmed"
        }
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'Booking created'
    assert 'booking_id' in data

    # Проверяем, что бронирование действительно создано в базе данных
    with app.app_context():
        booking = Booking.query.get(data['booking_id'])
        assert booking is not None
        user = User.query.filter_by(email='test1@example.com').first()
        assert booking.user_id == int(user.id)
        assert booking.class_id == yoga_class.id
        assert booking.status == 'confirmed'
        assert booking.day == yoga_class.schedule.strftime('%A')  # Проверка дня

def test_create_booking_class_not_found(client, user_access_token, app):
    """
    Тестирование создания бронирования для несуществующего класса.
    """
    response = client.post(
        "/api/v1/bookings",
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        },
        json={
            "class_id": 9999,  # Предполагается, что такого класса нет
            "status": "confirmed"
        }
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data['message'] == 'Class not found'

def test_create_booking_no_slots(client, user_access_token, sample_class, app, mocker):
    """
    Тестирование создания бронирования, когда нет доступных слотов.
    """
    yoga_class, pilates_class = sample_class

    # Замокируем метод available_slots, чтобы он возвращал 0
    mocker.patch.object(Class, 'available_slots', return_value=0)

    response = client.post(
        "/api/v1/bookings",
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        },
        json={
            "class_id": yoga_class.id,
            "status": "confirmed"
        }
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data['message'] == 'No available slots for this class'

def test_create_booking_duplicate(client, user_access_token, sample_class, app):
    """
    Тестирование создания дублирующего бронирования.
    """
    yoga_class, pilates_class = sample_class

    with app.app_context():
        user = User.query.filter_by(email='test1@example.com').first()
        booking = Booking(
            user_id=int(user.id),
            class_id=yoga_class.id,
            status='confirmed',
            day=yoga_class.schedule.strftime('%A'),  # Установка дня
            booking_date=datetime.now(timezone.utc)
        )
        db.session.add(booking)
        db.session.commit()

    # Пытаемся создать дублирующее бронирование
    response = client.post(
        "/api/v1/bookings",
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        },
        json={
            "class_id": yoga_class.id,
            "status": "confirmed"
        }
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data['message'] == 'You have already booked this class'

def test_get_booking_detail_owner(client, user_access_token, sample_booking, app):
    """
    Тестирование получения деталей бронирования владельцем.
    """
    booking_id = sample_booking

    response = client.get(
        f"/api/v1/bookings/{booking_id}",
        headers={
            "Authorization": f"Bearer {user_access_token}"
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    with app.app_context():
        booking = Booking.query.get(booking_id)
        assert data['id'] == booking.id
        assert data['class_id'] == booking.class_id
        assert data['status'] == booking.status
        assert data['booking_date'] == booking.booking_date.isoformat()
        assert data['day'] == booking.day

def test_get_booking_detail_non_owner_non_admin(client, user_access_token, sample_booking, app):
    """
    Тестирование получения деталей бронирования другим пользователем без прав администратора.
    """
    with app.app_context():
        # Создаём другого пользователя
        hashed_password = bcrypt.generate_password_hash('password2').decode('utf-8')
        another_user = User(username='anotheruser', email='another@example.com', password=hashed_password, is_admin=False)
        db.session.add(another_user)
        db.session.commit()

        # Генерация токена для другого пользователя
        token = create_access_token(identity=str(another_user.id))

    response = client.get(
        f"/api/v1/bookings/{sample_booking}",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 403
    data = response.get_json()
    assert data['message'] == 'Access denied'

def test_get_booking_detail_admin(client, admin_access_token, sample_booking, app):
    """
    Тестирование получения деталей бронирования администратором.
    """
    booking_id = sample_booking

    response = client.get(
        f"/api/v1/bookings/{booking_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}"
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    with app.app_context():
        booking = Booking.query.get(booking_id)
        assert data['id'] == booking.id
        assert data['class_id'] == booking.class_id
        assert data['status'] == booking.status
        assert data['booking_date'] == booking.booking_date.isoformat()
        assert data['day'] == booking.day

def test_update_booking_status_owner(client, user_access_token, sample_booking, app):
    """
    Тестирование обновления статуса бронирования владельцем.
    """
    booking_id = sample_booking

    response = client.put(
        f"/api/v1/bookings/{booking_id}",
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        },
        json={
            "status": "cancelled"
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Booking updated'

    # Проверяем, что статус обновлён в базе данных
    with app.app_context():
        updated_booking = Booking.query.get(booking_id)
        assert updated_booking.status == 'cancelled'

def test_update_booking_status_non_owner_non_admin(client, user_access_token, sample_booking, app):
    """
    Тестирование обновления статуса бронирования другим пользователем без прав администратора.
    """
    with app.app_context():
        # Создаём другого пользователя
        hashed_password = bcrypt.generate_password_hash('password2').decode('utf-8')
        another_user = User(username='anotheruser', email='another@example.com', password=hashed_password, is_admin=False)
        db.session.add(another_user)
        db.session.commit()

        # Генерация токена для другого пользователя
        token = create_access_token(identity=str(another_user.id))

    response = client.put(
        f"/api/v1/bookings/{sample_booking}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "status": "cancelled"
        }
    )

    assert response.status_code == 403
    data = response.get_json()
    assert data['message'] == 'Access denied'

def test_update_booking_status_admin(client, admin_access_token, sample_booking, app):
    """
    Тестирование обновления статуса бронирования администратором.
    """
    booking_id = sample_booking

    response = client.put(
        f"/api/v1/bookings/{booking_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}",
            "Content-Type": "application/json"
        },
        json={
            "status": "completed"
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Booking updated'

    # Проверяем, что статус обновлён в базе данных
    with app.app_context():
        updated_booking = Booking.query.get(booking_id)
        assert updated_booking.status == 'completed'

def test_delete_booking_owner(client, user_access_token, sample_booking, app):
    """
    Тестирование удаления бронирования владельцем.
    """
    booking_id = sample_booking

    response = client.delete(
        f"/api/v1/bookings/{booking_id}",
        headers={
            "Authorization": f"Bearer {user_access_token}"
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Booking deleted'

    # Проверяем, что бронирование удалено из базы данных
    with app.app_context():
        deleted_booking = Booking.query.get(booking_id)
        assert deleted_booking is None

def test_delete_booking_non_owner_non_admin(client, user_access_token, sample_booking, app):
    """
    Тестирование удаления бронирования другим пользователем без прав администратора.
    """
    with app.app_context():
        # Создаём другого пользователя
        hashed_password = bcrypt.generate_password_hash('password2').decode('utf-8')
        another_user = User(username='anotheruser', email='another@example.com', password=hashed_password, is_admin=False)
        db.session.add(another_user)
        db.session.commit()

        # Генерация токена для другого пользователя
        token = create_access_token(identity=str(another_user.id))

    response = client.delete(
        f"/api/v1/bookings/{sample_booking}",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 403
    data = response.get_json()
    assert data['message'] == 'Access denied'

def test_delete_booking_admin(client, admin_access_token, sample_booking, app):
    """
    Тестирование удаления бронирования администратором.
    """
    booking_id = sample_booking

    response = client.delete(
        f"/api/v1/bookings/{booking_id}",
        headers={
            "Authorization": f"Bearer {admin_access_token}"
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Booking deleted'

    # Проверяем, что бронирование удалено из базы данных
    with app.app_context():
        deleted_booking = Booking.query.get(booking_id)
        assert deleted_booking is None

def test_create_booking_missing_class_id(client, user_access_token):
    """
    Тестирование создания бронирования без указания class_id.
    """
    response = client.post(
        "/api/v1/bookings",
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        },
        json={
            # "class_id": 1,  # Отсутствует
            "status": "confirmed"
        }
    )

    assert response.status_code == 400
    data = response.get_json()
    # Flask-RESTful использует сообщения в формате 'field: error message'
    assert 'class_id' in data['message']

def test_update_booking_status_missing_status(client, user_access_token, sample_booking, app):
    """
    Тестирование обновления статуса бронирования без указания нового статуса.
    """
    booking_id = sample_booking

    response = client.put(
        f"/api/v1/bookings/{booking_id}",
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        },
        json={
            # "status": "cancelled"  # Отсутствует
        }
    )

    assert response.status_code == 400
    data = response.get_json()
    # Flask-RESTful использует сообщения в формате 'field: error message'
    assert 'status' in data['message']

def test_get_non_existing_booking(client, user_access_token):
    """
    Тестирование получения несуществующего бронирования.
    """
    response = client.get(
        "/api/v1/bookings/9999",  # Предполагается, что такого бронирования нет
        headers={
            "Authorization": f"Bearer {user_access_token}"
        }
    )

    assert response.status_code == 404

def test_update_non_existing_booking(client, user_access_token):
    """
    Тестирование обновления несуществующего бронирования.
    """
    response = client.put(
        "/api/v1/bookings/9999",  # Предполагается, что такого бронирования нет
        headers={
            "Authorization": f"Bearer {user_access_token}",
            "Content-Type": "application/json"
        },
        json={
            "status": "cancelled"
        }
    )

    assert response.status_code == 404

def test_delete_non_existing_booking(client, user_access_token):
    """
    Тестирование удаления несуществующего бронирования.
    """
    response = client.delete(
        "/api/v1/bookings/9999",  # Предполагается, что такого бронирования нет
        headers={
            "Authorization": f"Bearer {user_access_token}"
        }
    )

    assert response.status_code == 404