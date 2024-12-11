# run.py

import logging
from app import create_app, db


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

with app.app_context():
    db.create_all()
    logger.info("Database created or already exists.")

if __name__ == '__main__':
    """
    Entry point for running the Flask application.
    The application will run on host 0.0.0.0 and port 5000 in debug mode.
    """
    app.run(host='0.0.0.0', port=5000, debug=True)
