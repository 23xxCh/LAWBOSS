"""用户 LLM 配置 ORM 模型"""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class UserLLMConfig(Base):
    """用户 LLM 配置 — 每人一条"""
    __tablename__ = "user_llm_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="openai")
    api_key_encrypted: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    api_base: Mapped[str] = mapped_column(String(256), nullable=False, default="https://api.openai.com/v1")
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4o-mini")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=2048)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
