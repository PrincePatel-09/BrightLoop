from uuid import uuid4

from tests.conftest import auth_header
from app.models.catalog import Plan, Product
from app.models.company import Company


def test_customer_can_buy_plan_directly(client, db, customer_user):
    suffix = uuid4().hex[:10]
    product = Product(
        company_id=customer_user.company_id,
        name="Direct purchase service",
        sku=f"DIRECT-{suffix}",
        product_type="service",
        sales_price=25,
        cost_price=0,
        is_active=True,
    )
    db.add(product)
    db.flush()
    plan = Plan(product_id=product.id, name="Monthly", price=25, billing_interval="month", interval_count=1, is_active=True)
    db.add(plan)
    db.commit()

    response = client.post(
        "/api/v1/my/subscriptions",
        headers=auth_header(client, customer_user.email),
        json={"plan_id": plan.id, "quantity": 1},
    )

    assert response.status_code == 201, response.text
    subscription = response.json()
    assert subscription["status"] == "active"
    assert subscription["quotation_id"] is None
    assert subscription["plan_id"] == plan.id

    listed = client.get("/api/v1/my/subscriptions", headers=auth_header(client, customer_user.email))
    assert listed.status_code == 200
    assert any(row["id"] == subscription["id"] for row in listed.json())


def test_customer_cannot_buy_another_company_plan(client, db, customer_user):
    suffix = uuid4().hex[:10]
    company = Company(name="Other workspace", slug=f"other-{suffix}", is_active=True)
    db.add(company)
    db.flush()
    product = Product(
        company_id=company.id,
        name="Private service",
        sku=f"PRIVATE-{suffix}",
        product_type="service",
        sales_price=30,
        cost_price=0,
        is_active=True,
    )
    db.add(product)
    db.flush()
    plan = Plan(product_id=product.id, name="Private monthly", price=30, billing_interval="month", interval_count=1, is_active=True)
    db.add(plan)
    db.commit()

    response = client.post(
        "/api/v1/my/subscriptions",
        headers=auth_header(client, customer_user.email),
        json={"plan_id": plan.id, "quantity": 1},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "plan_not_found"
