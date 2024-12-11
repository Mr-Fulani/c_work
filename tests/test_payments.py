# tests/test_payments.py

import stripe

def test_payment_endpoint(client, user_access_token, mocker):
    # Мокаем метод создания платежа в Stripe
    mock_create_payment_intent = mocker.patch('stripe.PaymentIntent.create')
    mock_create_payment_intent.return_value = {
        "id": "pi_123456789",
        "client_secret": "pi_123456789_secret_abcdef",
        "status": "succeeded",
        "charges": {
            "data": []
        }
    }

    response = client.post(
        "/api/v1/payment",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_access_token}"
        },
        json={
            "amount": 2000,
            "currency": "gbp",
            "description": "Payment for services",
            "payment_method_id": "pm_card_visa"
        }
    )

    # Проверка статуса ответа
    assert response.status_code == 200, f"Ожидалось 200, но получили {response.status_code}. Ответ: {response.data.decode('utf-8')}"

    # Получение и проверка JSON-данных
    data = response.get_json()
    assert data is not None, "Ответ не является JSON"
    assert data.get("success") == True, f"Ожидалось 'success=True', но получили {data.get('success')}"
    assert "client_secret" in data, "Поле 'client_secret' отсутствует в ответе"

    # Проверка, что Stripe API был вызван с правильными параметрами
    mock_create_payment_intent.assert_called_once_with(
        amount=2000,
        currency='gbp',
        description='Payment for services',
        payment_method='pm_card_visa',
        confirm=True
    )





# tests/test_payments.py

def test_payment_endpoint(client, user_access_token, mocker):
    # Мокаем метод создания платежа в Stripe
    mock_create_payment_intent = mocker.patch('stripe.PaymentIntent.create')
    mock_create_payment_intent.return_value = mocker.Mock(
        id="pi_123456789",
        client_secret="pi_123456789_secret_abcdef",
        status="succeeded",
        charges=mocker.Mock(data=[])
    )

    response = client.post(
        "/api/v1/payment",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {user_access_token}"
        },
        json={
            "amount": 2000,
            "currency": "gbp",
            "description": "Payment for services",
            "payment_method_id": "pm_card_visa"
        }
    )

    # Проверка статуса ответа
    assert response.status_code == 200, f"Ожидалось 200, но получили {response.status_code}. Ответ: {response.data.decode('utf-8')}"


def test_payment_endpoint_admin(client, admin_access_token, mocker):
    # Мокаем метод создания платежа в Stripe
    mock_create_payment_intent = mocker.patch('stripe.PaymentIntent.create')
    mock_create_payment_intent.return_value = mocker.Mock(
        id="pi_987654321",
        client_secret="pi_987654321_secret_abcdef",
        status="succeeded",
        charges=mocker.Mock(data=[])
    )

    response = client.post(
        "/api/v1/payment",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_access_token}"
        },
        json={
            "amount": 3000,
            "currency": "usd",
            "description": "Admin Payment",
            "payment_method_id": "pm_card_mastercard"
        }
    )

    # Проверка статуса ответа
    assert response.status_code == 200, f"Ожидалось 200, но получили {response.status_code}. Ответ: {response.data.decode('utf-8')}"





