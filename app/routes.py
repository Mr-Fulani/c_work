import logging
import os
import re
import uuid
from datetime import datetime, timedelta

import stripe
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.utils import secure_filename

from app import db, bcrypt
from app import mail  # Ensure Flask-Mail is initialized
from app.forms import RegistrationForm, BookingForm, CancelBookingForm, UpdateProfileForm, SelectDayForm, \
    ChangePasswordForm, LoginForm, ResetPasswordForm, ResetPasswordRequestForm, PaymentForm
from app.models import User, Class, Booking, ActionLog
from app.utils import allowed_file

main_bp = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

# Initialize Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

MAX_FAILED_ATTEMPTS = 5
BLOCK_DURATION = timedelta(minutes=15)


@main_bp.errorhandler(500)
def internal_error(error):
    """
    Handles internal server errors (HTTP 500).

    Args:
        error: The error object.

    Returns:
        Response: Rendered 500 error page.
    """
    return render_template('500.html'), 500


@main_bp.route('/')
@main_bp.route('/home')
def home():
    """
    Home page route.

    Returns:
        Response: Rendered home page template with class data.
    """
    classes = Class.query.all()
    return render_template('home.html', classes=classes)


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route.

    Handles user registration by validating the form, saving user details, and logging the action.

    Returns:
        Response: Redirects to the login page upon success or renders the registration page upon failure.
    """
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

        # Log registration action
        action = ActionLog(
            user_id=user.id,
            action='Registration',
            ip_address=request.remote_addr,
            status='success'
        )
        db.session.add(action)
        db.session.commit()

        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    elif request.method == 'POST':
        # Log failed registration attempt
        action = ActionLog(
            user_id=None,
            action='Registration',
            ip_address=request.remote_addr,
            status='failure'
        )
        db.session.add(action)
        db.session.commit()

    return render_template('register.html', form=form)


@main_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"], error_message="Too many login attempts. Please try again later.")
def login():
    """
    User login route.

    Validates user credentials, logs successful or failed login attempts, and enforces rate limiting.

    Returns:
        Response: Redirects to the home page upon success or renders the login page upon failure.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.email_or_username.data.strip()
        password = form.password.data

        # Determine if identifier is an email using regex
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if re.match(email_regex, identifier):
            user = User.query.filter_by(email=identifier.lower()).first()
        else:
            user = User.query.filter_by(username=identifier).first()

        if user:
            # Get number of failed login attempts in the last 15 minutes
            recent_failed_logins = ActionLog.query.filter(
                ActionLog.user_id == user.id,
                ActionLog.action == 'Login',
                ActionLog.status == 'failure',
                ActionLog.timestamp >= datetime.utcnow() - BLOCK_DURATION
            ).count()

            if recent_failed_logins >= MAX_FAILED_ATTEMPTS:
                # Log failed login attempt
                action = ActionLog(
                    user_id=user.id,
                    action='Login',
                    ip_address=request.remote_addr,
                    status='failure'
                )
                db.session.add(action)
                db.session.commit()

                return redirect(url_for('main.error_page', error_type='too_many_attempts'))

            if bcrypt.check_password_hash(user.password, password):
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()

                # Log successful login
                action = ActionLog(
                    user_id=user.id,
                    action='Login',
                    ip_address=request.remote_addr,
                    status='success'
                )
                db.session.add(action)
                db.session.commit()

                return redirect(url_for('main.home'))
            else:
                # Log failed login attempt
                action = ActionLog(
                    user_id=user.id,
                    action='Login',
                    ip_address=request.remote_addr,
                    status='failure'
                )
                db.session.add(action)
                db.session.commit()

                return redirect(url_for('main.error_page', error_type='invalid_credentials'))
        else:
            # Log failed login attempt (user not found)
            action = ActionLog(
                user_id=None,
                action='Login',
                ip_address=request.remote_addr,
                status='failure'
            )
            db.session.add(action)
            db.session.commit()

            return redirect(url_for('main.error_page', error_type='invalid_credentials'))

    return render_template('login.html', form=form)






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





@main_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            # Инициализация сериализатора внутри функции
            serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = serializer.dumps(user.email, salt='password-reset-salt')
            reset_url = url_for('main.reset_with_token', token=token, _external=True)

            # Отправка письма с ссылкой для сброса пароля
            msg = Message('Сброс Пароля',
                          sender=current_app.config['MAIL_DEFAULT_SENDER'],
                          recipients=[user.email])
            msg.body = f'''Здравствуйте, {user.username}!

Вы получили это письмо, потому что вы (или кто-то другой) запросили сброс пароля для вашего аккаунта.

Пожалуйста, перейдите по следующей ссылке, чтобы сбросить пароль:

{reset_url}

Если вы не запрашивали сброс пароля, пожалуйста, проигнорируйте это письмо.

Спасибо!
Команда c_work
'''
            try:
                mail.send(msg)
                flash('Ссылка для сброса пароля отправлена на ваш email.', 'info')
            except Exception as e:
                logger.error(f"Ошибка при отправке письма сброса пароля: {e}")
                flash('Не удалось отправить письмо. Пожалуйста, попробуйте позже.', 'danger')
        else:
            flash('Email не найден в системе.', 'danger')
    return render_template('reset_password.html', form=form)








