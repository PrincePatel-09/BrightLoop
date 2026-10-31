from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerUpdate(BaseModel):
    company_name: str | None = Field(default=None, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    billing_address: str | None = Field(default=None, max_length=2000)


class CustomerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    is_active: bool
    company_name: str | None
    phone: str | None
    billing_address: str | None
    created_at: datetime
