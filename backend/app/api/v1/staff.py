from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import DbSession, RequireAdmin
from app.repositories.user_repository import UserRepository
from app.schemas.user import StaffCreateRequest, StaffUpdateRequest, UserPublic
from app.services.auth_service import AuthService, to_public
from app.services.audit_service import record_audit

router = APIRouter()


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


AuthDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("", response_model=UserPublic, status_code=201)
def create_staff(admin: RequireAdmin, payload: StaffCreateRequest, service: AuthDep, db: DbSession):
    user = service.create_staff(payload.name, payload.email, payload.password)
    record_audit(db, admin.id, "staff.created", "user", user.id)
    db.commit()
    return to_public(user)


@router.get("", response_model=list[UserPublic])
def list_staff(_admin: RequireAdmin, db: DbSession):
    return [to_public(user) for user in UserRepository(db).list_by_role("staff")]


@router.patch("/{staff_id}", response_model=UserPublic)
def update_staff(admin: RequireAdmin, staff_id: int, payload: StaffUpdateRequest, service: AuthDep, db: DbSession):
    user = service.update_staff(staff_id, payload.name, payload.is_active)
    record_audit(db, admin.id, "staff.updated", "user", user.id, {"active": user.is_active})
    db.commit()
    return to_public(user)
