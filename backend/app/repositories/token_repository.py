from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.token import PasswordResetToken, RefreshToken


class TokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_refresh(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        self.db.flush()
        return token

    def get_refresh_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def add_reset(self, token: PasswordResetToken) -> PasswordResetToken:
        self.db.add(token)
        self.db.flush()
        return token

    def get_reset_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self.db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))

    def expire_unused_resets(self, user_id: int) -> None:
        now = datetime.now(timezone.utc)
        tokens = self.db.scalars(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        for token in tokens:
            if token.expires_at > now:
                token.expires_at = now
