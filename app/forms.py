# app/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User
from password_validator import PasswordValidator

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