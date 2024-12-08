# app/admin_routes.py
import logging
import os
import random
import string
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename

from app import db
from app.forms import ClassForm, DeleteClassForm, PromoteUserForm, DemoteUserForm, DeleteUserForm, AddBookingForm
from app.models import User, Class, Booking, ActionLog, Payment
from flask_login import login_required, current_user
from functools import wraps

from app.utils import allowed_file, random_string

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Декоратор для проверки прав администратора
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Доступ запрещён. Требуются права администратора.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


# Панель администратора
@admin_bp.route('/')
@login_required
@admin_required
def admin_panel():
    try:
        # Предварительная загрузка бронирований и связанных классов
        users = User.query.options(
            joinedload(User.bookings).joinedload(Booking.class_),
            joinedload(User.payments)
        ).order_by(User.username.asc()).all()

        classes = Class.query.order_by(Class.schedule.asc()).all()

        # Создание формы для удаления классов
        delete_class_forms = {class_.id: DeleteClassForm(class_id=class_.id) for class_ in classes}

        # Создание форм для управления пользователями
        promote_user_forms = {user.id: PromoteUserForm(user_id=user.id) for user in users if not user.is_admin}
        demote_user_forms = {user.id: DemoteUserForm(user_id=user.id) for user in users if user.is_admin}
        delete_user_forms = {user.id: DeleteUserForm(user_id=user.id) for user in users if user.id != current_user.id}

        # Получение количества подтверждённых бронирований для всех классов за один запрос
        booking_counts = db.session.query(
            Booking.class_id,
            db.func.count(Booking.id)
        ).filter_by(status='confirmed').group_by(Booking.class_id).all()

        # Создание словаря с количеством бронирований
        bookings_dict = {class_id: count for class_id, count in booking_counts}

        # Вычисление доступных мест для каждого класса
        available_spots = {}
        for class_ in classes:
            confirmed_bookings = bookings_dict.get(class_.id, 0)
            available = class_.capacity - confirmed_bookings
            available_spots[class_.id] = available if available >= 0 else 0  # Предотвращение отрицательных значений

        return render_template(
            'admin_panel.html',
            users=users,
            classes=classes,
            delete_class_forms=delete_class_forms,
            promote_user_forms=promote_user_forms,
            demote_user_forms=demote_user_forms,
            delete_user_forms=delete_user_forms,
            available_spots=available_spots  # Передача данных о доступных местах
        )
    except Exception as e:
        logger.error(f"Ошибка в admin_panel: {e}")
        flash('Произошла ошибка при загрузке панели администратора.', 'danger')
        return redirect(url_for('main.home'))


