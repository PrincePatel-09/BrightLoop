from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DbSession, RequireAdmin
from app.core.exceptions import AppError
from app.models.catalog import Discount, TaxRule
from app.models.company import Company
from app.schemas.pricing import DiscountCreate, DiscountPublic, DiscountUpdate, TaxRuleCreate, TaxRulePublic, TaxRuleUpdate
from app.services.audit_service import record_audit

router = APIRouter()


@router.get("/taxes", response_model=list[TaxRulePublic])
def list_taxes(_admin: RequireAdmin, db: DbSession):
    return db.scalars(select(TaxRule).order_by(TaxRule.name)).all()


@router.post("/taxes", response_model=TaxRulePublic, status_code=201)
def create_tax(payload: TaxRuleCreate, admin: RequireAdmin, db: DbSession):
    if db.scalar(select(TaxRule.id).where(TaxRule.name == payload.name.strip())):
        raise AppError("A tax rule with this name already exists", status_code=409, code="tax_name_taken")
    tax = TaxRule(name=payload.name.strip(), rate_percent=payload.rate_percent, is_active=True)
    db.add(tax); db.flush()
    record_audit(db, admin.id, "pricing.tax_created", "tax_rule", tax.id)
    db.commit(); db.refresh(tax)
    return tax


@router.patch("/taxes/{tax_id}", response_model=TaxRulePublic)
def update_tax(tax_id: int, payload: TaxRuleUpdate, admin: RequireAdmin, db: DbSession):
    tax = db.get(TaxRule, tax_id)
    if not tax:
        raise AppError("Tax rule not found", status_code=404, code="not_found")
    values = payload.model_dump(exclude_unset=True)
    if "name" in values:
        values["name"] = values["name"].strip()
    for key, value in values.items(): setattr(tax, key, value)
    record_audit(db, admin.id, "pricing.tax_updated", "tax_rule", tax.id)
    db.commit(); db.refresh(tax)
    return tax


@router.get("/discounts", response_model=list[DiscountPublic])
def list_discounts(_admin: RequireAdmin, db: DbSession):
    return db.scalars(select(Discount).order_by(Discount.code)).all()


@router.post("/discounts", response_model=DiscountPublic, status_code=201)
def create_discount(payload: DiscountCreate, admin: RequireAdmin, db: DbSession):
    values = payload.model_dump()
    company_id = values.pop("company_id", None)
    company = db.get(Company, company_id) if company_id else None
    if not company or not company.is_active:
        raise AppError("Select an active company for this discount", status_code=422, code="discount_company_required")
    if values["discount_type"] == "percentage" and values["value"] > 100:
        raise AppError("Percentage discounts cannot exceed 100", status_code=422, code="invalid_discount")
    if values["starts_at"] and values["ends_at"] and values["ends_at"] < values["starts_at"]:
        raise AppError("Discount end date must be on or after its start date", status_code=422, code="invalid_discount_dates")
    if db.scalar(select(Discount.id).where(Discount.company_id == company.id, Discount.code == values["code"])):
        raise AppError("A discount with this code already exists", status_code=409, code="discount_code_taken")
    discount = Discount(company_id=company.id, **values, is_active=True, times_used=0)
    db.add(discount); db.flush()
    record_audit(db, admin.id, "pricing.discount_created", "discount", discount.id, {"code": discount.code, "company_id": company.id})
    db.commit(); db.refresh(discount)
    return discount


@router.patch("/discounts/{discount_id}", response_model=DiscountPublic)
def update_discount(discount_id: int, payload: DiscountUpdate, admin: RequireAdmin, db: DbSession):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise AppError("Discount not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(discount, key, value)
    if discount.discount_type == "percentage" and discount.value > 100:
        raise AppError("Percentage discounts cannot exceed 100", status_code=422, code="invalid_discount")
    if discount.starts_at and discount.ends_at and discount.ends_at < discount.starts_at:
        raise AppError("Discount end date must be on or after its start date", status_code=422, code="invalid_discount_dates")
    record_audit(db, admin.id, "pricing.discount_updated", "discount", discount.id)
    db.commit(); db.refresh(discount)
    return discount
