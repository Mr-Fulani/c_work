# app/routes.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db, bcrypt
from app.models import User, Class, Booking, Payment
from app.forms import RegistrationForm
from flask_login import login_user, current_user, logout_user, login_required



main_bp = Blueprint('main', __name__)





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
        flash('Ваш аккаунт создан! Вы можете войти.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)



@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Вы вошли в систему!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
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
    return render_template('classes.html', classes=classes)


@main_bp.route('/book_class/<int:class_id>', methods=['GET', 'POST'])
@login_required
def book_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    if request.method == 'POST':
        selected_day = request.form.get('day')
        if selected_day not in [day.strip() for day in class_.days_of_week.split(',')]:
            flash('Выбранный день недоступен для этого класса.', 'danger')
            return redirect(url_for('main.book_class', class_id=class_id))

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

        # Создание бронирования
        booking = Booking(user_id=current_user.id, class_id=class_id, day=selected_day)
        db.session.add(booking)
        db.session.commit()
        flash('Класс успешно забронирован!', 'success')
        return redirect(url_for('main.my_bookings'))

    # GET-запрос: отображение формы бронирования
    available_days = [day.strip() for day in class_.days_of_week.split(',')]
    return render_template('book_class.html', class_=class_, available_days=available_days)


@main_bp.route('/my_bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)


@main_bp.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('У вас нет прав на отмену этого бронирования.', 'danger')
        return redirect(url_for('main.my_bookings'))

    booking.status = 'cancelled'
    db.session.commit()
    flash('Бронирование успешно отменено.', 'success')
    return redirect(url_for('main.my_bookings'))