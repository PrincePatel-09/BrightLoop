from datetime import date, timedelta
from decimal import Decimal
import hashlib
import hmac
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.catalog import Plan, Product
from app.models.company import Company
from app.models.customer import Customer
from app.models.user import User
from app.models.subscription import Subscription


def make_company(db: Session, suffix: str) -> Company:
    company = Company(name=f"Workspace {suffix}", slug=f"workspace-{suffix}", is_active=True)
    db.add(company)
    db.flush()
    return company


def make_company_admin(db: Session, company: Company) -> User:
    user = User(name="Workspace Admin", email=f"owner-{uuid4().hex[:10]}@example.com",
        password_hash=hash_password("DemoPass123!"), role="company_admin", company_id=company.id, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_headers(client, email: str, password: str = "DemoPass123!") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_company_workspace_isolates_products_and_customers(db: Session, client):
    suffix = uuid4().hex[:8]
    company_a = make_company(db, f"a-{suffix}")
    company_b = make_company(db, f"b-{suffix}")
    owner = make_company_admin(db, company_a)
    owner_b = make_company_admin(db, company_b)

    product_a = Product(company_id=company_a.id, name="Own product", sku=f"OWN-{suffix}", product_type="service", sales_price=10)
    product_b = Product(company_id=company_b.id, name="Other product", sku=f"OTHER-{suffix}", product_type="service", sales_price=20)
    user_a = User(name="Own customer", email=f"own-{suffix}@example.com", password_hash=hash_password("DemoPass123!"), role="customer", company_id=company_a.id, is_active=True)
    user_b = User(name="Other customer", email=f"other-{suffix}@example.com", password_hash=hash_password("DemoPass123!"), role="customer", company_id=company_b.id, is_active=True)
    db.add_all([product_a, product_b, user_a, user_b])
    db.flush()
    db.add_all([Customer(user_id=user_a.id, company_id=company_a.id), Customer(user_id=user_b.id, company_id=company_b.id)])
    db.flush()
    customer_a = db.query(Customer).filter(Customer.user_id == user_a.id).one()
    customer_b = db.query(Customer).filter(Customer.user_id == user_b.id).one()
    plan_a = Plan(product_id=product_a.id, name="Own monthly", price=10, billing_interval="month", interval_count=1, is_active=True)
    plan_b = Plan(product_id=product_b.id, name="Other monthly", price=20, billing_interval="month", interval_count=1, is_active=True)
    db.add_all([plan_a, plan_b])
    db.commit()

    headers = login_headers(client, owner.email)
    products = client.get("/api/v1/workspace/products", headers=headers)
    customers = client.get("/api/v1/workspace/customers", headers=headers)
    assert products.status_code == 200
    assert [item["id"] for item in products.json()] == [product_a.id]
    assert customers.status_code == 200
    assert [item["email"] for item in customers.json()] == [user_a.email]

    discount = client.post("/api/v1/workspace/discounts", headers=headers, json={
        "code": "SAVE10", "name": "Ten percent", "discount_type": "percentage", "value": "10",
        "minimum_amount": "0", "starts_at": None, "ends_at": None, "usage_limit": 1,
    })
    assert discount.status_code == 201, discount.text
    assert [row["code"] for row in client.get("/api/v1/workspace/discounts", headers=headers).json()] == ["SAVE10"]
    customer_headers_a = login_headers(client, user_a.email)
    customer_request = client.post("/api/v1/my/subscription-requests", headers=customer_headers_a, json={
        "plan_id": plan_a.id, "quantity": 1, "discount_code": "SAVE10",
    })
    assert customer_request.status_code == 201, customer_request.text
    headers_b = login_headers(client, owner_b.email)
    assert client.get("/api/v1/workspace/discounts", headers=headers_b).json() == []
    template = client.post("/api/v1/workspace/quotation-templates", headers=headers, json={
        "name": "Standard monthly", "plan_id": plan_a.id, "quantity": 2, "valid_days": 21,
        "notes": "Standard service terms", "discount_code": "SAVE10",
    })
    assert template.status_code == 201, template.text
    assert template.json()["plan_name"] == plan_a.name and template.json()["quantity"] == 2
    assert len(client.get("/api/v1/workspace/quotation-templates", headers=headers).json()) == 1
    assert client.get("/api/v1/workspace/quotation-templates", headers=headers_b).json() == []
    assert client.delete(f"/api/v1/workspace/quotation-templates/{template.json()['id']}", headers=headers_b).status_code == 404
    add_on_plan = Plan(product_id=product_a.id, name="Extra storage", price=5, billing_interval="month", interval_count=1, is_active=True)
    db.add(add_on_plan); db.commit()
    customer_headers_b = login_headers(client, user_b.email)
    customer_request_b = client.post("/api/v1/my/subscription-requests", headers=customer_headers_b, json={
        "plan_id": plan_b.id, "quantity": 1, "discount_code": "SAVE10",
    })
    assert customer_request_b.status_code == 422 and customer_request_b.json()["code"] == "invalid_discount_code"
    quote_a = client.post("/api/v1/workspace/quotations", headers=headers, json={
        "customer_id": customer_a.id, "plan_id": plan_a.id,
        "valid_until": (date.today() + timedelta(days=5)).isoformat(), "discount_code": "save10",
        "line_items": [{"plan_id": add_on_plan.id, "quantity": 2}],
    })
    assert quote_a.status_code == 201, quote_a.text
    assert len(quote_a.json()["line_items"]) == 2
    assert Decimal(str(quote_a.json()["discount_amount"])) == Decimal("2.00")
    quote_a_id = quote_a.json()["id"]
    repriced_quote = client.patch(f"/api/v1/workspace/quotations/{quote_a_id}", headers=headers,
        json={"quantity": 2})
    assert repriced_quote.status_code == 200, repriced_quote.text
    assert Decimal(str(repriced_quote.json()["discount_amount"])) == Decimal("3.00")
    assert client.patch(f"/api/v1/workspace/quotations/{quote_a_id}", headers=headers, json={"status": "sent"}).status_code == 200
    assert client.patch(f"/api/v1/workspace/quotations/{quote_a_id}", headers=headers, json={"status": "accepted"}).status_code == 200
    converted = client.post(f"/api/v1/workspace/quotations/{quote_a_id}/convert", headers=headers)
    assert converted.status_code == 201, converted.text
    assert len(converted.json()["line_items"]) == 2
    assert client.get("/api/v1/workspace/discounts", headers=headers).json()[0]["times_used"] == 1
    exhausted_quote = client.post("/api/v1/workspace/quotations", headers=headers, json={
        "customer_id": customer_a.id, "plan_id": plan_a.id,
        "valid_until": (date.today() + timedelta(days=5)).isoformat(), "discount_code": "SAVE10",
    })
    assert exhausted_quote.status_code == 409 and exhausted_quote.json()["code"] == "discount_limit_reached"
    quote_b = client.post("/api/v1/workspace/quotations", headers=headers_b, json={
        "customer_id": customer_b.id, "plan_id": plan_b.id,
        "valid_until": (date.today() + timedelta(days=5)).isoformat(), "discount_code": "SAVE10",
    })
    assert quote_b.status_code == 422 and quote_b.json()["code"] == "invalid_discount_code"
    assert client.patch(f"/api/v1/workspace/discounts/{discount.json()['id']}", headers=headers_b,
        json={"is_active": False}).status_code == 404

    cross_tenant_edit = client.patch(
        f"/api/v1/workspace/products/{product_b.id}",
        headers=headers,
        json={"name": "Stolen update"},
    )
    assert cross_tenant_edit.status_code == 404


def test_company_workspace_quote_billing_and_payment_flow(db: Session, client, monkeypatch):
    suffix = uuid4().hex[:8]
    company = make_company(db, f"billing-{suffix}")
    owner = make_company_admin(db, company)
    customer_user = User(name="Billing customer", email=f"buyer-{suffix}@example.com",
        password_hash=hash_password("DemoPass123!"), role="customer", company_id=company.id, is_active=True)
    db.add(customer_user); db.flush()
    customer = Customer(user_id=customer_user.id, company_id=company.id, company_name="Buyer Co", state_code="GJ")
    product = Product(company_id=company.id, name="Hosted service", sku=f"HOST-{suffix}", product_type="service", sales_price=120)
    db.add_all([customer, product]); db.flush()
    plan = Plan(product_id=product.id, name="Monthly", price=120, billing_interval="month", interval_count=1, features=["Support"], is_active=True)
    upgrade_plan = Plan(product_id=product.id, name="Premium monthly", price=240, billing_interval="month", interval_count=1, features=["Priority support"], is_active=True)
    db.add_all([plan, upgrade_plan]); db.commit()
    db.refresh(customer)

    headers = login_headers(client, owner.email)
    setting = client.put("/api/v1/workspace/settings", headers=headers, json={
        "name": "Billing Workspace", "tax_id": "GSTIN-TEST-001", "state_name": "Maharashtra", "state_code": "MH",
        "gst_rate_percent": "18.00", "currency_code": "USD", "invoice_prefix": "BW", "payment_terms_days": 5,
    })
    assert setting.status_code == 200, setting.text

    quote = client.post("/api/v1/workspace/quotations", headers=headers, json={
        "customer_id": customer.id, "plan_id": plan.id, "valid_until": (date.today() + timedelta(days=10)).isoformat(),
        "line_items": [{"plan_id": upgrade_plan.id, "quantity": 1}],
    })
    assert quote.status_code == 201, quote.text
    quote_id = quote.json()["id"]
    edited_quote = client.patch(f"/api/v1/workspace/quotations/{quote_id}", headers=headers,
        json={"notes": "Customer requested standard terms", "valid_until": (date.today() + timedelta(days=12)).isoformat()})
    assert edited_quote.status_code == 200 and edited_quote.json()["notes"] == "Customer requested standard terms"
    assert client.patch(f"/api/v1/workspace/quotations/{quote_id}", headers=headers, json={"status": "sent"}).status_code == 200
    assert client.patch(f"/api/v1/workspace/quotations/{quote_id}", headers=headers, json={"quantity": 3}).status_code == 409
    accepted = client.patch(f"/api/v1/workspace/quotations/{quote_id}", headers=headers, json={"status": "accepted"})
    assert accepted.status_code == 200, accepted.text
    converted = client.post(f"/api/v1/workspace/quotations/{quote_id}/convert", headers=headers)
    assert converted.status_code == 201, converted.text

    billing = client.post("/api/v1/workspace/billing/run", headers=headers, json={"as_of": date.today().isoformat()})
    assert billing.status_code == 200, billing.text
    assert billing.json()["invoices_created"] == 1
    invoices = client.get("/api/v1/workspace/invoices", headers=headers)
    assert invoices.status_code == 200 and len(invoices.json()) == 1
    invoice = invoices.json()[0]
    assert invoice["currency_code"] == "USD"
    fiscal_start = date.today().year if date.today().month >= 4 else date.today().year - 1
    assert invoice["number"] == f"BW/{fiscal_start}-{(fiscal_start + 1) % 100:02d}/0001"
    assert Decimal(str(invoice["tax_amount"])) == Decimal("64.80")
    assert Decimal(str(invoice["subtotal"])) == Decimal("360.00") and len(invoice["line_items"]) == 2
    assert invoice["tax_details"][0]["name"] == "IGST"
    assert invoice["seller_gstin"] == "GSTIN-TEST-001"
    assert invoice["seller_state_code"] == "MH" and invoice["customer_state_code"] == "GJ"
    assert invoice["customer_name"] == customer_user.name

    emailed = []
    monkeypatch.setattr("app.api.v1.workspace.send_invoice_notice",
        lambda email, number, url: emailed.append((email, number, url)) or True)
    email_response = client.post(f"/api/v1/workspace/invoices/{invoice['id']}/email", headers=headers)
    assert email_response.status_code == 202, email_response.text
    assert email_response.json() == {"delivered": True, "recipient": customer_user.email}
    assert emailed and emailed[0][0:2] == (customer_user.email, invoice["number"])
    assert client.post(f"/api/v1/workspace/invoices/{invoice['id']}/email",
        headers=login_headers(client, make_company_admin(db, make_company(db, f"other-{suffix}")).email)).status_code == 404

    credit = client.post(f"/api/v1/workspace/invoices/{invoice['id']}/credit-notes", headers=headers,
        json={"amount": "10.00", "reason": "Service adjustment"})
    assert credit.status_code == 201, credit.text
    credited = next(row for row in client.get("/api/v1/workspace/invoices", headers=headers).json() if row["id"] == invoice["id"])
    assert Decimal(str(credited["credited_amount"])) == Decimal("10.00")
    assert Decimal(str(credited["balance_due"])) == Decimal("414.80")
    voided = client.patch(f"/api/v1/workspace/credit-notes/{credit.json()['id']}", headers=headers, json={"status": "void"})
    assert voided.status_code == 200 and voided.json()["status"] == "void"

    subscription = db.get(Subscription, converted.json()["id"])
    subscription.next_billing_date = date.today() + timedelta(days=1)
    db.commit()
    second_run = client.post("/api/v1/workspace/billing/run", headers=headers,
        json={"as_of": (date.today() + timedelta(days=1)).isoformat()})
    assert second_run.status_code == 200 and second_run.json()["invoices_created"] == 1
    sequential = client.get("/api/v1/workspace/invoices", headers=headers).json()
    assert any(row["number"] == f"BW/{fiscal_start}-{(fiscal_start + 1) % 100:02d}/0002" for row in sequential)

    payment = client.post(f"/api/v1/workspace/invoices/{invoice['id']}/payments", headers=headers,
        json={"amount": "25.00", "method": "bank_transfer"})
    assert payment.status_code == 201, payment.text
    refund = client.post(f"/api/v1/workspace/payments/{payment.json()['id']}/refunds", headers=headers,
        json={"amount": "5.00", "reason": "Duplicate payment", "reference": "bank-refund-1"})
    assert refund.status_code == 201, refund.text
    assert Decimal(str(refund.json()["amount"])) == Decimal("5.00")
    refreshed = next(row for row in client.get("/api/v1/workspace/invoices", headers=headers).json() if row["id"] == invoice["id"])
    assert Decimal(str(refreshed["amount_paid"])) == Decimal("20.00")
    assert Decimal(str(refreshed["balance_due"])) == Decimal("404.80")

    customer_headers = login_headers(client, customer_user.email)
    catalog = client.get("/api/v1/my/catalog", headers=customer_headers)
    assert catalog.status_code == 200, catalog.text
    assert catalog.json()["products"][0]["plans"]
    subscription_id = converted.json()["id"]

    pause_request = client.post(f"/api/v1/my/subscriptions/{subscription_id}/requests", headers=customer_headers,
        json={"request_type": "pause", "notes": "Taking a short break"})
    assert pause_request.status_code == 201, pause_request.text
    requests = client.get("/api/v1/workspace/requests", headers=headers)
    assert requests.status_code == 200 and requests.json()[0]["customer_email"] == customer_user.email
    request_id = requests.json()[0]["id"]
    approved = client.patch(f"/api/v1/workspace/requests/{request_id}", headers=headers, json={"status": "approved"})
    assert approved.status_code == 200, approved.text
    assert client.get("/api/v1/my/subscriptions", headers=customer_headers).json()[0]["status"] == "paused"

    resume_request = client.post(f"/api/v1/my/subscriptions/{subscription_id}/requests", headers=customer_headers, json={"request_type": "resume"})
    assert resume_request.status_code == 201, resume_request.text
    resume_id = client.get("/api/v1/workspace/requests", headers=headers).json()[0]["id"]
    assert client.patch(f"/api/v1/workspace/requests/{resume_id}", headers=headers, json={"status": "approved"}).status_code == 200

    upgrade = client.post(f"/api/v1/my/subscriptions/{subscription_id}/requests", headers=customer_headers,
        json={"request_type": "upgrade", "requested_plan_id": upgrade_plan.id})
    assert upgrade.status_code == 201, upgrade.text
    approved_upgrade = client.patch(f"/api/v1/workspace/requests/{upgrade.json()['id']}", headers=headers,
        json={"status": "approved"})
    assert approved_upgrade.status_code == 200, approved_upgrade.text
    updated_subscription = client.get("/api/v1/my/subscriptions", headers=customer_headers).json()[0]
    assert updated_subscription["plan_id"] == upgrade_plan.id and len(updated_subscription["line_items"]) == 1

    from app.api.v1 import portal
    from app.core.config import settings

    settings.RAZORPAY_KEY_ID = "rzp_test_workspace"
    settings.RAZORPAY_KEY_SECRET = "test-secret"

    class GatewayResponse:
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): pass
        def json(self): return self.payload

    monkeypatch.setattr(portal.httpx, "post", lambda *args, **kwargs: GatewayResponse({
        "id": "order_workspace", "amount": 40480, "currency": "USD",
    }))
    payment_order = client.post(f"/api/v1/my/invoices/{invoice['id']}/payment-orders", headers=customer_headers)
    assert payment_order.status_code == 200, payment_order.text
    assert payment_order.json()["amount"] == 40480
    payment_id = "pay_workspace"
    signature = hmac.new(b"test-secret", f"order_workspace|{payment_id}".encode(), hashlib.sha256).hexdigest()
    monkeypatch.setattr(portal.httpx, "get", lambda *args, **kwargs: GatewayResponse({
        "id": payment_id, "order_id": "order_workspace", "amount": 40480,
        "currency": "USD", "status": "captured", "captured": True, "method": "card",
    }))
    verified = client.post(f"/api/v1/my/invoices/{invoice['id']}/verify-payment", headers=customer_headers,
        json={"order_id": "order_workspace", "payment_id": payment_id, "signature": signature})
    assert verified.status_code == 200, verified.text
    assert Decimal(str(verified.json()["amount"])) == Decimal("404.80")
    paid_invoice = next(row for row in client.get("/api/v1/my/invoices", headers=customer_headers).json() if row["id"] == invoice["id"])
    assert paid_invoice["status"] == "paid"


