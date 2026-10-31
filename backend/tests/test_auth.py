from tests.conftest import auth_header


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_customer_and_me(client):
    from uuid import uuid4

    email = f"new.{uuid4().hex[:10]}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "New Customer",
            "email": email,
            "password": "Secret123",
            "confirm_password": "Secret123",
            "company_name": "Acme",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "customer"
    assert body["email"] == email
    assert body["customer_id"] is not None


def test_duplicate_email(client):
    from uuid import uuid4

    payload = {
        "name": "Dup",
        "email": f"dup.{uuid4().hex[:10]}@example.com",
        "password": "Secret123",
        "confirm_password": "Secret123",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    again = client.post("/api/v1/auth/register", json=payload)
    assert again.status_code == 409


def test_invalid_login(client, customer_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": customer_user.email, "password": "wrong-pass-1"},
    )
    assert response.status_code == 401


def test_password_mismatch(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Bad",
            "email": "bad@example.com",
            "password": "Secret123",
            "confirm_password": "Secret124",
        },
    )
    assert response.status_code == 422


def test_staff_cannot_create_staff(client, staff_user):
    headers = auth_header(client, staff_user.email)
    response = client.post(
        "/api/v1/staff",
        json={"name": "Intruder", "email": "intruder@example.com", "password": "Secret123"},
        headers=headers,
    )
    assert response.status_code == 403


def test_customer_cannot_create_staff(client, customer_user):
    headers = auth_header(client, customer_user.email)
    response = client.post(
        "/api/v1/staff",
        json={"name": "Intruder", "email": "intruder2@example.com", "password": "Secret123"},
        headers=headers,
    )
    assert response.status_code == 403


def test_admin_can_create_and_list_staff(client, admin_user):
    headers = auth_header(client, admin_user.email)
    created = client.post(
        "/api/v1/staff",
        json={"name": "Priya Shah", "email": "priya.staff@example.com", "password": "Secret123"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["role"] == "staff"
    listed = client.get("/api/v1/staff", headers=headers)
    assert listed.status_code == 200
    emails = [row["email"] for row in listed.json()]
    assert "priya.staff@example.com" in emails


def test_unauthenticated_me(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_and_logout(client, customer_user):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": customer_user.email, "password": "DemoPass123!"},
    )
    refresh = login.json()["refresh_token"]
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401
    new_refresh = rotated.json()["refresh_token"]
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout.status_code == 200
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401


def test_forgot_password_generic_message(client, db, customer_user):
    response = client.post("/api/v1/auth/forgot-password", json={"email": customer_user.email})
    assert response.status_code == 200
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert unknown.status_code == 200
    assert response.json()["message"] == unknown.json()["message"]

    from datetime import datetime, timedelta, timezone
    import secrets

    from app.models.token import PasswordResetToken
    from app.services.auth_service import hash_token

    raw = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            user_id=customer_user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
    )
    db.commit()
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "password": "NewPass123", "confirm_password": "NewPass123"},
    )
    assert reset.status_code == 200
    old = client.post(
        "/api/v1/auth/login",
        json={"email": customer_user.email, "password": "DemoPass123!"},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/v1/auth/login",
        json={"email": customer_user.email, "password": "NewPass123"},
    )
    assert new.status_code == 200
