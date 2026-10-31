from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import DbSession, RequireAdmin, RequireStaff
from app.core.exceptions import AppError
from app.models.catalog import Plan, Product, ProductVariant
from app.models.company import Company
from app.schemas.catalog import PlanCreate, PlanPublic, PlanUpdate, ProductCreate, ProductPublic, ProductUpdate, ProductVariantCreate, ProductVariantPublic, ProductVariantUpdate
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("/products/{product_id}/variants", response_model=list[ProductVariantPublic])
def list_variants(product_id: int, _staff: RequireStaff, db: DbSession, include_inactive: bool = False):
    query = select(ProductVariant).where(ProductVariant.product_id == product_id).order_by(ProductVariant.attribute, ProductVariant.name)
    if not include_inactive:
        query = query.where(ProductVariant.is_active.is_(True))
    return db.scalars(query).all()


@router.post("/products/{product_id}/variants", response_model=ProductVariantPublic, status_code=201)
def create_variant(product_id: int, payload: ProductVariantCreate, admin: RequireAdmin, db: DbSession):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise AppError("Active product not found", status_code=404, code="not_found")
    variant = ProductVariant(product_id=product_id, **payload.model_dump())
    db.add(variant)
    db.flush()
    record_audit(db, admin.id, "catalog.variant_created", "product_variant", variant.id, {"product_id": product_id})
    db.commit()
    db.refresh(variant)
    return variant


@router.patch("/variants/{variant_id}", response_model=ProductVariantPublic)
def update_variant(variant_id: int, payload: ProductVariantUpdate, admin: RequireAdmin, db: DbSession):
    variant = db.get(ProductVariant, variant_id)
    if not variant:
        raise AppError("Variant not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, key, value)
    record_audit(db, admin.id, "catalog.variant_updated", "product_variant", variant.id)
    db.commit()
    db.refresh(variant)
    return variant


@router.get("/products", response_model=list[ProductPublic])
def list_products(_staff: RequireStaff, db: DbSession, include_inactive: bool = Query(default=False)):
    query = select(Product).order_by(Product.name)
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))
    return db.scalars(query).unique().all()


@router.post("/products", response_model=ProductPublic, status_code=201)
def create_product(payload: ProductCreate, admin: RequireAdmin, db: DbSession):
    if db.scalar(select(Product.id).where(Product.sku == payload.sku)):
        raise AppError("A product with this SKU already exists", status_code=409, code="sku_taken")
    values = payload.model_dump()
    company_id = values.pop("company_id", None)
    if company_id is None:
        company_id = db.scalar(select(Company.id).where(Company.slug == "brightloop-demo", Company.is_active.is_(True)))
    if company_id is None or not db.get(Company, company_id):
        raise AppError("Active company workspace not found", status_code=422, code="company_not_found")
    product = Product(company_id=company_id, **values)
    db.add(product)
    db.commit()
    db.refresh(product)
    record_audit(db, admin.id, "catalog.product_created", "product", product.id, {"sku": product.sku})
    db.commit()
    return product


@router.patch("/products/{product_id}", response_model=ProductPublic)
def update_product(product_id: int, payload: ProductUpdate, admin: RequireAdmin, db: DbSession):
    product = db.get(Product, product_id)
    if not product:
        raise AppError("Product not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    record_audit(db, admin.id, "catalog.product_updated", "product", product.id)
    db.commit()
    db.refresh(product)
    return product


@router.post("/products/{product_id}/plans", response_model=PlanPublic, status_code=201)
def create_plan(product_id: int, payload: PlanCreate, admin: RequireAdmin, db: DbSession):
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise AppError("Active product not found", status_code=404, code="not_found")
    plan = Plan(product_id=product_id, **payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    record_audit(db, admin.id, "catalog.plan_created", "plan", plan.id, {"product_id": product_id})
    db.commit()
    return plan


@router.get("/plans", response_model=list[PlanPublic])
def list_plans(_staff: RequireStaff, db: DbSession, product_id: int | None = None, include_inactive: bool = False):
    query = select(Plan).join(Product).where(Product.is_active.is_(True)).order_by(Product.name, Plan.name)
    if product_id is not None:
        query = query.where(Plan.product_id == product_id)
    if not include_inactive:
        query = query.where(Plan.is_active.is_(True))
    return db.scalars(query).all()


@router.patch("/plans/{plan_id}", response_model=PlanPublic)
def update_plan(plan_id: int, payload: PlanUpdate, admin: RequireAdmin, db: DbSession):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise AppError("Plan not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    record_audit(db, admin.id, "catalog.plan_updated", "plan", plan.id)
    db.commit()
    db.refresh(plan)
    return plan
