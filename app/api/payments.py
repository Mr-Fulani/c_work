import logging
from flask_restful import Resource
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required
import stripe

class PaymentResource(Resource):
    @jwt_required()
    def post(self):
        try:
            logging.debug("Received payment request")
            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            logging.debug(f"Stripe API Key set: {stripe.api_key}")

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
                return jsonify({'success': False, 'error': 'Invalid amount'}), 400

            if not payment_method_id or not isinstance(payment_method_id, str):
                logging.error("Invalid payment_method_id")
                return jsonify({'success': False, 'error': 'Invalid payment_method_id'}), 400

            # Создание PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                description=description,
                payment_method=payment_method_id,
                confirm=True
            )
            logging.debug(f"PaymentIntent created: {intent}")

            return jsonify({
                'success': True,
                'client_secret': intent['client_secret'],
                'status': intent['status'],
                'charges': intent['charges']['data']
            })

        except stripe.error.CardError as e:
            logging.error(f"Card declined: {e}")
            return jsonify({'success': False, 'error': 'Card declined'}), 402
        except stripe.error.RateLimitError as e:
            logging.error(f"Rate limit error: {e}")
            return jsonify({'success': False, 'error': 'Rate limit error'}), 429
        except stripe.error.InvalidRequestError as e:
            logging.error(f"Invalid parameters: {e}")
            return jsonify({'success': False, 'error': 'Invalid request'}), 400
        except stripe.error.AuthenticationError as e:
            logging.error(f"Authentication error: {e}")
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
        except stripe.error.APIConnectionError as e:
            logging.error(f"Network communication error: {e}")
            return jsonify({'success': False, 'error': 'Network error'}), 503
        except stripe.error.StripeError as e:
            logging.error(f"Stripe error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logging.error(f"General error: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
