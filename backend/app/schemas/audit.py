from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    details: dict
    created_at: datetime
