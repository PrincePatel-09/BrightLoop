from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import DbSession, RequireAdmin
from app.models.base import AppSetting
from app.schemas.settings import SettingsPublic, SettingsUpdate
from app.services.audit_service import record_audit

router = APIRouter()
DEFAULTS = {"company_name": "Brightloop Software", "currency_code": "INR", "invoice_prefix": "INV", "payment_terms_days": "14"}


@router.get("", response_model=SettingsPublic)
def get_settings(_admin: RequireAdmin, db: DbSession):
    values = dict(DEFAULTS)
    for row in db.scalars(select(AppSetting)).all():
        if row.key in values:
            values[row.key] = row.value
    return {**values, "payment_terms_days": int(values["payment_terms_days"])}


@router.put("", response_model=SettingsPublic)
def update_settings(payload: SettingsUpdate, admin: RequireAdmin, db: DbSession):
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        row = db.get(AppSetting, key)
        if row:
            row.value = str(value)
        else:
            db.add(AppSetting(key=key, value=str(value)))
    record_audit(db, admin.id, "settings.updated", "settings", None, {"keys": list(payload.model_dump(exclude_unset=True))})
    db.commit()
    return get_settings(_admin, db)
