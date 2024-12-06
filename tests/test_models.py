# tests/test_models.py
from app import db
from app.models import User, Class, Booking, Payment


def test_user_model(app):
    """
    Тест модели пользователя.
    """
    with app.app_context():
        user = User.query.filter_by(email='test1@example.com').first()
        assert user is not None
        assert user.username == 'testuser1'

def test_admin_user_model(app):
    """
    Тест модели администратора.
    """
    with app.app_context():
        admin = User.query.filter_by(email='admin@example.com').first()
        assert admin is not None
        assert admin.username == 'adminuser'
        assert admin.is_admin == True

def test_class_model(app):
    """
    Тест модели класса.
    """
    with app.app_context():
        class_ = Class.query.filter_by(name='Yoga').first()
        assert class_ is not None
        assert class_.capacity == 10

def test_booking_model(app):
    """
    Тест модели бронирования.
    """
    with app.app_context():
        user = User.query.filter_by(email='test1@example.com').first()
        class_ = Class.query.filter_by(name='Yoga').first()
        booking = Booking(user_id=user.id, class_id=class_.id, status='confirmed')
        db.session.add(booking)
        db.session.commit()

        fetched_booking = Booking.query.filter_by(user_id=user.id, class_id=class_.id).first()
        assert fetched_booking is not None
        assert fetched_booking.status == 'confirmed'



def test_payment_model(app):
    """
    Тест модели платежа.
    """
    with app.app_context():
        user = User.query.filter_by(email='test1@example.com').first()
        payment = Payment(user_id=user.id, amount=100.0, stripe_payment_id='stripe_12345')
        db.session.add(payment)
        db.session.commit()

        fetched_payment = Payment.query.filter_by(user_id=user.id).first()
        assert fetched_payment is not None
        assert fetched_payment.amount == 100.0
        assert fetched_payment.status == 'paid'  # Убедитесь, что статус 'paid' устанавливается корректно