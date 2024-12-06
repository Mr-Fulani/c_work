# add_classes.py

from app import create_app, db
from app.models import Class
from datetime import datetime

app = create_app()

with app.app_context():
    classes_to_add = [
        {
            'name': 'MMA',
            'description': 'Изучите основы бокса, включая удары и передвижение.',
            'schedule': datetime(2024, 12, 7, 18, 0, 0),
            'capacity': 20,
            'days_of_week': 'Mon, Wed, Fri',  # Дни недели на английском
            'extra_info': 'Приносите свою перчатку.'
        }
    ]

    for cls in classes_to_add:
        new_class = Class(
            name=cls['name'],
            description=cls['description'],
            schedule=cls['schedule'],
            capacity=cls['capacity'],
            days_of_week=cls['days_of_week'],
            extra_info=cls['extra_info']
        )
        db.session.add(new_class)

    try:
        db.session.commit()
        print("Все классы успешно добавлены.")
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при добавлении классов: {e}")
