from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.deps import DbSession, RequireAdmin
from app.core.exceptions import AppError
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyDirectoryItem, CompanyPublic, CompanyUpdate
from app.schemas.user import CompanyAdminCreateRequest, UserPublic
from app.core.security import hash_password
from app.services.audit_service import record_audit
from datetime import datetime, timezone
from app.schemas.user import StaffUpdateRequest

router = APIRouter()


def company_public(company: Company, user_count: int) -> CompanyPublic:
    return CompanyPublic(
        id=company.id,
        name=company.name,
        slug=company.slug,
        legal_name=company.legal_name,
        email=company.email,
        phone=company.phone,
        address=company.address,
        tax_id=company.tax_id,
        is_active=company.is_active,
        user_count=user_count,
        created_at=company.created_at,
    )


def user_count_query(company_id: int):
    return select(func.count(User.id)).where(User.company_id == company_id)


@router.get("/directory", response_model=list[CompanyDirectoryItem])
def company_directory(db: DbSession):
    return [{"id": company.id, "name": company.name, "slug": company.slug}
        for company in db.scalars(select(Company).where(Company.is_active.is_(True)).order_by(Company.name)).all()]


@router.get("", response_model=list[CompanyPublic])
def list_companies(_admin: RequireAdmin, db: DbSession):
    companies = db.scalars(select(Company).order_by(Company.name)).all()
    return [company_public(company, db.scalar(user_count_query(company.id)) or 0) for company in companies]


@router.post("", response_model=CompanyPublic, status_code=201)
def create_company(payload: CompanyCreate, admin: RequireAdmin, db: DbSession):
    if db.scalar(select(Company.id).where(Company.slug == payload.slug)):
        raise AppError("A company with this slug already exists", status_code=409, code="slug_taken")
    company = Company(**payload.model_dump())
    db.add(company)
    db.flush()
    record_audit(db, admin.id, "company.created", "company", company.id, {"slug": company.slug})
    db.commit()
    db.refresh(company)
    return company_public(company, 0)


@router.post("/{company_id}/admins", response_model=UserPublic, status_code=201)
def create_company_admin(company_id: int, payload: CompanyAdminCreateRequest, admin: RequireAdmin, db: DbSession):
    company = db.get(Company, company_id)
    if not company or not company.is_active:
        raise AppError("Active company not found", status_code=404, code="company_not_found")
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise AppError("An account with this email already exists", status_code=409, code="email_taken")
    user = User(
        name=payload.name.strip(), email=email, password_hash=hash_password(payload.password),
        role="company_admin", company_id=company.id, is_active=True,
    )
    db.add(user)
    db.flush()
    record_audit(db, admin.id, "company.admin_created", "user", user.id, {"company_id": company.id})
    db.commit()
    db.refresh(user)
    return UserPublic.model_validate(user)


@router.get("/{company_id}/admins", response_model=list[UserPublic])
def list_company_admins(company_id: int, _admin: RequireAdmin, db: DbSession):
    if not db.get(Company, company_id):
        raise AppError("Company not found", status_code=404, code="company_not_found")
    return db.scalars(select(User).where(User.company_id == company_id, User.role == "company_admin").order_by(User.id)).all()


@router.patch("/{company_id}/admins/{user_id}", response_model=UserPublic)
def update_company_admin(company_id: int, user_id: int, payload: StaffUpdateRequest, admin: RequireAdmin, db: DbSession):
    user = db.scalar(select(User).where(User.id == user_id, User.company_id == company_id, User.role == "company_admin"))
    if not user:
        raise AppError("Company administrator not found", status_code=404, code="not_found")
    values = payload.model_dump(exclude_unset=True)
    if values.get("name") is not None:
        user.name = values["name"].strip()
    if values.get("is_active") is not None:
        user.is_active = values["is_active"]
        if not user.is_active:
            now = datetime.now(timezone.utc)
            for token in user.refresh_tokens:
                if token.revoked_at is None:
                    token.revoked_at = now
    record_audit(db, admin.id, "company.admin_updated", "user", user.id, {"company_id": company_id, "active": user.is_active})
    db.commit()
    db.refresh(user)
    return UserPublic.model_validate(user)


@router.patch("/{company_id}", response_model=CompanyPublic)
def update_company(company_id: int, payload: CompanyUpdate, admin: RequireAdmin, db: DbSession):
    company = db.get(Company, company_id)
    if not company:
        raise AppError("Company not found", status_code=404, code="not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
    record_audit(db, admin.id, "company.updated", "company", company.id, {"active": company.is_active})
    db.commit()
    db.refresh(company)
    return company_public(company, db.scalar(user_count_query(company.id)) or 0)