# Добавление Администратора
@admin_bp.route('/promote_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def promote_user(user_id):
    form = PromoteUserForm()
    if form.validate_on_submit() and int(form.user_id.data) == user_id:
        user = User.query.get_or_404(user_id)
        if user.is_admin:
            flash(f'Пользователь {user.username} уже является администратором.', 'info')
        else:
            user.is_admin = True
            db.session.commit()
            flash(f'Пользователь {user.username} успешно назначен администратором.', 'success')
    else:
        flash('Ошибка при обработке запроса.', 'danger')
    return redirect(url_for('admin.admin_panel'))



@admin_bp.route('/demote/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def demote_user(user_id):
    form = DemoteUserForm()
    if form.validate_on_submit() and int(form.user_id.data) == user_id:
        user = User.query.get_or_404(user_id)
        if not user.is_admin:
            flash(f'Пользователь {user.username} уже не является администратором.', 'info')
        elif user.id == current_user.id:
            flash('Вы не можете понизить собственные административные права.', 'danger')
        else:
            user.is_admin = False
            db.session.commit()
            flash(f'Пользователь {user.username} успешно понижен из администраторов.', 'success')
    else:
        flash('Ошибка при обработке запроса.', 'danger')
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/delete_class/<int:class_id>', methods=['POST'])
@login_required
@admin_required
def delete_class(class_id):
    form = DeleteClassForm()
    if form.validate_on_submit() and int(form.class_id.data) == class_id:
        class_ = Class.query.get_or_404(class_id)

        # Проверка наличия подтверждённых бронирований
        confirmed_bookings = Booking.query.filter_by(class_id=class_id, status='confirmed').count()
        logger.info(f"Attempting to delete class ID {class_id}. Confirmed bookings: {confirmed_bookings}")

        if confirmed_bookings > 0:
            flash('Невозможно удалить класс с активными бронированиями.', 'warning')
            return redirect(url_for('admin.admin_panel'))

        # Удаление класса. Благодаря cascade все связанные бронирования будут удалены автоматически.
        db.session.delete(class_)
        db.session.commit()
        logger.info(f"Class ID {class_id} successfully deleted.")
        flash('Класс успешно удалён.', 'success')
    else:
        logger.error(f"Failed to delete class ID {class_id}. Form validation failed.")
        flash('Ошибка при обработке запроса.', 'danger')
    return redirect(url_for('admin.admin_panel'))




@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    form = DeleteUserForm()
    if form.validate_on_submit() and int(form.user_id.data) == user_id:
        user_to_delete = User.query.get_or_404(user_id)

        # Запрещаем администратору удалять самого себя
        if user_to_delete.id == current_user.id:
            flash('Вы не можете удалить свой собственный аккаунт.', 'danger')
            return redirect(url_for('admin.admin_panel'))

        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'Пользователь {user_to_delete.username} успешно удалён.', 'success')
    else:
        flash('Ошибка при обработке запроса.', 'danger')
    return redirect(url_for('admin.admin_panel'))



# Добавление класса
@admin_bp.route('/add_class', methods=['GET', 'POST'])
@login_required
def add_class():
    if not current_user.is_admin:
        flash('У вас нет прав на добавление класса.', 'danger')
        return redirect(url_for('main.home'))

    form = ClassForm()
    if form.validate_on_submit():
        # Преобразуем список дней недели в строку
        days_of_week = ','.join(form.days_of_week.data)

        # Создаём новый объект класса
        new_class = Class(
            name=form.name.data,
            description=form.description.data,
            schedule=form.schedule.data,
            capacity=form.capacity.data,
            days_of_week=days_of_week,
            extra_info=form.extra_info.data
        )

        # Обработка загрузки изображения
        if form.image.data:
            image_file = form.image.data
            filename = secure_filename(image_file.filename)
            # Добавляем случайную строку для уникальности имени файла
            unique_suffix = random_string()
            filename = f"{unique_suffix}_{filename}"
            # Используем current_app.root_path для построения пути
            image_path = os.path.join(current_app.root_path, 'static', 'images', filename)
            try:
                image_file.save(image_path)
                new_class.image_filename = filename
                logger.info(f"Изображение сохранено как: {filename}")
            except Exception as e:
                logger.error(f"Ошибка сохранения изображения: {e}")
                flash('Ошибка при сохранении изображения.', 'danger')
                return render_template('add_class.html', form=form)

        # Добавляем класс в базу данных
        try:
            db.session.add(new_class)
            db.session.commit()
            flash('Класс успешно добавлен!', 'success')
            return redirect(url_for('main.classes'))
        except Exception as e:
            logger.error(f"Ошибка добавления класса в базу данных: {e}")
            flash('Ошибка при добавлении класса.', 'danger')
            db.session.rollback()

    return render_template('add_class.html', form=form)




@admin_bp.route('/edit_class/<int:class_id>', methods=['GET', 'POST'])
@login_required
def edit_class(class_id):
    class_ = Class.query.get_or_404(class_id)
    if not current_user.is_admin:
        flash('У вас нет прав на редактирование этого класса.', 'danger')
        return redirect(url_for('main.home'))

    form = ClassForm(obj=class_)

    if form.validate_on_submit():
        # Обновление полей формы
        class_.name = form.name.data
        class_.description = form.description.data
        class_.schedule = form.schedule.data
        class_.capacity = form.capacity.data
        class_.extra_info = form.extra_info.data

        # Преобразование списка дней недели в строку
        class_.days_of_week = ','.join(form.days_of_week.data)

        # Обработка удаления текущего изображения, если выбрано
        remove_image = request.form.get('remove_image')
        if remove_image:
            if class_.image_filename:
                old_image_path = os.path.join(current_app.root_path, 'static', 'images', class_.image_filename)
                if os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                        logger.info(f"Старое изображение {class_.image_filename} удалено.")
                    except Exception as e:
                        logger.error(f"Ошибка удаления изображения: {e}")
                        flash('Ошибка при удалении старого изображения.', 'danger')
                        return render_template('edit_class.html', form=form, class_=class_)
                class_.image_filename = None

        # Обработка загрузки нового изображения, если было выбрано новое
        if form.image.data:
            # Удаляем старое изображение, если оно существует
            if class_.image_filename:
                old_image_path = os.path.join(current_app.root_path, 'static', 'images', class_.image_filename)
                if os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                        logger.info(f"Старое изображение {class_.image_filename} удалено.")
                    except Exception as e:
                        logger.error(f"Ошибка удаления изображения: {e}")
                        flash('Ошибка при удалении старого изображения.', 'danger')
                        return render_template('edit_class.html', form=form, class_=class_)

            image_file = form.image.data
            filename = secure_filename(image_file.filename)
            # Добавляем случайную строку для уникальности имени файла
            unique_suffix = random_string()
            filename = f"{unique_suffix}_{filename}"
            image_path = os.path.join(current_app.root_path, 'static', 'images', filename)
            try:
                image_file.save(image_path)
                class_.image_filename = filename
                logger.info(f"Новое изображение сохранено как: {filename}")
            except Exception as e:
                logger.error(f"Ошибка сохранения изображения: {e}")
                flash('Ошибка при сохранении нового изображения.', 'danger')
                return render_template('edit_class.html', form=form, class_=class_)

        # Сохранение изменений в базе данных
        try:
            db.session.commit()
            flash('Класс успешно обновлён!', 'success')
            return redirect(url_for('main.classes'))
        except Exception as e:
            logger.error(f"Ошибка обновления класса в базе данных: {e}")
            flash('Ошибка при обновлении класса.', 'danger')
            db.session.rollback()

    # Если метод GET, преобразуем строку дней недели обратно в список
    if request.method == 'GET' and class_.days_of_week:
        form.days_of_week.data = class_.days_of_week.split(',')

    # Генерируем случайную строку для предотвращения кеширования изображения
    random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    return render_template('edit_class.html', form=form, class_=class_, random_string=random_suffix)







@admin_bp.route('/action_logs')
@login_required
@admin_required  # Предполагается, что у вас есть декоратор для проверки прав администратора
def action_logs():
    try:
        # Получаем номер страницы из запроса, по умолчанию 1
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Количество логов на странице

        # Запрос с предварительной загрузкой пользователей для избежания N+1 проблемы
        logs_pagination = ActionLog.query.options(joinedload(ActionLog.user)) \
            .order_by(ActionLog.timestamp.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        logs = logs_pagination.items

        return render_template('action_logs.html', logs=logs, pagination=logs_pagination)
    except Exception as e:
        logger.error(f"Ошибка при загрузке логов действий: {e}")
        flash('Произошла ошибка при загрузке логов действий.', 'danger')
        return redirect(url_for('admin.admin_panel'))



@admin_bp.route('/add_booking/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def add_booking(user_id):
    user = User.query.get_or_404(user_id)
    form = AddBookingForm()
    if form.validate_on_submit():
        class_id = form.class_id.data
        day = form.day.data
        # Проверка доступности места
        class_ = Class.query.get(class_id)
        if not class_:
            flash('Выбранный класс не существует.', 'danger')
            return redirect(url_for('admin.add_booking', user_id=user_id))

        # Проверка, не превышает ли бронирование вместимость класса
        confirmed_bookings = Booking.query.filter_by(class_id=class_id, day=day, status='confirmed').count()
        if confirmed_bookings >= class_.capacity:
            flash('Извините, на этот день места уже заполнены.', 'danger')
            return redirect(url_for('admin.add_booking', user_id=user_id))

        # Создание бронирования
        booking = Booking(user_id=user.id, class_id=class_id, day=day, status='confirmed')
        db.session.add(booking)
        db.session.commit()

        # Логирование добавления бронирования администратором
        action = ActionLog(
            user_id=current_user.id,
            action=f"Добавление бронирования для пользователя '{user.username}' на класс '{class_.name}' в день '{day}'",
            ip_address=request.remote_addr,
            status='success'
        )
        db.session.add(action)
        db.session.commit()

        flash('Бронирование успешно добавлено.', 'success')
        return redirect(url_for('admin.admin_panel'))
    return render_template('add_booking.html', form=form, user=user)




@admin_bp.route('/delete_booking/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    user = booking.user
    db.session.delete(booking)
    db.session.commit()

    # Логирование удаления бронирования администратором
    action = ActionLog(
        user_id=current_user.id,
        action=f"Удаление бронирования пользователя '{user.username}' на класс ID {booking.class_id} в день {booking.day}",
        ip_address=request.remote_addr,
        status='success'
    )
    db.session.add(action)
    db.session.commit()

    flash('Бронирование успешно удалено.', 'success')
    return redirect(url_for('admin.admin_panel'))







@admin_bp.route('/statistics')
@login_required
@admin_required
def statistics():
    try:
        # Популярные классы (наибольшее количество бронирований)
        popular_classes = db.session.query(
            Class.name,
            db.func.count(Booking.id).label('booking_count')
        ).join(Booking).filter(Booking.status == 'confirmed').group_by(Class.id).order_by(db.desc('booking_count')).limit(10).all()

        # Активность пользователей (наибольшее количество бронирований)
        active_users = db.session.query(
            User.username,
            db.func.count(Booking.id).label('booking_count')
        ).join(Booking).filter(Booking.status == 'confirmed').group_by(User.id).order_by(db.desc('booking_count')).limit(10).all()

        # Время занятий (например, бронирования по часам)
        bookings_by_hour = db.session.query(
            db.extract('hour', Class.schedule).label('hour'),
            db.func.count(Booking.id).label('booking_count')
        ).join(Booking).filter(Booking.status == 'confirmed').group_by('hour').order_by('hour').all()

        # Неактивные пользователи (не заходили более 30 дней)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        inactive_users = User.query.filter(
            (User.last_login < thirty_days_ago) | (User.last_login == None)
        ).all()

        # Количество успешных и неуспешных транзакций
        successful_payments = Payment.query.filter_by(status='paid').count()
        failed_payments = Payment.query.filter_by(status='failed').count()

        return render_template(
            'statistics.html',
            popular_classes=popular_classes,
            active_users=active_users,
            bookings_by_hour=bookings_by_hour,
            inactive_users=inactive_users,
            successful_payments=successful_payments,
            failed_payments=failed_payments
        )
    except Exception as e:
        logger.error(f"Ошибка при загрузке статистики: {e}")
        flash('Произошла ошибка при загрузке статистики.', 'danger')
        return redirect(url_for('admin.admin_panel'))