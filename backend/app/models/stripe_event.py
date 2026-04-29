"""Stripe Webhook 事件模型 — 用于幂等处理"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class StripeEvent(Base):
    """Stripe Webhook 事件记录，用于幂等处理"""
    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Stripe event ID
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    customer_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    subscription_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
