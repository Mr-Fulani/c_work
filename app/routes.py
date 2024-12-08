# app/routes.py
import logging
import os
import uuid
from datetime import datetime, timedelta

import stripe
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from wtforms.fields.choices import SelectField
from wtforms.fields.simple import SubmitField
from wtforms.validators import DataRequired

from app import db, bcrypt, limiter
from app.models import User, Class, Booking, Payment, ActionLog
from app.forms import RegistrationForm, BookingForm, CancelBookingForm, UpdateProfileForm, SelectDayForm, \
    ChangePasswordForm
from flask_login import login_user, current_user, logout_user, login_required

from app.utils import allowed_file

main_bp = Blueprint('main', __name__)

logger = logging.getLogger(__name__)



@main_bp.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


@main_bp.route('/')
@main_bp.route('/home')
def home():
    classes = Class.query.all()
    return render_template('home.html', classes=classes)




@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        password = form.password.data
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        # Логирование действия регистрации
        action = ActionLog(
            user_id=user.id,
            action='Регистрация',
            ip_address=request.remote_addr,
            status='success'
        )
        db.session.add(action)
        db.session.commit()

        flash('Ваш аккаунт создан! Вы можете войти.', 'success')
        return redirect(url_for('main.login'))
    elif request.method == 'POST':
        # Логирование неуспешной попытки регистрации
        action = ActionLog(
            user_id=None,
            action='Регистрация',
            ip_address=request.remote_addr,
            status='failure'
        )
        db.session.add(action)
        db.session.commit()
    return render_template('register.html', form=form)







MAX_FAILED_ATTEMPTS = 5
BLOCK_DURATION = timedelta(minutes=15)



@main_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"], error_message="Слишком много попыток входа. Попробуйте позже.")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        # Получение количества неудачных попыток за последние 15 минут
        recent_failed_logins = ActionLog.query.filter(
            ActionLog.user_id == user.id if user else False,
            ActionLog.action == 'Вход',
            ActionLog.status == 'failure',
            ActionLog.timestamp >= datetime.utcnow() - BLOCK_DURATION
        ).count()

        if recent_failed_logins >= MAX_FAILED_ATTEMPTS:
            flash('Слишком много неудачных попыток входа. Попробуйте позже.', 'danger')
            return render_template('login.html')

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()

            # Логирование успешного входа
            action = ActionLog(
                user_id=user.id,
                action='Вход',
                ip_address=request.remote_addr,
                status='success'
            )
            db.session.add(action)
            db.session.commit()

            next_page = request.args.get('next')
            flash('Вы вошли в систему!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            # Логирование неуспешного входа
            action = ActionLog(
                user_id=user.id if user else None,
                action='Вход',
                ip_address=request.remote_addr,
                status='failure'
            )
            db.session.add(action)
            db.session.commit()

            flash('Неверные данные для входа. Пожалуйста, попробуйте снова.', 'danger')
    return render_template('login.html')


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('main.home'))




@main_bp.route('/classes')
@login_required
def classes():
    classes = Class.query.order_by(Class.schedule.asc()).all()
    booking_forms = {class_.id: BookingForm(class_id=class_.id) for class_ in classes}
    return render_template('classes.html', classes=classes, booking_forms=booking_forms)






