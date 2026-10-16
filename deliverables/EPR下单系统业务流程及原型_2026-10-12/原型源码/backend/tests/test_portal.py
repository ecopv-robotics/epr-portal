from tests.helpers import confirm_offline_payment


def login(client):
    response = client.post("/api/auth/login", json={"account": "demo@eprflow.com", "password": "Demo123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_portal_catalog_and_countries(client):
    catalog = client.get("/api/portal/catalog")
    assert catalog.status_code == 200
    assert any(item["id"] == "de-weee" for item in catalog.json())
    germany_weee = next(item for item in catalog.json() if item["id"] == "de-weee")
    assert germany_weee["reporting_frequency"] == "月度申报"
    assert germany_weee["subject_types"] == ["德国公司", "非德国公司"]
    assert germany_weee["package_types"] == ["一品一类", "多品多类"]
    countries = client.get("/api/portal/catalog/countries")
    assert countries.status_code == 200
    assert "德国" in countries.json()
    assert "西班牙" in countries.json()


def test_cart_is_user_scoped_and_persistent(client):
    headers = login(client)
    created = client.post("/api/portal/cart", json={"service_id": "de-weee"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["service"]["title"] == "德国 WEEE 注册"
    duplicate = client.post("/api/portal/cart", json={"service_id": "de-weee"}, headers=headers)
    assert duplicate.status_code == 201
    listed = client.get("/api/portal/cart", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    deleted = client.delete(f"/api/portal/cart/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/api/portal/cart", headers=headers).json() == []


def test_dashboard_messages_and_manager(client):
    headers = login(client)
    order = client.post("/api/portal/orders", json={"service_id": "de-weee", "service_year": "2026年（自然年）", "quantity": 1}, headers=headers)
    paid = confirm_offline_payment(client, headers, order)
    application_id = paid.json()["service_instances"][0]["id"]
    dashboard = client.get("/api/portal/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["pending_materials"] == 1
    assert dashboard.json()["todos"][0]["application_id"] == application_id
    messages = client.get("/api/portal/messages", headers=headers)
    assert messages.status_code == 200
    assert isinstance(messages.json(), list)
    manager = client.get("/api/portal/manager", headers=headers)
    assert manager.status_code == 200
    assert manager.json()["role"] == "专属客户经理"


def test_paid_purchase_order_creates_pending_material_application(client):
    headers = login(client)
    created = client.post("/api/portal/orders", headers=headers, json={
        "service_id": "de-weee", "service_year": "2026年（自然年）",
        "quantity": 2,
    })
    assert created.status_code == 201
    assert created.json()["status"] == "PENDING"
    assert created.json()["total_amount"] == 2560
    assert created.json()["application_id"] is None
    listed_before_payment = client.get("/api/portal/orders", headers=headers)
    assert listed_before_payment.status_code == 200
    assert listed_before_payment.json()[0]["status"] == "PENDING"
    paid = confirm_offline_payment(client, headers, created)
    assert paid.status_code == 200
    assert paid.json()["status"] == "PAID"
    assert paid.json()["payment_method"] == "OFFLINE"
    listed_after_payment = client.get("/api/portal/orders", headers=headers)
    assert listed_after_payment.json()[0]["status"] == "PAID"
    assert paid.json()["application_id"] is not None
    assert len(paid.json()["service_instances"]) == 2
    assert [item["instance_index"] for item in paid.json()["service_instances"]] == [1, 2]
    assert all(item["status"] == "DRAFT" for item in paid.json()["service_instances"])
    paid_again = client.post(f"/api/portal/orders/{created.json()['id']}/pay", headers=headers, json={"payment_method": "OFFLINE", "payer_name": "测试付款账户", "payment_proof": "customer-transfer.png"})
    assert len(paid_again.json()["service_instances"]) == 2
    applications = client.get("/api/applications", headers=headers).json()["items"]
    application = next(item for item in applications if item["id"] == paid.json()["application_id"])
    assert application["status"] == "DRAFT"
    assert application["country"] == "Germany"
    assert application["service_type"] == "WEEE"
    assert application["purchase_order_id"] == created.json()["id"]
    assert client.post(f"/api/portal/orders/{created.json()['id']}/cancel", headers=headers).status_code == 409


def test_offline_payment_requires_payer_and_proof(client):
    headers = login(client)
    created = client.post("/api/portal/orders", headers=headers, json={
        "service_id": "fr-pack", "service_year": "2026年（自然年）",
        "quantity": 1,
    })
    response = client.post(f"/api/portal/orders/{created.json()['id']}/pay", headers=headers, json={"payment_method": "OFFLINE"})
    assert response.status_code == 422
    assert "转账凭证" in response.json()["detail"]


def test_cancel_pending_order_and_confirm_offline_payment(client):
    customer = login(client)
    admin_login = client.post("/api/auth/login", json={"account": "admin@eprflow.com", "password": "Admin123!"})
    admin = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    cancelled = client.post("/api/portal/orders", headers=customer, json={
        "service_id": "de-weee", "service_year": "2026年（自然年）", "quantity": 1,
    })
    cancel_response = client.post(f"/api/portal/orders/{cancelled.json()['id']}/cancel", headers=customer)
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"

    created = client.post("/api/portal/orders", headers=customer, json={
        "service_id": "de-weee", "service_year": "2026年（自然年）", "quantity": 2,
    })
    confirming = client.post(f"/api/portal/orders/{created.json()['id']}/pay", headers=customer, json={
        "payment_method": "OFFLINE", "payer_name": "深圳测试有限公司", "payment_proof": "transfer.png",
    })
    assert confirming.status_code == 200
    assert confirming.json()["status"] == "PAYMENT_CONFIRMING"
    assert confirming.json()["service_instances"] == []

    approved = client.post(f"/api/admin/orders/{created.json()['id']}/payment-review", headers=admin, json={"approved": True, "actual_paid_amount": created.json()["total_amount"], "finance_receipt": "bank-receipt.png"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "PAID"
    assert len(approved.json()["service_instances"]) == 2
    order_list = client.get("/api/admin/orders", headers=admin)
    assert order_list.status_code == 200
    assert any(item["id"] == created.json()["id"] for item in order_list.json())


def test_cart_checkout_package_discount_contract_and_finance_receipt(client):
    customer = login(client)
    admin_login = client.post("/api/auth/login", json={"account": "admin@eprflow.com", "password": "Admin123!"})
    admin = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    first = client.post("/api/portal/cart", headers=customer, json={"service_id": "de-weee"}).json()
    second = client.post("/api/portal/cart", headers=customer, json={"service_id": "fr-pack"}).json()
    checkout = client.post("/api/portal/cart/checkout", headers=customer, json={"items": [
        {"cart_item_id": first["id"], "service_year": first["service"]["service_years"][0], "quantity": 1},
        {"cart_item_id": second["id"], "service_year": second["service"]["service_years"][0], "quantity": 1},
    ]})
    assert checkout.status_code == 201
    orders = checkout.json()
    assert len(orders) == 2
    assert len({item["batch_no"] for item in orders}) == 1
    assert client.get("/api/portal/cart", headers=customer).json() == []

    standard_total = sum(item["standard_amount"] for item in orders)
    package_total = standard_total - 500
    discounted = client.post("/api/admin/orders/package-discount", headers=admin, json={
        "order_ids": [item["id"] for item in orders], "package_total": package_total, "reason": "多个服务打包优惠",
    })
    assert discounted.status_code == 200
    assert sum(item["total_amount"] for item in discounted.json()) == package_total
    assert sum(item["discount_amount"] for item in discounted.json()) == 500

    order = discounted.json()[0]
    contract = client.put(f"/api/admin/orders/{order['id']}/contract", headers=admin, json={
        "contract_no": "HT-TEST-001", "contract_version": "V1", "contract_file": "/files/contracts/test.pdf",
    })
    assert contract.status_code == 200
    assert contract.json()["contract_no"] == "HT-TEST-001"

    submitted = client.post(f"/api/portal/orders/{order['id']}/pay", headers=customer, json={
        "payment_method": "OFFLINE", "payer_name": "测试付款账户", "payment_proof": "/files/payments/customer.png",
    })
    assert submitted.json()["status"] == "PAYMENT_CONFIRMING"
    missing_receipt = client.post(f"/api/admin/orders/{order['id']}/payment-review", headers=admin, json={"approved": True})
    assert missing_receipt.status_code == 422
    confirmed = client.post(f"/api/admin/orders/{order['id']}/payment-review", headers=admin, json={
        "approved": True, "actual_paid_amount": order["total_amount"], "finance_receipt": "/files/payments/bank.png",
    })
    assert confirmed.status_code == 200
    assert confirmed.json()["actual_paid_amount"] == order["total_amount"]
    assert confirmed.json()["status"] == "PAID"
