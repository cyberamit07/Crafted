from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    Text, ForeignKey, Enum, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
import enum

Base = declarative_base()

class DealStatus(enum.Enum):
    DRAFT = "DRAFT"
    WAITING_FOR_AGREEMENT = "WAITING_FOR_AGREEMENT"
    AGREED_WAITING_PAYMENT = "AGREED_WAITING_PAYMENT"
    ACTIVE = "ACTIVE"
    DISPUTED = "DISPUTED"
    REFUND_REQUESTED = "REFUND_REQUESTED"
    REFUNDED = "REFUNDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class PaymentMethod(enum.Enum):
    INR = "INR"
    GRAM = "GRAM"
    USDT = "USDT"
    STARS = "STARS"

class DisputeStatus(enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64))
    first_name: Mapped[Optional[str]] = mapped_column(String(128))
    last_name: Mapped[Optional[str]] = mapped_column(String(128))
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    deals_as_buyer = relationship("DealParticipant", foreign_keys="DealParticipant.buyer_id")
    deals_as_seller = relationship("DealParticipant", foreign_keys="DealParticipant.seller_id")
    vouches = relationship("Vouch", back_populates="user")
    disputes = relationship("Dispute", foreign_keys="Dispute.initiator_id")

class Deal(Base):
    __tablename__ = 'deals'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    item: Mapped[str] = mapped_column(String(512), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    holding_time: Mapped[str] = mapped_column(String(50), nullable=False)
    terms: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[DealStatus] = mapped_column(Enum(DealStatus), default=DealStatus.DRAFT)
    escrower_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    participants = relationship("DealParticipant", back_populates="deal")
    agreements = relationship("DealAgreement", back_populates="deal")
    payments = relationship("Payment", back_populates="deal")
    refunds = relationship("Refund", back_populates="deal")
    disputes = relationship("Dispute", back_populates="deal")
    escrower = relationship("User", foreign_keys=[escrower_id])

class DealParticipant(Base):
    __tablename__ = 'deal_participants'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(Integer, ForeignKey('deals.id'), nullable=False)
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    buyer_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    seller_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    buyer_agreed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    seller_agreed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    deal = relationship("Deal", back_populates="participants")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])

class DealAgreement(Base):
    __tablename__ = 'deal_agreements'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(Integer, ForeignKey('deals.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    agreed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    deal = relationship("Deal", back_populates="agreements")
    user = relationship("User")

class Payment(Base):
    __tablename__ = 'payments'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(Integer, ForeignKey('deals.id'), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    is_received: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    confirmed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    transaction_id: Mapped[Optional[str]] = mapped_column(String(128))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    deal = relationship("Deal", back_populates="payments")
    confirmer = relationship("User", foreign_keys=[confirmed_by])

class Refund(Base):
    __tablename__ = 'refunds'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(Integer, ForeignKey('deals.id'), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    processed_by: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    external_reference: Mapped[Optional[str]] = mapped_column(String(128))
    
    # Relationships
    deal = relationship("Deal", back_populates="refunds")
    processor = relationship("User", foreign_keys=[processed_by])

class Vouch(Base):
    __tablename__ = 'vouches'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(Integer, ForeignKey('deals.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    vouch_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    message_id: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Relationships
    deal = relationship("Deal")
    user = relationship("User", back_populates="vouches")

class Escrower(Base):
    __tablename__ = 'escrowers'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    adder = relationship("User", foreign_keys=[added_by])

class Admin(Base):
    __tablename__ = 'admins'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    adder = relationship("User", foreign_keys=[added_by])

class Dispute(Base):
    __tablename__ = 'disputes'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(Integer, ForeignKey('deals.id'), nullable=False)
    initiator_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(Enum(DisputeStatus), default=DisputeStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    deal = relationship("Deal", back_populates="disputes")
    initiator = relationship("User", foreign_keys=[initiator_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

class Log(Base):
    __tablename__ = 'logs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    deal_id: Mapped[Optional[str]] = mapped_column(String(20))
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    username: Mapped[Optional[str]] = mapped_column(String(64))
    details: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_logs_deal_id', 'deal_id'),
        Index('idx_logs_user_id', 'user_id'),
        Index('idx_logs_action', 'action'),
        Index('idx_logs_created_at', 'created_at'),
    )

class Setting(Base):
    __tablename__ = 'settings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
