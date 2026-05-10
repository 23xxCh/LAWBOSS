"""规则 ORM 模型 — 商业化 SaaS 数据架构

支持:
- 禁用词库 (banned_words)
- 替换建议 (word_replacements)
- 法规文件 (regulations)
- 规则变更历史 (rule_versions)
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Integer, Boolean, DateTime, Date, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class BannedWord(Base):
    """禁用词库"""
    __tablename__ = "banned_words"
    __table_args__ = (
        Index("ix_banned_words_lookup", "violation_type", "market", "category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    word: Mapped[str] = mapped_column(String(200), nullable=False)
    violation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # medical_claim, absolute_term, etc.
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class WordReplacement(Base):
    """替换建议"""
    __tablename__ = "word_replacements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_word: Mapped[str] = mapped_column(String(200), nullable=False)
    replacement: Mapped[str] = mapped_column(String(200), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Regulation(Base):
    """法规文件"""
    __tablename__ = "regulations"
    __table_args__ = (
        Index("ix_regulations_lookup", "market", "category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    effective_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class RuleVersion(Base):
    """规则变更历史 — 审计追踪"""
    __tablename__ = "rule_versions"
    __table_args__ = (
        Index("ix_rule_versions_table_record", "table_name", "record_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)  # banned_words, word_replacements, regulations
    record_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create, update, delete
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    change_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    changed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
