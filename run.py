# run.py

import logging
from app import create_app, db
from app.models import User, Class, Booking, Payment



# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

with app.app_context():
    db.create_all()
    logger.info("База данных создана или уже существует.")

if __name__ == '__main__':
    logger.info("Запуск Flask-приложения.")
    app.run(debug=True)