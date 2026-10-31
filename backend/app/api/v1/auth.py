from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.core.rate_limit import limiter
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.schemas.user import UserPublic
from app.services.auth_service import AuthService, to_public

router = APIRouter()


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


AuthDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=TokenPair, status_code=201)
def register(payload: RegisterRequest, service: AuthDep):
    _user, access, refresh = service.register_customer(payload)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenPair)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, payload: LoginRequest, service: AuthDep):
    _user, access, refresh = service.login(
        payload.email,
        payload.password,
        user_agent=request.headers.get("user-agent"),
    )
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, service: AuthDep):
    _user, access, refresh_token = service.refresh(payload.refresh_token)
    return TokenPair(access_token=access, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, service: AuthDep):
    service.logout(payload.refresh_token)
    return MessageResponse(message="Signed out")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_RESET)
def forgot_password(request: Request, payload: ForgotPasswordRequest, service: AuthDep):
    message = service.forgot_password(payload.email)
    return MessageResponse(message=message or "If an account exists for that email, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, service: AuthDep):
    service.reset_password(payload.token, payload.password)
    return MessageResponse(message="Password updated. You can now sign in.")


@router.get("/me", response_model=UserPublic)
def me(user: CurrentUser):
    return to_public(user)
