# app/api/bookings.py

from flask_restful import Resource, reqparse
from flask import request
from app import db
from app.models import Booking, User, Class
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone

# Парсер для POST-запросов
booking_parser = reqparse.RequestParser()
booking_parser.add_argument('class_id', type=int, required=True, help='Class ID is required')
booking_parser.add_argument('status', type=str, default='confirmed')

class BookingListResource(Resource):
    @jwt_required()
    def get(self):
        """
        Получить список всех бронирований текущего пользователя
        """
        user_id = get_jwt_identity()
        try:
            user_id = int(user_id)
        except ValueError:
            return {"message": "Invalid token"}, 400

        bookings = Booking.query.filter_by(user_id=user_id).all()
        return [
            {
                'id': b.id,
                'class_id': b.class_id,
                'status': b.status,
                'booking_date': b.booking_date.isoformat(),
                'day': b.day
            } for b in bookings
        ], 200

    @jwt_required()
    def post(self):
        """
        Создать новое бронирование
        """
        args = booking_parser.parse_args()
        try:
            user_id = int(get_jwt_identity())
        except ValueError:
            return {"message": "Invalid token"}, 400

        # Используем db.session.get() вместо Query.get()
        class_ = db.session.get(Class, args['class_id'])
        if not class_:
            return {'message': 'Class not found'}, 404

        if class_.available_slots() <= 0:
            return {'message': 'No available slots for this class'}, 400

        # Проверка, уже есть ли бронирование на этот класс
        existing_booking = Booking.query.filter_by(user_id=user_id, class_id=class_.id).first()
        if existing_booking:
            return {'message': 'You have already booked this class'}, 400

        # Установка поля 'day' на основе расписания класса
        day = class_.schedule.strftime('%A')  # Например, 'Monday'

        booking = Booking(
            user_id=user_id,
            class_id=class_.id,
            status=args['status'],
            day=day,
            booking_date=datetime.now(timezone.utc)
        )
        db.session.add(booking)
        db.session.commit()

        return {'message': 'Booking created', 'booking_id': booking.id}, 201

class BookingResource(Resource):
    @jwt_required()
    def get(self, booking_id):
        """
        Получить детали конкретного бронирования
        """
        try:
            user_id = int(get_jwt_identity())
        except ValueError:
            return {"message": "Invalid token"}, 400

        # Используем db.session.get() вместо Query.get()
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return {'message': 'Booking not found'}, 404

        user = db.session.get(User, user_id)
        if booking.user_id != user_id and not user.is_admin:
            return {'message': 'Access denied'}, 403

        return {
            'id': booking.id,
            'class_id': booking.class_id,
            'status': booking.status,
            'booking_date': booking.booking_date.isoformat(),
            'day': booking.day
        }, 200

    @jwt_required()
    def put(self, booking_id):
        """
        Обновить статус бронирования
        """
        try:
            user_id = int(get_jwt_identity())
        except ValueError:
            return {"message": "Invalid token"}, 400

        booking = db.session.get(Booking, booking_id)
        if not booking:
            return {'message': 'Booking not found'}, 404

        user = db.session.get(User, user_id)
        if booking.user_id != user_id and not user.is_admin:
            return {'message': 'Access denied'}, 403

        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str, required=True, help='Status is required')
        data = parser.parse_args()

        booking.status = data['status']
        db.session.commit()

        return {'message': 'Booking updated'}, 200

    @jwt_required()
    def delete(self, booking_id):
        """
        Удалить бронирование
        """
        try:
            user_id = int(get_jwt_identity())
        except ValueError:
            return {"message": "Invalid token"}, 400

        booking = db.session.get(Booking, booking_id)
        if not booking:
            return {'message': 'Booking not found'}, 404

        user = db.session.get(User, user_id)
        if booking.user_id != user_id and not user.is_admin:
            return {'message': 'Access denied'}, 403

        db.session.delete(booking)
        db.session.commit()

        return {'message': 'Booking deleted'}, 200