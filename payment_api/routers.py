from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from authentication.roles import ADMINISTRATOR, CUSTOMER
from .auth import require_roles
from .database import get_db
from .schemas import (
    CardResponse,
    PaymentCreate,
    PaymentResponse,
    PaymentResultResponse,
)
from .services import (
    create_payment,
    get_payment,
)

router = APIRouter(prefix="/api/payments", tags=["Payments"])
payment_role = require_roles(ADMINISTRATOR, CUSTOMER)


def _cards_for_user(user_id: int, db: Session):
    query = text(
        """
        SELECT id, card_type, card_holder, masked_number, last_four, expiry
        FROM cards_card
        WHERE user_id = :user_id
        ORDER BY id DESC
        """
    )
    return db.execute(query, {"user_id": user_id}).mappings().all()


@router.get("/cards/", response_model=list[CardResponse])
def get_current_user_cards(
    user_id: int = Depends(payment_role),
    db: Session = Depends(get_db),
):
    return _cards_for_user(user_id, db)


@router.get("/cards/{requested_user_id}", response_model=list[CardResponse])
def get_user_cards(
    requested_user_id: int,
    user_id: int = Depends(payment_role),
    db: Session = Depends(get_db),
):
    if requested_user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own cards.")
    return _cards_for_user(user_id, db)


@router.post(
    "/",
    response_model=PaymentResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def make_payment(
    payment_data: PaymentCreate,
    user_id: int = Depends(payment_role),
    db: Session = Depends(get_db),
):
    try:
        payment = create_payment(
            db,
            user_id,
            payment_data.card_id,
            payment_data.card_last_four,
            payment_data.amount,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "card_id": payment.card_id,
        "card_last_four": payment.card_last_four,
        "amount": payment.amount,
        "message": "Simulation successful. No real money was charged.",
    }


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment_details(
    payment_id: str,
    user_id: int = Depends(payment_role),
    db: Session = Depends(get_db),
):
    payment, _ = get_payment(db, payment_id, user_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found.")
    return payment
