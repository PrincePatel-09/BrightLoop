import os
from uuid import uuid4
from sqlalchemy import select

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.customer import Customer
from app.models.company import Company
from app.models.user import User


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _ensure_user(db: Session, name: str, email: str, role: str, password: str = "DemoPass123!") -> User:
    company = db.scalar(select(Company).where(Company.slug == "brightloop-demo"))
    if not company:
        company = Company(name="Test Company", slug="brightloop-demo", is_active=True)
        db.add(company)
        db.flush()
    user = User(name=name, email=email, password_hash=hash_password(password), role=role, is_active=True,
        company_id=company.id if role == "customer" else None)
    db.add(user)
    db.flush()
    if role == "customer":
        db.add(Customer(user_id=user.id, company_id=company.id, company_name="Test Co"))
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> User:
    return _ensure_user(db, "Admin", f"admin.{uuid4().hex[:10]}@example.com", "admin")


@pytest.fixture
def staff_user(db: Session) -> User:
    return _ensure_user(db, "Staff", f"staff.{uuid4().hex[:10]}@example.com", "staff")


@pytest.fixture
def customer_user(db: Session) -> User:
    return _ensure_user(db, "Customer", f"customer.{uuid4().hex[:10]}@example.com", "customer")


def auth_header(client: TestClient, email: str, password: str = "DemoPass123!") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
