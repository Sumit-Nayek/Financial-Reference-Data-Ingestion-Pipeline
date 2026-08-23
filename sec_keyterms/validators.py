from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SecurityReferenceSchema(BaseModel):
    isin: str = Field(..., min_length=12, max_length=12)
    bse_scrip_code: Optional[str] = Field(None, min_length=6, max_length=6)
    issuer_name: str = Field(..., min_length=2)
    coupon_rate: float = Field(..., ge=0.0, le=25.0)
    maturity_date: str
    credit_rating: Optional[str] = None
    currency: str = Field(default="INR", min_length=3, max_length=3)

    @field_validator("isin")
    @classmethod
    def validate_indian_isin(cls, v: str) -> str:
        v = v.upper()
        # INE = Corporate Debt/Equity, INF = Mutual Funds, IN0 = Govt Securities
        valid_prefixes = ("INE", "INF", "IN0", "IN9")
        if not v.startswith(valid_prefixes):
            raise ValueError(f"Invalid ISIN prefix. Indian securities must start with: {valid_prefixes}")
        return v

    @field_validator("bse_scrip_code")
    @classmethod
    def validate_scrip_code(cls, v: Optional[str]) -> Optional[str]:
        if v and (not v.isdigit() or not v.startswith("5")):
            raise ValueError("BSE equity/debt scrip codes must be 6-digit numeric starting with 5.")
        return v