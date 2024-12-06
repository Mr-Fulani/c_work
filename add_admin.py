from app import create_app, db
from app.models import User
from flask_bcrypt import Bcrypt

app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    # Удаляем старого администратора
    admin = User.query.filter_by(email="admin@example.com").first()
    if admin:
        db.session.delete(admin)
        db.session.commit()
        print("Старый администратор успешно удалён.")

    # Добавляем нового администратора
    new_admin = User(
        username="admin",
        email="admin@example.com",
        password=bcrypt.generate_password_hash("adminpassword").decode('utf-8'),
        is_admin=True
    )
    db.session.add(new_admin)
    db.session.commit()
    print("Новый администратор успешно добавлен.")
