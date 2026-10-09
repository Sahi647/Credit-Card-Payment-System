from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: int = Field(..., gt=0)
    card_last_four: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$")
    amount: Decimal = Field(..., gt=0, decimal_places=2)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value > Decimal("1000000"):
            raise ValueError("Payment amount cannot exceed 1,000,000")
        return value

class PaymentResponse(BaseModel):
    payment_id: str
    user_id: int
    card_id: int
    card_last_four: str
    amount: Decimal
    status: Literal["PENDING", "SUCCESS", "FAILED"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaymentResultResponse(BaseModel):
    payment_id: str
    status: Literal["PENDING", "SUCCESS", "FAILED"]
    card_id: int
    card_last_four: str
    amount: Decimal
    message: str


class CardResponse(BaseModel):
    id: int
    card_type: str
    card_holder: str
    masked_number: str
    last_four: str
    expiry: str