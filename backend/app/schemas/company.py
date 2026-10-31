from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    legal_name: str | None = Field(default=None, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = None
    tax_id: str | None = Field(default=None, max_length=80)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    legal_name: str | None = Field(default=None, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = None
    tax_id: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None


class CompanyPublic(CompanyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    user_count: int
    created_at: datetime


class CompanyDirectoryItem(BaseModel):
    id: int
    name: str
    slug: str
