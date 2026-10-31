from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import AuditEvent


def record_audit(db: Session, actor_id: int | None, action: str, entity_type: str, entity_id: int | None, details: dict | None = None) -> None:
    db.add(AuditEvent(actor_user_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}))


def recent_events(db: Session, limit: int = 100) -> list[AuditEvent]:
    return db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit)).all()
