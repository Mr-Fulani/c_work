# app/admin_routes.py
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app import db
from app.models import User, Class, Booking
from flask_login import login_required, current_user
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Панель администратора
@admin_bp.route('/')
@login_required
@admin_required
def admin_panel():
    classes = Class.query.order_by(Class.schedule.asc()).all()
    users = User.query.order_by(User.username.asc()).all()
    return render_template('admin_panel.html', classes=classes, users=users)

# Добавление Администратора
@admin_bp.route('/promote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def promote_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash(f'Пользователь {user.username} уже является администратором.', 'info')
    else:
        user.is_admin = True
        db.session.commit()
        flash(f'Пользователь {user.username} успешно назначен администратором.', 'success')
    return redirect(url_for('admin.admin_panel'))

# Понижение Администратора
@admin_bp.route('/demote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def demote_user(user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_admin:
        flash(f'Пользователь {user.username} уже не является администратором.', 'info')
    elif user.id == current_user.id:
        flash('Вы не можете понизить собственные административные права.', 'danger')
    else:
        user.is_admin = False
        db.session.commit()
        flash(f'Пользователь {user.username} успешно понижен из администраторов.', 'success')
    return redirect(url_for('admin.admin_panel'))

# Добавление класса
@admin_bp.route('/add_class', methods=['GET', 'POST'])
@login_required
@admin_required
def add_class():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        schedule_str = request.form.get('schedule')
        capacity = request.form.get('capacity')
        days_of_week = request.form.get('days_of_week')
        extra_info = request.form.get('extra_info')

        try:
            schedule = datetime.strptime(schedule_str, '%Y-%m-%d %H:%M')
            capacity = int(capacity)
            days = [day.strip() for day in days_of_week.split(',')]
            # Проверка валидности дней
            valid_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            for day in days:
                if day not in valid_days:
                    raise ValueError(f'Неверный день недели: {day}')
        except ValueError as e:
            flash(f'Ошибка: {e}', 'danger')
            return redirect(url_for('admin.add_class'))

        new_class = Class(
            name=name,
            description=description,
            schedule=schedule,
            capacity=capacity,
            days_of_week=', '.join(days),
            extra_info=extra_info
        )
        db.session.add(new_class)
        db.session.commit()
        flash('Новый класс успешно добавлен.', 'success')
        return redirect(url_for('admin.admin_panel'))

    return render_template('add_class.html')



# Редактирование класса
@admin_bp.route('/edit_class/<int:class_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_class(class_id):
    class_ = Class.query.get_or_404(class_id)

    if request.method == 'POST':
        class_.name = request.form.get('name')
        class_.description = request.form.get('description')
        schedule_str = request.form.get('schedule')
        capacity = request.form.get('capacity')
        days_of_week = request.form.get('days_of_week')
        extra_info = request.form.get('extra_info')

        try:
            class_.schedule = datetime.strptime(schedule_str, '%Y-%m-%d %H:%M')
            class_.capacity = int(capacity)
            days = [day.strip() for day in days_of_week.split(',')]
            # Проверка валидности дней
            valid_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            for day in days:
                if day not in valid_days:
                    raise ValueError(f'Неверный день недели: {day}')
            class_.days_of_week = ', '.join(days)
            class_.extra_info = extra_info
        except ValueError as e:
            flash(f'Ошибка: {e}', 'danger')
            return redirect(url_for('admin.edit_class', class_id=class_id))

        db.session.commit()
        flash('Класс успешно обновлён.', 'success')
        return redirect(url_for('admin.admin_panel'))

    # Подготовка данных для формы редактирования
    available_days = class_.days_of_week.split(', ') if class_.days_of_week else []
    return render_template('edit_class.html', class_=class_, available_days=available_days)



@admin_bp.route('/delete_class/<int:class_id>', methods=['POST'])
@login_required
@admin_required
def delete_class(class_id):
    class_ = Class.query.get_or_404(class_id)

    # Проверка наличия бронирований
    if class_.bookings:
        flash('Невозможно удалить класс с существующими бронированиями.', 'warning')
        return redirect(url_for('admin.admin_panel'))

    db.session.delete(class_)
    db.session.commit()
    flash('Класс успешно удалён.', 'success')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)

    # Запрещаем администратору удалять самого себя
    if user_to_delete.id == current_user.id:
        flash('Вы не можете удалить свой собственный аккаунт.', 'danger')
        return redirect(url_for('admin.admin_panel'))

    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'Пользователь {user_to_delete.username} успешно удалён.', 'success')
    return redirect(url_for('admin.admin_panel'))