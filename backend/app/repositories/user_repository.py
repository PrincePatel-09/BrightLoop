from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.scalar(
            select(User).options(selectinload(User.customer)).where(User.id == user_id)
        )

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(
            select(User).options(selectinload(User.customer)).where(User.email == email.lower())
        )

    def list_by_role(self, role: str) -> list[User]:
        return list(
            self.db.scalars(
                select(User)
                .options(selectinload(User.customer))
                .where(User.role == role)
                .order_by(User.id)
            )
        )

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
