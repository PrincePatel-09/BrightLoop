import hashlib
import logging
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import (
    access_token_expires,
    create_token,
    hash_password,
    needs_rehash,
    refresh_token_expires,
    reset_token_expires,
    verify_password,
)
from app.models.customer import Customer
from app.models.company import Company
from app.models.token import PasswordResetToken, RefreshToken
from app.models.user import User
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserPublic
from app.services.email_service import send_password_reset

logger = logging.getLogger(__name__)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def to_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        company_id=user.company_id,
        customer_id=user.customer.id if user.customer else None,
        created_at=user.created_at,
    )


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)

    def register_customer(self, payload: RegisterRequest) -> tuple[User, str, str]:
        if self.users.get_by_email(payload.email):
            raise AppError("An account with this email already exists", status_code=409, code="email_taken")
        company_slug = payload.company_slug or "brightloop-demo"
        default_company = self.db.scalar(select(Company).where(Company.slug == company_slug, Company.is_active.is_(True)))
        if not default_company:
            raise AppError("Company workspace was not found or is inactive", status_code=422, code="company_not_available")
        user = User(
            name=payload.name,
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            role="customer",
            is_active=True,
            company_id=default_company.id,
        )
        self.users.add(user)
        customer = Customer(user=user, company_id=default_company.id, company_name=payload.company_name)
        self.db.add(customer)
        access, refresh = self._issue_tokens(user)
        self.db.commit()
        self.db.refresh(user)
        return user, access, refresh

    def login(self, email: str, password: str, user_agent: str | None = None) -> tuple[User, str, str]:
        user = self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise AppError("Invalid email or password", status_code=401, code="invalid_credentials")
        if not user.is_active:
            raise AppError("This account has been deactivated", status_code=403, code="inactive")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        access, refresh = self._issue_tokens(user, user_agent)
        self.db.commit()
        return user, access, refresh

    def refresh(self, raw_refresh: str) -> tuple[User, str, str]:
        stored = self.tokens.get_refresh_by_hash(hash_token(raw_refresh))
        now = datetime.now(timezone.utc)
        if not stored or stored.revoked_at is not None or as_utc(stored.expires_at) <= now:
            raise AppError("Refresh token is invalid or expired", status_code=401, code="invalid_refresh")
        user = self.users.get_by_id(stored.user_id)
        if not user or not user.is_active:
            raise AppError("Account is inactive", status_code=401, code="inactive")
        stored.revoked_at = now
        access, refresh = self._issue_tokens(user, stored.user_agent)
        stored.replaced_by_id = None
        self.db.flush()
        latest = self.tokens.get_refresh_by_hash(hash_token(refresh))
        stored.replaced_by_id = latest.id if latest else None
        self.db.commit()
        return user, access, refresh

    def logout(self, raw_refresh: str) -> None:
        stored = self.tokens.get_refresh_by_hash(hash_token(raw_refresh))
        if stored and stored.revoked_at is None:
            stored.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    def forgot_password(self, email: str) -> str | None:
        user = self.users.get_by_email(email)
        generic = "If an account exists for that email, a reset link has been sent."
        if not user or not user.is_active:
            return generic
        self.tokens.expire_unused_resets(user.id)
        raw = secrets.token_urlsafe(32)
        self.tokens.add_reset(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(timezone.utc) + reset_token_expires(),
            )
        )
        self.db.commit()
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw}"
        send_password_reset(user.email, reset_url)
        if settings.is_development and not settings.SMTP_HOST:
            logger.warning("DEV password reset link for %s: %s", user.email, reset_url)
        return generic

    def reset_password(self, raw_token: str, new_password: str) -> None:
        stored = self.tokens.get_reset_by_hash(hash_token(raw_token))
        now = datetime.now(timezone.utc)
        if not stored or stored.used_at is not None or as_utc(stored.expires_at) <= now:
            raise AppError("Reset link is invalid or has expired", status_code=400, code="invalid_reset")
        user = self.users.get_by_id(stored.user_id)
        if not user:
            raise AppError("Reset link is invalid or has expired", status_code=400, code="invalid_reset")
        user.password_hash = hash_password(new_password)
        stored.used_at = now
        for token in user.refresh_tokens:
            if token.revoked_at is None:
                token.revoked_at = now
        self.db.commit()

    def create_staff(self, name: str, email: str, password: str) -> User:
        if self.users.get_by_email(email):
            raise AppError("An account with this email already exists", status_code=409, code="email_taken")
        user = User(
            name=name.strip(),
            email=email.lower(),
            password_hash=hash_password(password),
            role="staff",
            is_active=True,
        )
        self.users.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_staff(self, staff_id: int, name: str | None, is_active: bool | None) -> User:
        user = self.users.get_by_id(staff_id)
        if not user or user.role != "staff":
            raise AppError("Staff account not found", status_code=404, code="not_found")
        if name is not None:
            user.name = name.strip()
        if is_active is not None:
            user.is_active = is_active
            if not is_active:
                now = datetime.now(timezone.utc)
                for token in user.refresh_tokens:
                    if token.revoked_at is None:
                        token.revoked_at = now
        self.db.commit()
        self.db.refresh(user)
        return user

    def _issue_tokens(self, user: User, user_agent: str | None = None) -> tuple[str, str]:
        access = create_token(
            subject=str(user.id),
            token_type="access",
            expires_delta=access_token_expires(),
            extra={"role": user.role},
        )
        raw_refresh = secrets.token_urlsafe(48)
        self.tokens.add_refresh(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                expires_at=datetime.now(timezone.utc) + refresh_token_expires(),
                user_agent=user_agent,
            )
        )
        return access, raw_refresh
