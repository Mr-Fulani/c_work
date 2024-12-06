# app/api/auth.py

import logging
from flask_restful import Resource, reqparse
from flask_jwt_extended import create_access_token
from app.models import User
from app import bcrypt, db
from datetime import timedelta

auth_parser = reqparse.RequestParser()
auth_parser.add_argument('email', type=str, required=True, help='Email is required')
auth_parser.add_argument('password', type=str, required=True, help='Password is required')

class UserLoginResource(Resource):
    def post(self):
        logging.debug("Received login request")
        args = auth_parser.parse_args()
        email = args['email'].strip().lower()
        password = args['password']

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=1))
            logging.debug(f"User {user.id} authenticated successfully")
            return {'access_token': access_token}, 200
        else:
            logging.debug("Invalid credentials provided")
            return {'message': 'Invalid credentials'}, 401