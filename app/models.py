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
    bookings = db.relationship('Booking', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"



class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    schedule = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=10)  # Максимальное количество участников
    bookings = db.relationship('Booking', backref='class_', lazy=True)

    def __repr__(self):
        return f"Class('{self.name}', '{self.schedule}')"

    def available_slots(self):
        return self.capacity - len(self.bookings)




class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    booking_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='confirmed')  # Статус бронирования

    def __repr__(self):
        return f"Booking(User ID: {self.user_id}, Class ID: {self.class_id}, Status: {self.status})"




class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    stripe_payment_id = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"Payment(User ID: {self.user_id}, Amount: {self.amount})"