@main_bp.route('/book_class/<int:class_id>', methods=['GET', 'POST'])
@login_required
def book_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    form = SelectDayForm()
    available_days = [day.strip() for day in class_.days_of_week.split(',')]
    form.day.choices = [(day, day) for day in available_days]

    if form.validate_on_submit():
        selected_day = form.day.data

        # Проверка, не бронировал ли пользователь этот класс в этот день ранее
        existing_booking = Booking.query.filter_by(user_id=current_user.id, class_id=class_id, day=selected_day).first()
        if existing_booking:
            flash('Вы уже забронировали место в этом классе на выбранный день.', 'info')
            return redirect(url_for('main.classes'))

        # Проверка доступности мест
        confirmed_bookings = Booking.query.filter_by(class_id=class_id, day=selected_day, status='confirmed').count()
        if confirmed_bookings >= class_.capacity:
            flash('Извините, на этот день места уже заполнены.', 'danger')
            return redirect(url_for('main.classes'))

        # Проверка массового бронирования
        recent_bookings = Booking.query.filter(
            Booking.user_id == current_user.id,
            Booking.booking_date >= datetime.utcnow() - timedelta(minutes=10)
        ).count()
        if recent_bookings >= 10:
            flash('Вы сделали слишком много бронирований за короткий период. Попробуйте позже.', 'danger')
            # Логирование подозрительного действия
            action = ActionLog(
                user_id=current_user.id,
                action='Массовое бронирование',
                ip_address=request.remote_addr,
                status='warning'
            )
            db.session.add(action)
            db.session.commit()
            return redirect(url_for('main.classes'))

        # Создание бронирования
        booking = Booking(user_id=current_user.id, class_id=class_id, day=selected_day)
        db.session.add(booking)
        db.session.commit()

        # Логирование бронирования
        action = ActionLog(
            user_id=current_user.id,
            action=f"Бронирование класса '{class_.name}' на {selected_day}",
            ip_address=request.remote_addr,
            status='success'
        )
        db.session.add(action)
        db.session.commit()

        flash('Класс успешно забронирован!', 'success')
        return redirect(url_for('main.my_bookings'))

    return render_template('book_class.html', class_=class_, form=form, available_days=available_days)




@main_bp.route('/my_bookings')
@login_required
def my_bookings():
    # Получение только подтверждённых бронирований пользователя
    bookings = Booking.query.filter_by(user_id=current_user.id, status='confirmed').order_by(Booking.booking_date.desc()).all()
    cancel_forms = {booking.id: CancelBookingForm(booking_id=booking.id) for booking in bookings}
    return render_template('my_bookings.html', bookings=bookings, cancel_forms=cancel_forms)









@main_bp.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    form = CancelBookingForm()
    if form.validate_on_submit():
        booking = Booking.query.get_or_404(form.booking_id.data)
        if booking.user_id != current_user.id:
            flash('У вас нет прав на отмену этого бронирования.', 'danger')
            return redirect(url_for('main.profile'))

        # Проверка массовой отмены
        recent_cancellations = ActionLog.query.filter(
            ActionLog.user_id == current_user.id,
            ActionLog.action.like('Отмена бронирования%'),
            ActionLog.timestamp >= datetime.utcnow() - timedelta(minutes=10)
        ).count()
        if recent_cancellations >= 10:
            flash('Вы отменили слишком много бронирований за короткий период. Попробуйте позже.', 'danger')
            # Логирование подозрительного действия
            action = ActionLog(
                user_id=current_user.id,
                action='Массовая отмена бронирований',
                ip_address=request.remote_addr,
                status='warning'
            )
            db.session.add(action)
            db.session.commit()
            return redirect(url_for('main.profile'))

        # Обновление статуса бронирования
        booking.status = 'cancelled'
        db.session.commit()

        # Логирование отмены бронирования
        action = ActionLog(
            user_id=current_user.id,
            action=f"Отмена бронирования класса '{booking.class_.name}' на {booking.day}",
            ip_address=request.remote_addr,
            status='success'
        )
        db.session.add(action)
        db.session.commit()

        logger.info(f"Booking ID {booking.id} cancelled by User ID {current_user.id}")
        flash('Бронирование успешно отменено.', 'success')
        return redirect(url_for('main.profile'))
    else:
        logger.error(f"Failed to cancel booking ID {booking_id} by User ID {current_user.id}")
        flash('Ошибка при отмене бронирования.', 'danger')
        return redirect(url_for('main.profile'))




