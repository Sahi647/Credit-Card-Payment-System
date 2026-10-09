from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import Payment, Transaction


def generate_payment_id():
    return f"SIM-PAY-{uuid4().hex}"


def generate_transaction_id():
    return f"TXN-{uuid4().hex}"


def record_transaction(db: Session, payment: Payment):
    transaction = db.query(Transaction).filter(Transaction.payment_id == payment.payment_id).first()
    if transaction is None:
        transaction = Transaction(
            transaction_id=generate_transaction_id(),
            payment_id=payment.payment_id,
        )
        db.add(transaction)
    transaction.user_id = payment.user_id
    transaction.card_id = payment.card_id
    transaction.card_last_four = payment.card_last_four
    transaction.amount = payment.amount
    transaction.status = payment.status
    return transaction


def sync_missing_transactions(db: Session):
    payments = (
        db.query(Payment)
        .outerjoin(Transaction, Transaction.payment_id == Payment.payment_id)
        .filter(Transaction.id.is_(None))
        .all()
    )
    for payment in payments:
        db.add(
            Transaction(
                transaction_id=generate_transaction_id(),
                user_id=payment.user_id,
                payment_id=payment.payment_id,
                card_id=payment.card_id,
                card_last_four=payment.card_last_four,
                amount=payment.amount,
                status=payment.status,
            )
        )
    if payments:
        db.commit()


def get_saved_card(db: Session, card_id: int, user_id: int):
    query = text("""
        SELECT id, user_id, card_type, card_holder, masked_number, last_four, expiry
        FROM cards_card
        WHERE id = :card_id AND user_id = :user_id
    """)
    return db.execute(query, {"card_id": card_id, "user_id": user_id}).mappings().first()


def validate_amount(amount):
    if amount is None:
        return False, "Payment amount is required."
    try:
        amount = Decimal(str(amount))
        if not amount.is_finite():
            return False, "Payment amount must be a finite number."
    except (InvalidOperation, TypeError, ValueError):
        return False, "Payment amount must be a valid number."
    if amount <= 0:
        return False, "Payment amount must be greater than zero."
    if amount > 1000000:
        return False, "Payment amount exceeds the allowed limit."
    return True, "Amount is valid."


def create_payment(
    db: Session,
    user_id: int,
    card_id: int,
    card_last_four: str,
    amount: Decimal,
):
    amount_valid, amount_message = validate_amount(amount)
    if not amount_valid:
        raise ValueError(amount_message)
    card = get_saved_card(db, card_id, user_id)
    if not card:
        raise ValueError("Card not found.")
    if card["last_four"] != card_last_four:
        raise ValueError("Card number incorrect. Check the last four digits.")

    amount = Decimal(str(amount))
    rounded_amount = amount.quantize(Decimal("0.01"))
    if amount != rounded_amount:
        raise ValueError("Payment amount cannot have more than two decimal places.")
    amount = rounded_amount
    payment = Payment(
        payment_id=generate_payment_id(),
        user_id=user_id,
        card_id=card["id"],
        card_last_four=card["last_four"],
        amount=amount,
        status="SUCCESS",
    )
    db.add(payment)
    record_transaction(db, payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_payment(db: Session, payment_id: str, user_id: int):
    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id, Payment.user_id == user_id)
        .first()
    )
    if not payment:
        return None, "Payment not found."
    return payment, "Payment found."