from app.models import VerificationCode


def test_register_with_email_verification_code(client, monkeypatch):
    delivered = []
    monkeypatch.setattr("app.modules.user.router.secrets.randbelow", lambda _: 123456)
    monkeypatch.setattr(
        "app.modules.user.router.send_verification_code",
        lambda channel, target, code: delivered.append((channel, target, code)) or True,
    )

    sent = client.post("/api/auth/verification-codes", json={"account": " New.User@Example.com "})
    assert sent.status_code == 200
    assert sent.json()["debug_code"] is None
    assert delivered == [("email", "new.user@example.com", "123456")]

    registered = client.post("/api/auth/register", json={
        "account": "NEW.USER@example.com",
        "verification_code": "123456",
        "password": "StrongPass123!",
    })
    assert registered.status_code == 201
    assert registered.json()["user"]["email"] == "new.user@example.com"
    assert registered.json()["user"]["phone"] is None
    assert registered.json()["access_token"]

    login = client.post("/api/auth/login", json={"account": "new.user@example.com", "password": "StrongPass123!"})
    assert login.status_code == 200


def test_register_with_phone_and_reject_code_reuse(client, monkeypatch):
    monkeypatch.setattr("app.modules.user.router.secrets.randbelow", lambda _: 654321)
    monkeypatch.setattr("app.modules.user.router.send_verification_code", lambda *_: True)

    assert client.post("/api/auth/verification-codes", json={"account": "+86 138-0000-1234"}).status_code == 200
    registered = client.post("/api/auth/register", json={
        "account": "+8613800001234", "verification_code": "654321", "password": "PhonePass123!",
    })
    assert registered.status_code == 201
    assert registered.json()["user"]["phone"] == "+8613800001234"

    reused = client.post("/api/auth/register", json={
        "account": "+8613800001234", "verification_code": "654321", "password": "PhonePass123!",
    })
    assert reused.status_code == 409


def test_wrong_code_is_rejected_and_attempt_is_counted(client, monkeypatch):
    monkeypatch.setattr("app.modules.user.router.secrets.randbelow", lambda _: 111111)
    monkeypatch.setattr("app.modules.user.router.send_verification_code", lambda *_: True)
    client.post("/api/auth/verification-codes", json={"account": "wrong@example.com"})

    response = client.post("/api/auth/register", json={
        "account": "wrong@example.com", "verification_code": "222222", "password": "StrongPass123!",
    })
    assert response.status_code == 400
    assert response.json()["detail"] == "验证码错误"

    from app.core.database import SessionLocal
    with SessionLocal() as db:
        record = db.query(VerificationCode).filter_by(target="wrong@example.com").one()
        assert record.attempts == 1


def test_verification_delivery_failure_does_not_persist_code(client, monkeypatch):
    monkeypatch.setattr("app.modules.user.router.send_verification_code", lambda *_: False)
    response = client.post("/api/auth/verification-codes", json={"account": "unavailable@example.com"})
    assert response.status_code == 503

    from app.core.database import SessionLocal
    with SessionLocal() as db:
        assert db.query(VerificationCode).count() == 0