def test_platform_admin_can_provision_company_workspace(admin_user, client):
    admin_headers = login_headers(client, admin_user.email)
    suffix = uuid4().hex[:8]
    created = client.post("/api/v1/companies", headers=admin_headers, json={"name": "Provisioned Workspace", "slug": f"provisioned-{suffix}"})
    assert created.status_code == 201, created.text
    company_id = created.json()["id"]
    provisioned = client.post(f"/api/v1/companies/{company_id}/admins", headers=admin_headers, json={
        "name": "Company Owner", "email": f"company-owner-{suffix}@example.com", "password": "Workspace123",
    })
    assert provisioned.status_code == 201, provisioned.text
    assert provisioned.json()["role"] == "company_admin"
    assert provisioned.json()["company_id"] == company_id
    admins = client.get(f"/api/v1/companies/{company_id}/admins", headers=admin_headers)
    assert admins.status_code == 200 and len(admins.json()) == 1
    disabled = client.patch(f"/api/v1/companies/{company_id}/admins/{provisioned.json()['id']}", headers=admin_headers,
        json={"is_active": False})
    assert disabled.status_code == 200 and disabled.json()["is_active"] is False
    reenabled = client.patch(f"/api/v1/companies/{company_id}/admins/{provisioned.json()['id']}", headers=admin_headers,
        json={"is_active": True})
    assert reenabled.status_code == 200 and reenabled.json()["is_active"] is True
    company_headers = login_headers(client, provisioned.json()["email"], "Workspace123")
    overview = client.get("/api/v1/workspace/overview", headers=company_headers)
    assert overview.status_code == 200, overview.text
    assert overview.json()["customers"] == 0
