import logging
from flask import Blueprint, request, current_app
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import stripe

webhook_bp = Blueprint('webhooks', __name__)

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

@webhook_bp.route('/stripe_webhook', methods=['POST'])
@limiter.exempt
@csrf.exempt
def stripe_webhook():
    from app.models import ActionLog
    from app import db

    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config['STRIPE_ENDPOINT_SECRET']

    logging.info("Received webhook payload")
    logging.debug(f"Payload: {payload}")
    logging.debug(f"Stripe-Signature Header: {sig_header}")
    logging.debug(f"Endpoint Secret: {endpoint_secret}")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logging.info(f"Successfully constructed event: {event['type']}")

        # Сохранение события в логах
        action_log = ActionLog(
            user_id=None,
            action=f"Webhook event: {event['type']}",
            ip_address=request.remote_addr,
            status='received'
        )
        db.session.add(action_log)
        db.session.commit()

        # Обработка события
        event_type = event['type']
        if event_type == 'payment_intent.succeeded':
            handle_payment_intent_succeeded(event['data']['object'])
        elif event_type == 'payment_intent.payment_failed':
            handle_payment_intent_failed(event['data']['object'])
        else:
            logging.warning(f"Unhandled event type: {event_type}")

        return '', 200

    except Exception as e:
        logging.error(f"Error handling webhook: {e}")
        return 'Internal Server Error', 500

def handle_payment_intent_succeeded(payment_intent):
    from app.models import Payment
    from app import db

    user_id = payment_intent['metadata'].get('user_id')
    amount = payment_intent['amount'] / 100  # Преобразование из центов
    stripe_payment_id = payment_intent['id']

    logging.info(f"Handling payment_intent.succeeded for user_id: {user_id}, amount: {amount}")

    payment = Payment(
        user_id=user_id,
        amount=amount,
        stripe_payment_id=stripe_payment_id,
        status='paid'
    )
    db.session.add(payment)
    db.session.commit()

def handle_payment_intent_failed(payment_intent):
    from app.models import Payment
    from app import db

    user_id = payment_intent['metadata'].get('user_id')
    amount = payment_intent['amount'] / 100
    stripe_payment_id = payment_intent['id']

    logging.info(f"Handling payment_intent.payment_failed for user_id: {user_id}, amount: {amount}")

    payment = Payment(
        user_id=user_id,
        amount=amount,
        stripe_payment_id=stripe_payment_id,
        status='failed'
    )
    db.session.add(payment)
    db.session.commit()