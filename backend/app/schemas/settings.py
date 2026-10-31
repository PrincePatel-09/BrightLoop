from pydantic import BaseModel, Field, field_validator


class SettingsUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=2, max_length=180)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    invoice_prefix: str | None = Field(default=None, min_length=2, max_length=12, pattern=r"^[A-Za-z0-9_-]+$")
    payment_terms_days: int | None = Field(default=None, ge=1, le=90)

    @field_validator("currency_code", "invoice_prefix")
    @classmethod
    def uppercase_codes(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class SettingsPublic(BaseModel):
    company_name: str
    currency_code: str
    invoice_prefix: str
    payment_terms_days: int
