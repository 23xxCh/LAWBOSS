"""反馈 ORM 模型 — 商业化 SaaS 数据架构

支持:
- 用户反馈 (user_feedbacks)
- 规则优化建议 (optimization_suggestions)
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class UserFeedbackDB(Base):
    """用户反馈 — 数据库存储"""
    __tablename__ = "user_feedbacks"
    __table_args__ = (
        Index("ix_user_feedbacks_user", "user_id"),
        Index("ix_user_feedbacks_type", "feedback_type"),
        Index("ix_user_feedbacks_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    report_id: Mapped[str] = mapped_column(String(36), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)  # false_positive, false_negative, correct
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    violation_content: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    user_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    market: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, reviewed, applied
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class OptimizationSuggestionDB(Base):
    """规则优化建议 — 数据库存储"""
    __tablename__ = "optimization_suggestions"
    __table_args__ = (
        Index("ix_optimization_suggestions_status", "status"),
        Index("ix_optimization_suggestions_type", "violation_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False)  # remove_word, add_word, adjust_score
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    feedback_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of feedback IDs
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected, applied
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
