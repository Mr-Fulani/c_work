# c_work

## Описание

c_work - это веб-приложение для управления пользователями, бронированиями и платежами с использованием Flask и SQLite.

## Структура Проекта


c_work/
│
├── app/
│   ├── init.py
│   ├── models.py
│   ├── routes.py
│   └── templates/
│       ├── home.html
│       ├── register.html
│       └── login.html
│
├── docs/
│   ├── README.md
│   ├── функциональные_требования.md
│   ├── техническая_документация.md
│   └── пользовательская_документация.md
│
├── tests/
│   ├── init.py
│   ├── test_auth.py
│   ├── test_booking.py
│   └── test_payments.py
│
├── venv/
│
├── requirements.txt
├── run.py
├── config.py
├── README.md
├── .gitignore
└── .env.example


## Установка

1. **Клонирование репозитория:**

    ```bash
    git clone https://github.com/ваш-репозиторий/c_work.git
    cd c_work
    ```

2. **Создание виртуального окружения:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Для Windows: venv\Scripts\activate
    ```

3. **Установка зависимостей:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Настройка переменных окружения:**

    - Скопируйте файл `.env.example` в `.env` и заполните необходимые поля.

        ```bash
        cp .env.example .env
        ```

5. **Инициализация базы данных:**

    ```bash
    python run.py
    ```

6. **Запуск приложения:**

    ```bash
    python run.py
    ```

    Откройте браузер и перейдите по адресу `http://127.0.0.1:5000/`, чтобы увидеть ваше приложение в действии.

## Использование

Инструкции по использованию приложения описаны в папке `docs/`.

## Тестирование

Запустите тесты с помощью `pytest`:

```bash
pytest