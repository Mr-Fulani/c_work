import logging
from flask import Blueprint, request, current_app, jsonify
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
            user_id=None,  # Здесь лучше установить правильный user_id, если возможно
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
        elif event_type == 'charge.succeeded':
            handle_charge_succeeded(event['data']['object'])
        elif event_type == 'charge.failed':
            handle_charge_failed(event['data']['object'])
        else:
            logging.warning(f"Unhandled event type: {event_type}")

        return '', 200

    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Invalid signature: {e}")
        return 'Invalid signature', 400
    except Exception as e:
        logging.error(f"Error handling webhook: {e}")
        return 'Internal Server Error', 500

def handle_payment_intent_succeeded(payment_intent):
    from app.models import Payment, ActionLog
    from app import db

    user_id = payment_intent['metadata'].get('user_id')
    amount = payment_intent['amount'] / 100  # Преобразование из центов
    stripe_payment_id = payment_intent['id']

    logging.info(f"Handling payment_intent.succeeded for user_id: {user_id}, amount: {amount}")

    if not user_id:
        logging.error("user_id отсутствует в metadata PaymentIntent")
        # Дополнительная обработка, например, уведомление администратору или пропуск
        return

    try:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            stripe_payment_id=stripe_payment_id,
            status='paid'
        )
        db.session.add(payment)

        action = ActionLog(
            user_id=user_id,
            action=f"Успешный платеж на сумму {amount} USD",
            ip_address=request.remote_addr,
            status='success'
        )
        db.session.add(action)
        db.session.commit()
        logging.info(f"Платеж ID {stripe_payment_id} успешно обработан для пользователя ID {user_id}.")
    except Exception as e:
        logging.error(f"Error handling payment_intent.succeeded: {e}")
        db.session.rollback()

def handle_payment_intent_failed(payment_intent):
    from app.models import Payment, ActionLog
    from app import db

    user_id = payment_intent['metadata'].get('user_id')
    amount = payment_intent['amount'] / 100
    stripe_payment_id = payment_intent['id']

    logging.info(f"Handling payment_intent.payment_failed for user_id: {user_id}, amount: {amount}")

    if not user_id:
        logging.error("user_id отсутствует в metadata PaymentIntent")
        # Дополнительная обработка, например, уведомление администратору или пропуск
        return

    try:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            stripe_payment_id=stripe_payment_id,
            status='failed'
        )
        db.session.add(payment)

        action = ActionLog(
            user_id=user_id,
            action=f"Неуспешный платеж на сумму {amount} USD",
            ip_address=request.remote_addr,
            status='failure'
        )
        db.session.add(action)
        db.session.commit()
        logging.warning(f"Платеж ID {stripe_payment_id} не удался для пользователя ID {user_id}.")
    except Exception as e:
        logging.error(f"Error handling payment_intent.payment_failed: {e}")
        db.session.rollback()

def handle_charge_succeeded(charge):
    from app.models import Payment, ActionLog
    from app import db

    user_id = charge['metadata'].get('user_id')
    amount = charge['amount'] / 100  # Преобразование из центов
    stripe_charge_id = charge['id']

    logging.info(f"Handling charge.succeeded for user_id: {user_id}, amount: {amount}")

    if not user_id:
        logging.error("user_id отсутствует в metadata Charge")
        # Дополнительная обработка, например, уведомление администратору или пропуск
        return

    try:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            stripe_payment_id=stripe_charge_id,
            status='paid'
        )
        db.session.add(payment)

        action = ActionLog(
            user_id=user_id,
            action=f"Успешный платеж (charge) на сумму {amount} USD",
            ip_address=request.remote_addr,
            status='success'
        )
        db.session.add(action)
        db.session.commit()
        logging.info(f"Платеж charge ID {stripe_charge_id} успешно обработан для пользователя ID {user_id}.")
    except Exception as e:
        logging.error(f"Error handling charge.succeeded: {e}")
        db.session.rollback()

def handle_charge_failed(charge):
    from app.models import Payment, ActionLog
    from app import db

    user_id = charge['metadata'].get('user_id')
    amount = charge['amount'] / 100
    stripe_charge_id = charge['id']

    logging.info(f"Handling charge.failed for user_id: {user_id}, amount: {amount}")

    if not user_id:
        logging.error("user_id отсутствует в metadata Charge")
        # Дополнительная обработка, например, уведомление администратору или пропуск
        return

    try:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            stripe_payment_id=stripe_charge_id,
            status='failed'
        )
        db.session.add(payment)

        action = ActionLog(
            user_id=user_id,
            action=f"Неуспешный платеж (charge) на сумму {amount} USD",
            ip_address=request.remote_addr,
            status='failure'
        )
        db.session.add(action)
        db.session.commit()
        logging.warning(f"Платеж charge ID {stripe_charge_id} не удался для пользователя ID {user_id}.")
    except Exception as e:
        logging.error(f"Error handling charge.failed: {e}")
        db.session.rollback()