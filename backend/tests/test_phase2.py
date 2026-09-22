def login(client):
    response = client.post("/api/auth/login", json={"account": "demo@eprflow.com", "password": "Demo123!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_application(client, headers):
    response = client.post("/api/applications", json={"country": "Germany", "service_type": "WEEE"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def test_europe_catalog_and_phase2_form_flow(client):
    catalog = client.get("/api/catalog/countries")
    assert catalog.status_code == 200
    assert len(catalog.json()) == 50
    assert all({service["value"] for service in country["services"]} == {"WEEE", "Battery", "Packaging", "SUP"} for country in catalog.json())

    headers = login(client)
    application_id = create_application(client, headers)

    form = client.get(f"/api/applications/{application_id}/form", headers=headers)
    assert form.status_code == 200
    germany_weee_fields = form.json()["template"]["fields"]
    assert [field["field_name"] for field in germany_weee_fields] == [
        "category", "name", "brand_logo", "max_dimension_cm", "estimated_sales",
    ]
    category_field = germany_weee_fields[0]
    assert category_field["required"] is True
    assert category_field["options"] == [
        "热交换设备", "屏幕设备", "气体放电灯", "非气体放电灯",
        "大型设备，单边尺寸大于50cm", "小型设备，单边尺寸小于50cm",
        "小型信息和电信设备", "大型光伏，单边尺寸大于50cm",
        "小型光伏，单边尺寸小于50cm",
    ]
    assert germany_weee_fields[-1]["required"] is False
    requirement_id = form.json()["template"]["materials"][0]["id"]
    weee_materials = {item["material_name"]: item for item in form.json()["template"]["materials"]}
    assert weee_materials["授权书"]["required"] is True

    company = client.put(f"/api/applications/{application_id}/company", headers=headers, json={
        "company_name": "ABC LIMITED", "registration_region": "EU", "company_type": "Private Limited Company",
        "register_number": "REG-001", "established_date": "2020-01-02", "vat_number": "DE123456789",
        "register_address": "Test Address", "license_file": "/files/license.pdf",
    })
    assert company.status_code == 200
    legal = client.put(f"/api/applications/{application_id}/legal-person", headers=headers, json={
        "name_cn": "张三", "name_en": "San Zhang", "certificate_type": "PASSPORT", "gender": "MALE",
        "contact_email": "contact@example.com", "contact_phone": "+49 123456", "front_file": "/files/passport.jpg",
        "signature_file": "/files/signature.png",
    })
    assert legal.status_code == 200
    assert legal.json()["legal_person"]["name_en"] == "San Zhang"

    store = client.put(f"/api/applications/{application_id}/store", headers=headers, json={
        "platform": "Amazon", "store_url": "https://example.com", "company_name_en": "ABC LIMITED",
        "register_city_en": "Berlin", "postal_code": "10115", "register_address_en": "Example Str. 1",
        "screenshot_file": "/files/store.png",
    })
    assert store.status_code == 200
    products = client.put(f"/api/applications/{application_id}/products", headers=headers, json=[{
        "product_data": {
            "category": "小型信息和电信设备", "name": "Charger", "brand_logo": "ACME",
            "max_dimension_cm": 20, "estimated_sales": 10000,
        }
    }])
    assert products.status_code == 200

    invalid_category = client.put(f"/api/applications/{application_id}/products", headers=headers, json=[{
        "product_data": {"category": "不存在的类别", "name": "Charger"}
    }])
    assert invalid_category.status_code == 422

    uploaded = client.post(
        "/api/material/upload", headers=headers,
        data={"application_id": application_id, "requirement_id": requirement_id},
        files={"file": ("license.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["original_name"] == "license.pdf"

    history = client.get("/api/company/history", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["company_name"] == "ABC LIMITED"

    saved_form = client.get(f"/api/applications/{application_id}/form", headers=headers).json()
    assert saved_form["company"]["registration_region"] == "EU"
    assert saved_form["company"]["vat_number"] == "DE123456789"
    assert saved_form["company"]["legal_person"]["contact_email"] == "contact@example.com"
    assert saved_form["store"]["register_city_en"] == "Berlin"
    assert len(saved_form["products"]) == 1
    material_files = {item["requirement_id"]: item for item in saved_form["material_files"]}
    assert len(material_files) == 2
    assert material_files[requirement_id]["original_name"] == "license.pdf"
    assert material_files[requirement_id]["auto_synced"] is False
    synced = next(item for item in material_files.values() if item["auto_synced"])
    assert synced["file_url"] == "/files/passport.jpg"


def test_upload_rules_distinguish_store_screenshot(client):
    headers = login(client)
    rejected = client.post(
        "/api/files/upload", headers=headers, data={"purpose": "store_screenshot"},
        files={"file": ("store.pdf", b"%PDF-test", "application/pdf")},
    )
    assert rejected.status_code == 422
    accepted = client.post(
        "/api/files/upload", headers=headers, data={"purpose": "store_screenshot"},
        files={"file": ("store.png", b"png-test", "image/png")},
    )
    assert accepted.status_code == 200


def test_saved_company_license_is_auto_synced_to_materials(client, monkeypatch):
    headers = login(client)
    response = client.post(
        "/api/applications",
        json={"country": "Germany", "service_type": "Battery"},
        headers=headers,
    )
    assert response.status_code == 201
    application_id = response.json()["id"]

    saved = client.put(f"/api/applications/{application_id}/company", headers=headers, json={
        "company_name": "测试科技有限公司",
        "registration_region": "MAINLAND_CHINA",
        "company_type": "有限责任公司",
        "register_number": "91310000TEST000001",
        "established_date": "2020-01-02",
        "register_address": "上海市测试路 1 号",
        "license_file": "/files/company-license.png",
        "license_translation_file": "/files/company-license-translation.pdf",
        "credit_report_file": "/files/company-credit-report.pdf",
    })
    assert saved.status_code == 200
    assert saved.json()["license_translation_file"] == "/files/company-license-translation.pdf"

    monkeypatch.setattr(
        "app.modules.company.router.generate_translation",
        lambda _: ("/files/generated-license-translation.pdf", 1024),
    )
    generated = client.post(
        f"/api/applications/{application_id}/company/license-translation", headers=headers,
    )
    assert generated.status_code == 200
    assert generated.json()["file_url"] == "/files/generated-license-translation.pdf"

    form = client.get(f"/api/applications/{application_id}/form", headers=headers)
    assert form.status_code == 200
    payload = form.json()
    assert payload["company"]["license_translation_file"] == "/files/generated-license-translation.pdf"
    license_requirement = next(
        item for item in payload["template"]["materials"] if item["material_name"] == "营业执照"
    )
    synced_license = next(
        item for item in payload["material_files"] if item["requirement_id"] == license_requirement["id"]
    )

    assert synced_license["file_url"] == "/files/company-license.png"
    assert synced_license["auto_synced"] is True
