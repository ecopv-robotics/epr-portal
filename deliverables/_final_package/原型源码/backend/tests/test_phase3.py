from tests.helpers import confirm_offline_payment


def login(client, account="demo@eprflow.com", password="Demo123!"):
    response = client.post("/api/auth/login", json={"account": account, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_submission_review_and_status_history(client, monkeypatch):
    sent_emails = []
    monkeypatch.setattr(
        "app.modules.application.notifications.send_email",
        lambda recipients, subject, text: sent_emails.append((recipients, subject, text)) or True,
    )
    customer = login(client)
    order = client.post("/api/portal/orders", json={
        "service_id": "de-weee", "service_year": "2026年（自然年）", "quantity": 1,
    }, headers=customer)
    assert order.status_code == 201
    paid = confirm_offline_payment(client, customer, order)
    assert paid.status_code == 200
    assert paid.json()["status"] == "PAID"
    assert len(paid.json()["service_instances"]) == 1
    application_id = paid.json()["service_instances"][0]["id"]

    incomplete = client.post(f"/api/applications/{application_id}/submit", headers=customer)
    assert incomplete.status_code == 422
    assert "公司信息" in incomplete.json()["detail"]["missing_fields"]

    assert client.put(f"/api/applications/{application_id}/company", headers=customer, json={
        "company_name": "Phase 3 GmbH", "registration_region": "EU", "company_type": "Private Limited Company",
        "register_number": "HRB-003", "established_date": "2021-05-06", "vat_number": "DE999999999",
        "register_address": "Berlin", "license_file": "/files/company.pdf",
    }).status_code == 200
    assert client.put(f"/api/applications/{application_id}/legal-person", headers=customer, json={
        "certificate_type": "PASSPORT", "gender": "MALE", "name_cn": "李四", "name_en": "Si Li",
        "contact_email": "phase3@example.com", "contact_phone": "+49 100", "front_file": "/files/passport.jpg",
        "signature_file": "/files/signature.png",
    }).status_code == 200
    assert client.put(f"/api/applications/{application_id}/store", headers=customer, json={
        "platform": "Amazon", "store_url": "https://example.com/store", "company_name_en": "Phase 3 GmbH",
        "register_city_en": "Berlin", "postal_code": "10115", "register_address_en": "Example Street 3",
        "screenshot_file": "/files/store.png",
    }).status_code == 200
    assert client.put(f"/api/applications/{application_id}/products", headers=customer, json=[{"product_data": {
        "category": "大型设备，单边尺寸大于50cm", "name": "Device",
        "brand_logo": "Brand", "max_dimension_cm": 80, "estimated_sales": 1000,
    }}]).status_code == 200

    form = client.get(f"/api/applications/{application_id}/form", headers=customer).json()
    for requirement in form["template"]["materials"]:
        uploaded = client.post(
            "/api/material/upload", headers=customer,
            data={"application_id": application_id, "requirement_id": requirement["id"]},
            files={"file": (f"material-{requirement['id']}.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert uploaded.status_code == 200

    submitted = client.post(f"/api/applications/{application_id}/submit", headers=customer)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "SUBMITTED"
    assert any("staff@eprflow.com" in recipients and "待审核订单" in subject for recipients, subject, _ in sent_emails)
    locked = client.put(f"/api/applications/{application_id}/store", headers=customer, json={"platform": "eBay"})
    assert locked.status_code == 409
    assert client.get("/api/admin/applications", headers=customer).status_code == 403

    admin = login(client, "admin@eprflow.com", "Admin123!")
    staff = login(client, "staff@eprflow.com", "Staff123!")
    assert client.get("/api/admin/applications", headers=staff).status_code == 200
    review_list = client.get("/api/admin/applications?status=SUBMITTED", headers=admin)
    assert review_list.status_code == 200
    assert review_list.json()["total"] == 1
    assert client.patch(f"/api/admin/applications/{application_id}/status", headers=admin, json={"status": "REVIEWING"}).json()["status"] == "REVIEWING"
    need_fix = client.patch(f"/api/admin/applications/{application_id}/status", headers=admin, json={
        "status": "NEED_FIX", "note": "请更新店铺后台截图",
    })
    assert need_fix.status_code == 200
    assert need_fix.json()["review_note"] == "请更新店铺后台截图"

    editable = client.put(f"/api/applications/{application_id}/store", headers=customer, json={
        "platform": "Amazon", "store_url": "https://example.com/store", "company_name_en": "Phase 3 GmbH",
        "register_city_en": "Berlin", "postal_code": "10115", "register_address_en": "Example Street 3",
        "screenshot_file": "/files/store-new.png",
    })
    assert editable.status_code == 200
    resubmitted = client.post(f"/api/applications/{application_id}/submit", headers=customer)
    assert resubmitted.json()["status"] == "REVIEWING"
    registering = client.patch(f"/api/admin/applications/{application_id}/status", headers=admin, json={
        "status": "REGISTERING", "note": "材料审核通过",
    })
    assert registering.status_code == 200
    assert registering.json()["status"] == "REGISTERING"
    assert registering.json()["registration_number"] is None

    completed = client.patch(f"/api/admin/applications/{application_id}/status", headers=admin, json={
        "status": "COMPLETED", "note": "官方下证",
        "registration_number": "DE-WEEE-123456", "certificate_file": "/files/certificate.pdf",
        "service_expiry_date": "2027-09-21",
    })
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["registration_number"] == "DE-WEEE-123456"

    certificate_updated = client.patch(f"/api/admin/applications/{application_id}/status", headers=admin, json={
        "status": "COMPLETED", "note": "证书附件更新",
        "certificate_file": "/files/certificate-v2.pdf",
    })
    assert certificate_updated.status_code == 200
    assert certificate_updated.json()["certificate_file"] == "/files/certificate-v2.pdf"
    assert certificate_updated.json()["registration_number"] == "DE-WEEE-123456"
    assert any(
        recipients == ["demo@eprflow.com"] and "订单更新" in subject and "证书/账单/结果附件已更新" in text
        for recipients, subject, text in sent_emails
    )

    history = client.get(f"/api/applications/{application_id}/status-history", headers=customer)
    assert history.status_code == 200
    assert len(history.json()) == 7
    delivered_order = client.get(f"/api/portal/orders/{order.json()['id']}", headers=customer)
    assert delivered_order.status_code == 200
    assert delivered_order.json()["service_progress"] == "COMPLETED"
    assert delivered_order.json()["service_instances"][0]["registration_number"] == "DE-WEEE-123456"
    assert delivered_order.json()["service_instances"][0]["certificate_file"] == "/files/certificate-v2.pdf"
