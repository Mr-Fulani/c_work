# tests/test_auth.py
from app.models import User


def login(client, email, password):
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

def logout(client):
    return client.get('/logout', follow_redirects=True)

def test_register_success(client, app):
    """
    Тест успешной регистрации пользователя.
    """
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Ваш аккаунт создан! Вы можете войти.' in response.data.decode('utf-8')

    # Проверка, что пользователь добавлен в базу данных
    with app.app_context():
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.username == 'newuser'
        assert user.is_admin == False

def test_register_existing_email(client, app):
    """
    Тест регистрации с существующим email.
    """
    response = client.post('/register', data={
        'username': 'anotheruser',
        'email': 'test1@example.com',  # Уже зарегистрирован
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Этот email уже зарегистрирован.' in response.data.decode('utf-8')

def test_register_existing_username(client, app):
    """
    Тест регистрации с существующим именем пользователя.
    """
    response = client.post('/register', data={
        'username': 'testuser1',  # Уже существует
        'email': 'uniqueemail@example.com',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Это имя пользователя уже занято.' in response.data.decode('utf-8')

def test_register_weak_password(client):
    """
    Тест регистрации с слабым паролем.
    """
    response = client.post('/register', data={
        'username': 'weakpassworduser',
        'email': 'weakpass@example.com',
        'password': 'weak',
        'confirm_password': 'weak'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Пароль должен быть не менее 8 символов.' in response.data.decode('utf-8')

def test_register_password_no_special_char(client):
    """
    Тест регистрации с паролем без специальных символов.
    """
    response = client.post('/register', data={
        'username': 'nospecialcharuser',
        'email': 'nospecial@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Пароль должен содержать буквы, цифры и специальные символы' in response.data.decode('utf-8')

def test_login_success(client, app, access_token):
    """
    Тест успешного входа пользователя.
    """
    # Предполагается, что вы используете JWT для API
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = client.get('/protected-route', headers=headers)
    assert response.status_code == 200
    assert 'Доступ разрешен' in response.data.decode('utf-8')

def test_login_wrong_password(client):
    """
    Тест входа с неправильным паролем.
    """
    response = client.post('/login', data={
        'email': 'test1@example.com',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Неверные данные для входа. Пожалуйста, попробуйте снова.' in response.data.decode('utf-8')

def test_login_nonexistent_user(client):
    """
    Тест входа с несуществующим пользователем.
    """
    response = client.post('/login', data={
        'email': 'nonexistent@example.com',
        'password': 'Password@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Неверные данные для входа. Пожалуйста, попробуйте снова.' in response.data.decode('utf-8')