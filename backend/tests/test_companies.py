from tests.conftest import auth_header
from app.models.company import Company
from uuid import uuid4


def test_public_directory_lists_active_companies_without_auth(client, db):
    suffix = uuid4().hex[:10]
    active = Company(name="Public Workspace", slug=f"public-{suffix}", is_active=True)
    inactive = Company(name="Hidden Workspace", slug=f"hidden-{suffix}", is_active=False)
    db.add_all([active, inactive])
    db.commit()

    response = client.get("/api/v1/companies/directory")

    assert response.status_code == 200
    rows = response.json()
    assert any(row["slug"] == active.slug for row in rows)
    assert all(row["slug"] != inactive.slug for row in rows)


def test_admin_can_manage_companies(client, admin_user):
    headers = auth_header(client, admin_user.email)
    created = client.post(
        "/api/v1/companies",
        json={"name": "Northwind", "slug": "northwind", "email": "ops@northwind.example"},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["slug"] == "northwind"
    assert created.json()["user_count"] == 0

    listed = client.get("/api/v1/companies", headers=headers)
    assert listed.status_code == 200
    assert any(company["slug"] == "northwind" for company in listed.json())


def test_staff_cannot_manage_companies(client, staff_user):
    headers = auth_header(client, staff_user.email)
    response = client.get("/api/v1/companies", headers=headers)
    assert response.status_code == 403
