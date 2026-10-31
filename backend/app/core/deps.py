from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.security import decode_token
from app.models.user import User
from app.models.company import Company
from app.repositories.user_repository import UserRepository

DbSession = Annotated[Session, Depends(get_db)]


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("Not authenticated", status_code=401, code="unauthenticated")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    db: DbSession,
    token: Annotated[str, Depends(get_bearer_token)],
) -> User:
    payload = decode_token(token, "access")
    user_id = payload.get("sub")
    if not user_id:
        raise AppError("Invalid token", status_code=401, code="invalid_token")
    user = UserRepository(db).get_by_id(int(user_id))
    if not user or not user.is_active:
        raise AppError("Account is inactive or not found", status_code=401, code="inactive")
    if user.company_id is not None and user.role != "admin":
        company = db.get(Company, user.company_id)
        if not company or not company.is_active:
            raise AppError("Company workspace is inactive", status_code=403, code="company_inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AppError("You do not have permission to perform this action", status_code=403, code="forbidden")
        return user

    return checker


RequireAdmin = Annotated[User, Depends(require_roles("admin"))]
RequireStaff = Annotated[User, Depends(require_roles("admin", "staff"))]
RequireCustomer = Annotated[User, Depends(require_roles("customer"))]
RequireCompanyAdmin = Annotated[User, Depends(require_roles("company_admin"))]
RequireCompanyStaff = Annotated[User, Depends(require_roles("company_admin", "company_staff"))]
