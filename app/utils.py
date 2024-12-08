# app/utils.py
import random
import string

from flask import current_app






def allowed_file(filename):
    """
    Проверяет, что у файла есть точка и расширение входит в разрешённые.

    Args:
        filename (str): Имя файла.

    Returns:
        bool: True, если расширение допустимо, иначе False.
    """
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']




def random_string(length=8):
    """Генерирует случайную строку для уникальности имен файлов."""
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(length))