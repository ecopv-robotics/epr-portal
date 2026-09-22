from app.core.database import SessionLocal
from app.models import Application, ApplicationStatus


def login(client, account, password):
    response = client.post("/api/auth/login", json={"account": account, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_dashboard_assignment_and_template_configuration(client):
    admin = login(client, "admin@eprflow.com", "Admin123!")
    staff = login(client, "staff@eprflow.com", "Staff123!")
    customer = login(client, "demo@eprflow.com", "Demo123!")

    dashboard = client.get("/api/admin/dashboard", headers=admin)
    assert dashboard.status_code == 200
    assert set(dashboard.json()) == {"total", "submitted", "reviewing", "need_fix", "completed", "my_tasks"}
    assert client.get("/api/admin/dashboard", headers=customer).status_code == 403

    employees = client.get("/api/admin/employees", headers=admin)
    assert employees.status_code == 200
    staff_employee = next(item for item in employees.json() if item["username"] == "staff")
    assert client.get("/api/admin/employees", headers=staff).status_code == 403

    created = client.post("/api/applications", headers=customer, json={"country": "Germany", "service_type": "WEEE"})
    application_id = created.json()["id"]
    review_list = client.get("/api/admin/applications", headers=admin)
    assert review_list.status_code == 200
    assert review_list.json()["total"] == 0
    assert client.get(f"/api/admin/applications/{application_id}", headers=admin).status_code == 404
    assert client.put(f"/api/admin/applications/{application_id}/assignment", headers=admin, json={"employee_id": staff_employee["id"]}).status_code == 404

    templates = client.get("/api/admin/templates", headers=admin)
    assert templates.status_code == 200
    assert client.get("/api/admin/templates", headers=staff).status_code == 403
    template = templates.json()[0]
    updated = client.put(f"/api/admin/templates/{template['id']}", headers=admin, json={
        "fields": template["fields"], "materials": template["materials"],
    })
    assert updated.status_code == 200
    assert updated.json()["id"] == template["id"]


def test_agent_account_and_review_list_agent_name(client):
    admin = login(client, "admin@eprflow.com", "Admin123!")
    created_agent = client.post("/api/admin/agents", headers=admin, json={
        "username": "partner-one", "email": "partner@example.com", "password": "Partner123!",
        "name": "华南代理", "contact_name": "张经理", "contact_phone": "13900000000",
    })
    assert created_agent.status_code == 201
    assert created_agent.json()["customer_type"] == "AGENT"

    agent = login(client, "partner@example.com", "Partner123!")
    application = client.post("/api/applications", headers=agent, json={"country": "Germany", "service_type": "WEEE"})
    assert application.status_code == 201
    assert application.json()["agent_name"] == "华南代理"

    with SessionLocal() as db:
        item = db.get(Application, application.json()["id"])
        item.status = ApplicationStatus.SUBMITTED
        db.commit()

    review_list = client.get("/api/admin/applications?keyword=华南代理", headers=admin)
    assert review_list.status_code == 200
    assert review_list.json()["items"][0]["agent_name"] == "华南代理"

    direct_customers = client.get("/api/admin/direct-customers", headers=admin)
    assert any(item["name"] == "演示直客" for item in direct_customers.json())
