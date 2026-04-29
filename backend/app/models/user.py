"""用户 ORM 模型"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # admin, user, viewer
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Stripe 订阅相关字段
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    subscription_status: Mapped[str] = mapped_column(String(20), nullable=False, default="free")  # free, trialing, active, past_due, canceled
    subscription_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")  # free, pro, enterprise
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quota_checks_monthly: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