@main_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    try:
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # Срок действия токена: 1 час
    except Exception as e:
        flash('Срок действия ссылки для сброса пароля истёк или она некорректна.', 'danger')
        return redirect(url_for('main.error_page', error_type='invalid_token'))

    user = User.query.filter_by(email=email).first_or_404()
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при обновлении пароля пользователя {user.id}: {e}")
            flash('Произошла ошибка при обновлении пароля. Попробуйте позже.', 'danger')
            return redirect(url_for('main.error_page', error_type='unknown_error'))

        # Логирование успешного сброса пароля
        action = ActionLog(
            user_id=user.id,
            action='Сброс пароля',
            ip_address=request.remote_addr,
            status='success'
        )
        try:
            db.session.add(action)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при логировании сброса пароля пользователя {user.id}: {e}")
            flash('Пароль обновлён, но произошла ошибка при логировании действия.', 'warning')

        flash('Ваш пароль был успешно сброшен. Теперь вы можете войти.', 'success')
        return redirect(url_for('main.login'))
    return render_template('reset_with_token.html', form=form)







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

        # Отправка уведомления пользователю
        try:
            user_msg = Message(
                'Подтверждение Бронирования',
                recipients=[current_user.email]
            )
            user_msg.html = render_template(
                'emails/booking_confirmation.html',
                user=current_user,
                class_=class_,
                selected_day=selected_day
            )
            user_msg.body = f'''Здравствуйте, {current_user.username}!

Вы успешно забронировали место на классе "{class_.name}".
День недели: {selected_day}
Дата и время: {class_.schedule.strftime("%d.%m.%Y %H:%M")}

Спасибо за использование сервиса c_work!

С уважением,
Команда c_work
'''
            mail.send(user_msg)
        except Exception as e:
            logger.error(f"Ошибка при отправке подтверждения бронирования пользователю {current_user.id}: {e}")
            flash('Не удалось отправить подтверждение бронирования на ваш email.', 'warning')

        # Отправка уведомления администраторам
        try:
            admins = User.query.filter_by(is_admin=True).all()
            admin_emails = [admin.email for admin in admins]
            if admin_emails:
                admin_msg = Message(
                    'Новая Запись на Класс',
                    recipients=admin_emails
                )
                admin_msg.body = f'''Здравствуйте!

Пользователь {current_user.username} ({current_user.email}) забронировал место на классе "{class_.name}".
День недели: {selected_day}
Дата и время: {class_.schedule.strftime("%d.%m.%Y %H:%M")}

Пожалуйста, проверьте статус класса и при необходимости свяжитесь с пользователем.

С уважением,
Система c_work
'''
                mail.send(admin_msg)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления администраторам: {e}")
            flash('Не удалось отправить уведомление администраторам.', 'warning')

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









@main_bp.route('/process_payment', methods=['GET', 'POST'])
@login_required
def process_payment():
    form = PaymentForm()
    if form.validate_on_submit():
        try:
            amount = int(form.amount.data * 100)  # Stripe принимает сумму в центах
            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

            # Создание PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',  # Замените на нужную валюту
                metadata={'user_id': current_user.id}
            )

            logger.info(f"Created PaymentIntent: {intent['id']} for user {current_user.id}")

            return render_template(
                'process_payment.html',
                client_secret=intent.client_secret,
                stripe_publishable_key=current_app.config['STRIPE_PUBLISHABLE_KEY']
            )

        except Exception as e:
            logger.error(f"Ошибка при создании PaymentIntent: {e}")
            flash('Произошла ошибка при обработке платежа. Пожалуйста, попробуйте снова.', 'danger')
            return redirect(url_for('main.home'))

    return render_template('process_payment.html', form=form)




@main_bp.route('/payment_success')
@login_required
def payment_success():
    action = ActionLog(
        user_id=current_user.id,
        action='Успешный платёж',
        ip_address=request.remote_addr,
        status='success'
    )
    db.session.add(action)
    db.session.commit()
    logger.info(f"User {current_user.id} completed a payment successfully.")
    return render_template('payment_success.html')





@main_bp.route('/payment_failure')
@login_required
def payment_failure():
    action = ActionLog(
        user_id=current_user.id,
        action='Ошибка платежа',
        ip_address=request.remote_addr,
        status='failure'
    )
    db.session.add(action)
    db.session.commit()
    logger.warning(f"User {current_user.id} encountered a payment failure.")
    return render_template('payment_failure.html')






@main_bp.route('/error/<string:error_type>')
def error_page(error_type):
    error_messages = {
        'invalid_credentials': {
            'title': 'Неверные Данные',
            'message': 'Неверный email или пароль. Пожалуйста, попробуйте снова.'
        },
        'invalid_token': {
            'title': 'Некорректная Ссылка',
            'message': 'Срок действия ссылки истёк или она некорректна.'
        },
        'too_many_attempts': {
            'title': 'Слишком Много Попыток',
            'message': 'Слишком много попыток входа. Пожалуйста, попробуйте позже.'
        },
    }

    error = error_messages.get(error_type, {
        'title': 'Ошибка',
        'message': 'Произошла неизвестная ошибка.'
    })

    action = ActionLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=f"Страница ошибки: {error_type}",
        ip_address=request.remote_addr,
        status='failure'
    )
    db.session.add(action)
    db.session.commit()

    logger.error(f"Error page accessed: {error_type}. Message: {error['message']}")
    return render_template('error.html', error=error, error_type=error_type), 400









# @main_bp.route('/send_test_email')
# @login_required
# def send_test_email():
#     try:
#         msg = Message('Тестовое письмо',
#                       recipients=[current_user.email])
#         msg.body = 'Это тестовое письмо, отправленное с помощью Flask-Mail.'
#         mail.send(msg)
#         flash('Тестовое письмо успешно отправлено!', 'success')
#     except Exception as e:
#         logger.error(f"Ошибка при отправке тестового письма: {e}")
#         flash('Не удалось отправить тестовое письмо.', 'danger')
#     return redirect(url_for('main.home'))






