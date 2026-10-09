from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.sql import func
from .database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    card_id = Column(Integer, nullable=False)
    card_last_four = Column(String(4), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default="PENDING", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    payment_id = Column(String(50), nullable=False)
    card_id = Column(Integer, nullable=False)
    card_last_four = Column(String(4), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Transaction {self.transaction_id}>"