from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db, bcrypt
from app.models import User, Class, Booking, Payment
from flask_login import login_user, current_user, logout_user, login_required



bp = Blueprint('main', __name__)



@bp.route('/')
@bp.route('/home')
def home():
    return render_template('home.html')



@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Ваш аккаунт создан! Вы можете войти.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        email = request.form.get('email')
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

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@bp.route('/classes')
@login_required
def classes():
    classes = Class.query.order_by(Class.schedule.asc()).all()
    return render_template('classes.html', classes=classes)


@bp.route('/book/<int:class_id>', methods=['POST'])
@login_required
def book_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    if class_.available_slots() <= 0:
        flash('Извините, места на этот класс уже заполнены.', 'warning')
        return redirect(url_for('main.classes'))

    existing_booking = Booking.query.filter_by(user_id=current_user.id, class_id=class_id).first()
    if existing_booking:
        flash('Вы уже забронировали это занятие.', 'info')
        return redirect(url_for('main.classes'))

    booking = Booking(user_id=current_user.id, class_id=class_id)
    db.session.add(booking)
    db.session.commit()
    flash('Бронирование успешно создано!', 'success')
    return redirect(url_for('main.classes'))




@bp.route('/my_bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booking_date.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)