@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()

    if request.method == 'GET':
        # Предварительное заполнение формы текущими данными пользователя
        form.username.data = current_user.username
        form.email.data = current_user.email

    if form.validate_on_submit():
        old_username = current_user.username
        old_email = current_user.email

        if form.avatar.data:
            # Обработка загрузки аватара
            avatar_file = form.avatar.data
            if allowed_file(avatar_file.filename):
                filename = secure_filename(avatar_file.filename)
                unique_filename = f"{current_user.id}_{uuid.uuid4().hex}_{filename}"
                avatar_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                try:
                    avatar_file.save(avatar_path)
                    current_user.avatar = unique_filename
                except Exception as e:
                    logger.error(f"Ошибка при сохранении аватара пользователя {current_user.id}: {e}")
                    flash('Произошла ошибка при загрузке аватара.', 'danger')
                    return redirect(url_for('main.profile'))
            else:
                flash('Неверный формат файла аватара. Разрешены только изображения (png, jpg, jpeg, gif).', 'danger')
                return redirect(url_for('main.profile'))

        current_user.username = form.username.data.strip()
        current_user.email = form.email.data.strip().lower()

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при обновлении профиля пользователя {current_user.id}: {e}")
            flash('Произошла ошибка при обновлении профиля.', 'danger')
            return redirect(url_for('main.profile'))

        # Логирование обновления профиля
        changes = []
        if old_username != current_user.username:
            changes.append(f"Изменение имени пользователя: {old_username} → {current_user.username}")
        if old_email != current_user.email:
            changes.append(f"Изменение email: {old_email} → {current_user.email}")
        if form.avatar.data:
            changes.append("Обновление аватара")

        if changes:
            action = ActionLog(
                user_id=current_user.id,
                action='; '.join(changes),
                ip_address=request.remote_addr,
                status='success'
            )
            try:
                db.session.add(action)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Ошибка при логировании действия пользователя {current_user.id}: {e}")
                flash('Произошла ошибка при логировании действия.', 'danger')

        flash('Ваш профиль обновлён!', 'success')
        return redirect(url_for('main.profile'))

    elif request.method == 'POST':
        # Логирование неуспешной попытки обновления профиля (например, из-за ошибок валидации)
        action = ActionLog(
            user_id=current_user.id,
            action='Обновление профиля',
            ip_address=request.remote_addr,
            status='failure'
        )
        try:
            db.session.add(action)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при логировании неуспешного действия пользователя {current_user.id}: {e}")

    # Получение подтверждённых бронирований пользователя
    confirmed_bookings = Booking.query.filter_by(user_id=current_user.id, status='confirmed').order_by(
        Booking.booking_date.desc()).all()
    # Получение отменённых бронирований пользователя
    cancelled_bookings = Booking.query.filter_by(user_id=current_user.id, status='cancelled').order_by(
        Booking.booking_date.desc()).all()

    logger.info(f"User ID {current_user.id} has {len(confirmed_bookings)} confirmed bookings.")
    for booking in confirmed_bookings:
        logger.info(f"Booking ID: {booking.id}, Class ID: {booking.class_id}, Status: {booking.status}")

    cancel_forms = {booking.id: CancelBookingForm(booking_id=booking.id) for booking in confirmed_bookings}

    avatar_url = url_for('static', filename='images/' + (current_user.avatar or 'default_avatar.png'))
    return render_template(
        'profile.html',
        user=current_user,  # Передаём current_user как 'user'
        form=form,
        avatar_url=avatar_url,
        bookings=confirmed_bookings,
        cancelled_bookings=cancelled_bookings,
        cancel_forms=cancel_forms
    )




# @main_bp.route('/process_payment', methods=['POST'])
# @login_required
# def process_payment():
#     # Логика обработки платежа
#     try:
#         # Предположим, что здесь код для обработки платежа
#         # Например, взаимодействие с Stripe API
#
#         # Если платеж успешен
#         payment = Payment(
#             user_id=current_user.id,
#             amount=amount,  # Определите переменную amount
#             stripe_payment_id=stripe_payment_id,  # Получите ID платежа от Stripe
#             status='paid'
#         )
#         db.session.add(payment)
#         db.session.commit()
#
#         # Логирование успешного платежа
#         action = ActionLog(
#             user_id=current_user.id,
#             action=f"Успешный платеж на сумму {amount}",
#             ip_address=request.remote_addr,
#             status='success'
#         )
#         db.session.add(action)
#         db.session.commit()
#
#         flash('Платёж успешно выполнен.', 'success')
#         return redirect(url_for('main.payment_success'))
#     except Exception as e:
#         logger.error(f"Ошибка при обработке платежа: {e}")
#
#         # Логирование неуспешного платежа
#         action = ActionLog(
#             user_id=current_user.id,
#             action=f"Неуспешный платеж на сумму {amount}",
#             ip_address=request.remote_addr,
#             status='failure'
#         )
#         db.session.add(action)
#         db.session.commit()
#
#         flash('Ошибка при выполнении платежа. Пожалуйста, попробуйте снова.', 'danger')
#         return redirect(url_for('main.payment_failure'))









