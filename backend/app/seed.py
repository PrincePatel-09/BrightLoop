import logging
from datetime import date

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.customer import Customer
from app.models.catalog import Plan, Product
from app.models.company import Company
from app.models.user import User
from app.models.subscription import Subscription
from app.models.base import AppSetting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

DEMO_USERS = [
    {
        "name": "Brightloop Admin",
        "email": "admin@example.com",
        "role": "admin",
        "company_name": None,
    },
    {
        "name": "Asha Rao",
        "email": "staff@example.com",
        "role": "staff",
        "company_name": None,
    },
    {
        "name": "Rahul Mehta",
        "email": "customer@example.com",
        "role": "customer",
        "company_name": "Mehta Retail",
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        company = db.scalar(select(Company).where(Company.slug.in_(["brightloop-demo", "subnexa-demo"])))
        if not company:
            company = Company(name="Brightloop Software", legal_name="Brightloop Software", slug="brightloop-demo", email="admin@example.com", is_active=True)
            db.add(company)
            db.flush()
        password_hash = hash_password(settings.DEMO_PASSWORD)
        for item in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == item["email"]))
            if not user:
                user = User(email=item["email"])
                db.add(user)
            user.name = item["name"]
            user.password_hash = password_hash
            user.role = item["role"]
            user.is_active = True
            user.company_id = company.id if item["role"] in {"staff", "customer"} else None
            db.flush()
            if item["role"] == "customer":
                customer = db.scalar(select(Customer).where(Customer.user_id == user.id))
                if not customer:
                    db.add(Customer(user_id=user.id, company_id=company.id, company_name=item["company_name"]))
                else:
                    customer.company_id = company.id
                    if not customer.company_name:
                        customer.company_name = item["company_name"]
        setting = db.get(AppSetting, "company_name")
        if setting:
            setting.value = "Brightloop Software"
        else:
            db.add(AppSetting(key="company_name", value="Brightloop Software"))
        db.commit()
        logger.info("Ensured Brightloop demo users. Password for all: %s", settings.DEMO_PASSWORD)

        product = db.scalar(select(Product).where(Product.sku == "SUB-CLOUD-01"))
        if not product:
            product = Product(company_id=company.id, name="Cloud Workspace", sku="SUB-CLOUD-01", product_type="service", sales_price=1999, cost_price=0, notes="Demo recurring software subscription", is_active=True)
            db.add(product)
            db.flush()
        else:
            product.company_id = company.id
            product.is_active = True
        demo_plan = db.scalar(select(Plan).where(Plan.product_id == product.id, Plan.name == "Monthly Workspace"))
        if not demo_plan:
            demo_plan = Plan(product_id=product.id, name="Monthly Workspace", price=1999, billing_interval="month", interval_count=1, features=["Unlimited team members", "Priority email support", "Recurring invoice history", "Secure customer portal"], is_active=True)
            db.add(demo_plan)
            db.commit()
            logger.info("Seeded sample Cloud Workspace plan")
        else:
            demo_plan.is_active = True
            db.commit()

        demo_customer = db.scalar(select(Customer).join(User).where(User.email == "customer@example.com"))
        demo_plan = db.scalar(select(Plan).join(Product).where(
            Product.sku == "SUB-CLOUD-01", Product.company_id == company.id,
            Plan.name == "Monthly Workspace", Plan.is_active.is_(True),
        ))
        if demo_customer and demo_plan and not db.scalar(select(Subscription.id).where(
            Subscription.customer_id == demo_customer.id, Subscription.plan_id == demo_plan.id,
        )):
            today = date.today()
            db.add(Subscription(
                company_id=demo_customer.company_id,
                number=f"SN-DEMO-{demo_customer.id:04d}-{demo_plan.id:04d}",
                customer_id=demo_customer.id,
                plan_id=demo_plan.id,
                product_name=demo_plan.product.name,
                plan_name=demo_plan.name,
                billing_interval=demo_plan.billing_interval,
                interval_count=demo_plan.interval_count,
                quantity=1,
                unit_price=demo_plan.price,
                features=list(demo_plan.features or []),
                status="active",
                start_date=today,
                next_billing_date=today,
            ))
            db.commit()
            logger.info("Seeded demo customer subscription")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
