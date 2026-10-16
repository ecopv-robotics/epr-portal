def confirm_offline_payment(client, customer_headers, order):
    order_data = order.json() if hasattr(order, "json") else order
    submitted = client.post(
        f"/api/portal/orders/{order_data['id']}/pay",
        headers=customer_headers,
        json={"payment_method": "OFFLINE", "payer_name": "测试付款账户", "payment_proof": "customer-transfer.png"},
    )
    assert submitted.status_code == 200
    admin_login = client.post("/api/auth/login", json={"account": "admin@eprflow.com", "password": "Demo123!"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    confirmed = client.post(
        f"/api/admin/orders/{order_data['id']}/payment-review",
        headers=admin_headers,
        json={"approved": True, "actual_paid_amount": order_data["total_amount"], "finance_receipt": "bank-receipt.png"},
    )
    assert confirmed.status_code == 200
    return confirmed
