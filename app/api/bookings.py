# app/api/bookings.py

from flask_restful import Resource, reqparse
from flask import request
from app import db
from app.models import Booking, User, Class
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

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
        bookings = Booking.query.filter_by(user_id=user_id).all()
        return [{'id': b.id, 'class_id': b.class_id, 'status': b.status, 'booking_date': b.booking_date.isoformat()} for b in bookings], 200

    @jwt_required()
    def post(self):
        """
        Создать новое бронирование
        """
        args = booking_parser.parse_args()
        class_ = Class.query.get(args['class_id'])
        if not class_:
            return {'message': 'Class not found'}, 404

        if class_.available_slots() <= 0:
            return {'message': 'No available slots for this class'}, 400

        # Проверка, уже есть ли бронирование на этот класс
        user_id = get_jwt_identity()
        existing_booking = Booking.query.filter_by(user_id=user_id, class_id=class_.id).first()
        if existing_booking:
            return {'message': 'You have already booked this class'}, 400

        booking = Booking(user_id=user_id, class_id=class_.id, status=args['status'])
        db.session.add(booking)
        db.session.commit()

        return {'message': 'Booking created', 'booking_id': booking.id}, 201

class BookingResource(Resource):
    @jwt_required()
    def get(self, booking_id):
        """
        Получить детали конкретного бронирования
        """
        user_id = get_jwt_identity()
        booking = Booking.query.get_or_404(booking_id)
        user = User.query.get(user_id)
        if booking.user_id != user_id and not user.is_admin:
            return {'message': 'Access denied'}, 403

        return {
            'id': booking.id,
            'class_id': booking.class_id,
            'status': booking.status,
            'booking_date': booking.booking_date.isoformat()
        }, 200

    @jwt_required()
    def put(self, booking_id):
        """
        Обновить статус бронирования
        """
        user_id = get_jwt_identity()
        booking = Booking.query.get_or_404(booking_id)
        user = User.query.get(user_id)
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
        user_id = get_jwt_identity()
        booking = Booking.query.get_or_404(booking_id)
        user = User.query.get(user_id)
        if booking.user_id != user_id and not user.is_admin:
            return {'message': 'Access denied'}, 403

        db.session.delete(booking)
        db.session.commit()

        return {'message': 'Booking deleted'}, 200