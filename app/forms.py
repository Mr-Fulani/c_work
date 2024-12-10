# app/forms.py
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from password_validator import PasswordValidator
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms import widgets
from wtforms.fields.choices import SelectMultipleField, SelectField
from wtforms.fields.datetime import DateTimeField
from wtforms.fields.numeric import IntegerField, DecimalField
from wtforms.fields.simple import TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange

from app.models import User, Class


class LoginForm(FlaskForm):
    email_or_username = StringField('Email or Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(),
        Length(min=2, max=20, message='Имя пользователя должно быть от 2 до 20 символов.')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Неверный формат email.')
    ])
    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=8, message='Пароль должен быть не менее 8 символов.')
    ])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        DataRequired(),
        EqualTo('password', message='Пароли должны совпадать.')
    ])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data.strip()).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.strip().lower()).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован.')

    def validate_password(self, password):
        schema = PasswordValidator()
        schema.min(8).max(100).has().uppercase().has().lowercase().has().digits().has().symbols()
        if not schema.validate(password.data):
            raise ValidationError('Пароль должен содержать минимум 8 символов, включая буквы, цифры и специальные символы.')







class MultiCheckboxField(SelectMultipleField):
    """
    Поле для мультивыбора с чекбоксами.
    Использует виджет ListWidget и CheckboxInput для отображения как набора чекбоксов.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()




class ClassForm(FlaskForm):
    """
    Форма для добавления/редактирования класса.

    Поля:
        name, description, schedule, capacity, extra_info: как раньше.
        image: для загрузки изображения.
        days_of_week: мультивыбор чекбоксами.
    """
    name = StringField('Название Класса', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Описание', validators=[Length(max=500)])
    schedule = DateTimeField('Расписание (YYYY-MM-DD HH:MM)', validators=[DataRequired()], format='%Y-%m-%d %H:%M')
    capacity = IntegerField('Вместимость', validators=[DataRequired(), NumberRange(min=1)])
    # Используем SelectMultipleField для выбора дней
    days_of_week = SelectMultipleField(
        'Дни Недели',
        choices=[
            ('Mon', 'Понедельник'),
            ('Tue', 'Вторник'),
            ('Wed', 'Среда'),
            ('Thu', 'Четверг'),
            ('Fri', 'Пятница'),
            ('Sat', 'Суббота'),
            ('Sun', 'Воскресенье')
        ],
        validators=[DataRequired()],
        description="Выберите один или несколько дней недели"
    )
    extra_info = TextAreaField('Дополнительная Информация', validators=[Length(max=500)])
    image = FileField('Изображение Класса', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Только изображения!')
    ])
    submit = SubmitField('Сохранить')






class BookingForm(FlaskForm):
    class_id = HiddenField('Class ID', validators=[DataRequired()])
    submit = SubmitField('Забронировать')

class SelectDayForm(FlaskForm):
    day = SelectField('День Недели', validators=[DataRequired()], choices=[])
    submit = SubmitField('Забронировать')

class CancelBookingForm(FlaskForm):
    booking_id = HiddenField('Booking ID', validators=[DataRequired()])
    submit = SubmitField('Отменить')





class PromoteUserForm(FlaskForm):
    user_id = HiddenField('User ID', validators=[DataRequired()])
    submit = SubmitField('Назначить администратором')

class DemoteUserForm(FlaskForm):
    user_id = HiddenField('User ID', validators=[DataRequired()])
    submit = SubmitField('Отстранить от администраторов')

class DeleteUserForm(FlaskForm):
    user_id = HiddenField('User ID', validators=[DataRequired()])
    submit = SubmitField('Удалить Пользователя')

class DeleteClassForm(FlaskForm):
    class_id = HiddenField('Class ID', validators=[DataRequired()])
    submit = SubmitField('Удалить Класс')







class UpdateProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(),
        Length(min=2, max=20)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    avatar = FileField('Обновить аватар', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Только изображения!')
    ])
    submit = SubmitField('Обновить')

    def validate_username(self, username):
        if username.data.strip() != current_user.username:
            user = User.query.filter_by(username=username.data.strip()).first()
            if user:
                raise ValidationError('Это имя пользователя уже занято.')

    def validate_email(self, email):
        if email.data.strip().lower() != current_user.email:
            user = User.query.filter_by(email=email.data.strip().lower()).first()
            if user:
                raise ValidationError('Этот email уже зарегистрирован.')





class AddBookingForm(FlaskForm):
    class_id = SelectField('Класс', coerce=int, validators=[DataRequired()])
    day = SelectField('День недели', choices=[
        ('Понедельник', 'Понедельник'),
        ('Вторник', 'Вторник'),
        ('Среда', 'Среда'),
        ('Четверг', 'Четверг'),
        ('Пятница', 'Пятница'),
        ('Суббота', 'Суббота'),
        ('Воскресенье', 'Воскресенье')
    ], validators=[DataRequired()])
    submit = SubmitField('Добавить Бронирование')

    def __init__(self, *args, **kwargs):
        super(AddBookingForm, self).__init__(*args, **kwargs)
        # Заполнение поля class_id динамически из базы данных
        self.class_id.choices = [(cls.id, cls.name) for cls in Class.query.order_by(Class.name).all()]






class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Текущий Пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый Пароль', validators=[
        DataRequired(),
        Length(min=6, message='Пароль должен содержать минимум 6 символов.')
    ])
    confirm_new_password = PasswordField('Подтвердите Новый Пароль', validators=[
        DataRequired(),
        EqualTo('new_password', message='Пароли должны совпадать.')
    ])
    submit = SubmitField('Изменить Пароль')







class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message='Неверный формат email.')])
    submit = SubmitField('Отправить ссылку для сброса пароля')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Новый Пароль', validators=[
        DataRequired(),
        Length(min=8, message='Пароль должен быть не менее 8 символов.')
    ])
    confirm_password = PasswordField('Подтвердите Пароль', validators=[
        DataRequired(),
        EqualTo('password', message='Пароли должны совпадать.')
    ])
    submit = SubmitField('Сбросить Пароль')







class PaymentForm(FlaskForm):
    amount = DecimalField(
        'Сумма (USD)',
        validators=[
            DataRequired(),
            NumberRange(min=1, message='Минимальная сумма: 1$')
        ],
        places=2
    )
    submit = SubmitField('Оплатить')