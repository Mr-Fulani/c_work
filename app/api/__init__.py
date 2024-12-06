# app/api/__init__.py

from flask import Blueprint
from flask_restful import Api

from .payments import PaymentResource

api_bp = Blueprint('api', __name__)
api = Api(api_bp, prefix='/v1')

from .bookings import BookingListResource, BookingResource
from .auth import UserLoginResource

# Регистрация ресурсов
api.add_resource(BookingListResource, '/bookings')
api.add_resource(BookingResource, '/bookings/<int:booking_id>')
api.add_resource(UserLoginResource, '/login')
api.add_resource(PaymentResource, '/payment')
