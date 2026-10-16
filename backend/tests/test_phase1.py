from tests.helpers import confirm_offline_payment


def login(client):
    response = client.post("/api/auth/login", json={"account": "demo@eprflow.com", "password": "Demo123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_login_rejects_invalid_password(client):
    response = client.post("/api/auth/login", json={"account": "demo", "password": "wrong-password"})
    assert response.status_code == 401


def test_create_and_list_application(client):
    headers = login(client)
    order = client.post("/api/portal/orders", json={"service_id": "de-weee", "service_year": "2026年（自然年）", "quantity": 1}, headers=headers)
    created = confirm_offline_payment(client, headers, order).json()["service_instances"][0]
    assert created["status"] == "DRAFT"
    assert created["application_no"].startswith("EPR")

    listed = client.get("/api/applications", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["country"] == "Germany"


def test_catalog_is_available(client):
    response = client.get("/api/catalog/countries")
    assert response.status_code == 200
    germany = next(item for item in response.json() if item["value"] == "Germany")
    assert "WEEE" in [service["value"] for service in germany["services"]]


def test_rejects_unknown_country_service_pair(client):
    response = client.post(
        "/api/portal/orders",
        json={"service_id": "unknown", "service_year": "2026年（自然年）", "quantity": 1},
        headers=login(client),
    )
    assert response.status_code == 404


def test_customer_cannot_create_unpaid_service_instance(client):
    response = client.post("/api/applications", json={"country": "Germany", "service_type": "WEEE"}, headers=login(client))
    assert response.status_code == 409
    assert "完成付款" in response.json()["detail"]
