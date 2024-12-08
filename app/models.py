# app/models.py

from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    avatar = db.Column(db.String(120), nullable=True, default='user.png')  # Поле для аватара
    date_registered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Дата регистрации
    last_login = db.Column(db.DateTime, nullable=True)  # Последний вход
    bookings = db.relationship('Booking', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Class(db.Model):
    """
    Модель представления классов занятий.

    Атрибуты:
        id (int): Первичный ключ.
        name (str): Название класса.
        description (str): Описание класса.
        schedule (datetime): Дата и время занятия.
        capacity (int): Вместимость класса.
        days_of_week (str): Строка с днями недели (на англ. Mon, Tue...).
        extra_info (str): Дополнительная информация о классе.
        image_filename (str): Имя файла изображения класса, хранящегося в static/images.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    schedule = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, default=10, nullable=False)
    days_of_week = db.Column(db.String(100), nullable=False)
    extra_info = db.Column(db.Text, nullable=True)

    # Новое поле для имени файла изображения класса
    image_filename = db.Column(db.String(100), nullable=True)

    bookings = db.relationship('Booking', backref='class_', lazy=True, cascade='all, delete-orphan')

    def available_slots(self):
        confirmed_bookings = Booking.query.filter_by(class_id=self.id, status='confirmed').count()
        return self.capacity - confirmed_bookings

    @property
    def enrolled_count(self):
        return Booking.query.filter_by(class_id=self.id, status='confirmed').count()

    def __repr__(self):
        return f"Class('{self.name}', '{self.schedule}', Capacity={self.capacity})"




class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='confirmed')  # Статус бронирования
    day = db.Column(db.String(10), nullable=False)  # День недели выбранный пользователем

    def __repr__(self):
        return f"Booking(User ID: {self.user_id}, Class ID: {self.class_id}, Status: {self.status})"


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    stripe_payment_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='paid')

    def __repr__(self):
        return f"Payment(User ID: {self.user_id}, Amount: {self.amount}, Status: {self.status})"





class ActionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Может быть NULL для неавторизованных действий
    action = db.Column(db.String(255), nullable=False)  # Описание действия
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # Для IPv6
    status = db.Column(db.String(20), nullable=True)  # Например, 'success', 'failure'

    user = db.relationship('User', backref=db.backref('action_logs', lazy=True))

    def __repr__(self):
        return f"ActionLog(User ID: {self.user_id}, Action: {self.action}, Timestamp: {self.timestamp}, IP: {self.ip_address}, Status: {self.status})"





