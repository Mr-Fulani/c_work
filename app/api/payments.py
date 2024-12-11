# app/api/payments.py

import logging
from flask_restful import Resource
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Payment
from app import db
import stripe

class PaymentResource(Resource):
    @jwt_required()
    def post(self):
        try:
            logging.debug("Received payment request")
            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            logging.debug(f"Stripe API Key set: {stripe.api_key}")

            current_user_id = get_jwt_identity()
            logging.debug(f"Current User ID from JWT: {current_user_id}")

            try:
                current_user_id = int(current_user_id)
            except ValueError:
                logging.error(f"Invalid user ID in JWT: {current_user_id}")
                return {"success": False, "error": "Invalid token"}, 400

            user = User.query.get(current_user_id)
            if not user:
                logging.error(f"User with ID {current_user_id} not found")
                return {"success": False, "error": "User not found"}, 404

            data = request.get_json()
            logging.debug(f"Request Data: {data}")

            amount = data.get('amount')
            currency = data.get('currency', 'gbp')
            description = data.get('description', 'Payment for services')
            payment_method_id = data.get('payment_method_id')

            logging.debug(f"Payment Details - Amount: {amount}, Currency: {currency}, Description: {description}, Payment Method ID: {payment_method_id}")

            # Проверка входных данных
            if not isinstance(amount, int) or amount <= 0:
                logging.error("Invalid amount")
                return {'success': False, 'error': 'Invalid amount'}, 400

            if not payment_method_id or not isinstance(payment_method_id, str):
                logging.error("Invalid payment_method_id")
                return {'success': False, 'error': 'Invalid payment_method_id'}, 400

            # Создание PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                description=description,
                payment_method=payment_method_id,
                confirm=True
            )
            logging.debug(f"PaymentIntent created: {intent}")

            # Сохранение платежа в базе данных
            payment = Payment(
                user_id=user.id,
                amount=amount,
                stripe_payment_id=intent.id,
                status=intent.status
            )
            db.session.add(payment)
            db.session.commit()
            logging.debug(f"Payment saved to DB: {payment}")

            return {
                'success': True,
                'client_secret': intent.client_secret,
                'status': intent.status,
                'charges': intent.charges.data
            }, 200

        except stripe.error.CardError as e:
            logging.error(f"Card declined: {e}")
            return {'success': False, 'error': 'Card declined'}, 402
        except stripe.error.RateLimitError as e:
            logging.error(f"Rate limit error: {e}")
            return {'success': False, 'error': 'Rate limit error'}, 429
        except stripe.error.InvalidRequestError as e:
            logging.error(f"Invalid parameters: {e}")
            return {'success': False, 'error': 'Invalid request'}, 400
        except stripe.error.AuthenticationError as e:
            logging.error(f"Authentication error: {e}")
            return {'success': False, 'error': 'Authentication failed'}, 401
        except stripe.error.APIConnectionError as e:
            logging.error(f"Network communication error: {e}")
            return {'success': False, 'error': 'Network error'}, 503
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error: {e}")
            return {'success': False, 'error': str(e)}, 400
        except Exception as e:
            logging.error(f"General error: {e}")
            return {'success': False, 'error': 'Internal server error'}, 500




