
def test_payment_endpoint(client, access_token):
    response = client.post(
        "/api/v1/payment",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
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
