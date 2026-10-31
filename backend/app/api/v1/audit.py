from fastapi import APIRouter, Query

from app.core.deps import DbSession, RequireAdmin
from app.schemas.audit import AuditEventPublic
from app.services.audit_service import recent_events

router = APIRouter()


@router.get("", response_model=list[AuditEventPublic])
def list_audit_events(_admin: RequireAdmin, db: DbSession, limit: int = Query(default=100, ge=1, le=250)):
    return recent_events(db, limit)
