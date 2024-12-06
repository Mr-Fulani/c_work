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
    bookings = db.relationship('Booking', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    schedule = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, default=10, nullable=False)

    # Новые поля
    days_of_week = db.Column(db.String(100), nullable=False)  # Например: "Пн, Ср, Пт"
    extra_info = db.Column(db.Text, nullable=True)  # Дополнительная информация

    bookings = db.relationship('Booking', backref='class_', lazy=True)

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