@main_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # Проверка количества изменений пароля за последние 24 часа
        recent_password_changes = ActionLog.query.filter(
            ActionLog.user_id == current_user.id,
            ActionLog.action == 'Изменение пароля',
            ActionLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()

        if recent_password_changes >= 3:
            flash('Вы превысили лимит изменений пароля за последние 24 часа. Попробуйте позже.', 'danger')
            return redirect(url_for('main.profile'))

        # Проверка текущего пароля
        if bcrypt.check_password_hash(current_user.password, form.current_password.data):
            # Генерация хэшированного нового пароля
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            current_user.password = hashed_password
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Ошибка при обновлении пароля пользователя {current_user.id}: {e}")
                flash('Произошла ошибка при обновлении пароля. Попробуйте позже.', 'danger')
                return redirect(url_for('main.change_password'))

            # Логирование успешного изменения пароля
            action = ActionLog(
                user_id=current_user.id,
                action='Изменение пароля',
                ip_address=request.remote_addr,
                status='success'
            )
            try:
                db.session.add(action)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Ошибка при логировании изменения пароля пользователя {current_user.id}: {e}")
                flash('Пароль обновлён, но произошла ошибка при логировании действия.', 'warning')

            flash('Ваш пароль был обновлён!', 'success')
            return redirect(url_for('main.profile'))
        else:
            flash('Текущий пароль неверен.', 'danger')
            # Логирование неуспешного изменения пароля
            action = ActionLog(
                user_id=current_user.id,
                action='Изменение пароля',
                ip_address=request.remote_addr,
                status='failure'
            )
            try:
                db.session.add(action)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Ошибка при логировании неуспешного изменения пароля пользователя {current_user.id}: {e}")

    return render_template('change_password.html', form=form)





# @main_bp.route('/stripe_webhook', methods=['POST'])
# def stripe_webhook():
#     payload = request.get_data(as_text=True)
#     sig_header = request.headers.get('Stripe-Signature')
#     endpoint_secret = 'your_endpoint_secret'
#
#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, endpoint_secret
#         )
#     except ValueError:
#         # Неверный Payload
#         return 'Invalid payload', 400
#     except stripe.error.SignatureVerificationError:
#         # Неверный Подпись
#         return 'Invalid signature', 400
#
#     # Обработка события
#     if event['type'] == 'payment_intent.succeeded':
#         payment_intent = event['data']['object']
#         # Обработка успешного платежа
#         payment = Payment(
#             user_id=payment_intent['metadata']['user_id'],
#             amount=payment_intent['amount'] / 100,  # Преобразование из центов
#             stripe_payment_id=payment_intent['id'],
#             status='paid'
#         )
#         db.session.add(payment)
#
#         # Логирование успешного платежа
#         action = ActionLog(
#             user_id=payment.user_id,
#             action=f"Успешный платеж на сумму {payment.amount}",
#             ip_address=request.remote_addr,
#             status='success'
#         )
#         db.session.add(action)
#         db.session.commit()
#     elif event['type'] == 'payment_intent.payment_failed':
#         payment_intent = event['data']['object']
#         # Обработка неуспешного платежа
#         payment = Payment(
#             user_id=payment_intent['metadata']['user_id'],
#             amount=payment_intent['amount'] / 100,
#             stripe_payment_id=payment_intent['id'],
#             status='failed'
#         )
#         db.session.add(payment)
#
#         # Логирование неуспешного платежа
#         action = ActionLog(
#             user_id=payment.user_id,
#             action=f"Неуспешный платеж на сумму {payment.amount}",
#             ip_address=request.remote_addr,
#             status='failure'
#         )
#         db.session.add(action)
#         db.session.commit()
#
#     return '', 200



