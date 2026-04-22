"""检测报告 ORM 模型"""
import json
from datetime import datetime, timezone
from typing import List

from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class CheckReport(Base):
    """检测报告持久化模型"""
    __tablename__ = "check_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    risk_description: Mapped[str] = mapped_column(String(200), nullable=True)
    violations_json: Mapped[str] = mapped_column(Text, nullable=True)
    compliant_version: Mapped[str] = mapped_column(Text, nullable=True)
    required_labels_json: Mapped[str] = mapped_column(Text, nullable=True)
    required_certifications_json: Mapped[str] = mapped_column(Text, nullable=True)
    suggestions_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    def set_violations(self, violations: list):
        self.violations_json = json.dumps(violations, ensure_ascii=False)

    def get_violations(self) -> list:
        if self.violations_json:
            return json.loads(self.violations_json)
        return []

    def set_required_labels(self, labels: List[str]):
        self.required_labels_json = json.dumps(labels, ensure_ascii=False)

    def get_required_labels(self) -> List[str]:
        if self.required_labels_json:
            return json.loads(self.required_labels_json)
        return []

    def set_required_certifications(self, certs: List[str]):
        self.required_certifications_json = json.dumps(certs, ensure_ascii=False)

    def get_required_certifications(self) -> List[str]:
        if self.required_certifications_json:
            return json.loads(self.required_certifications_json)
        return []

    def set_suggestions(self, suggestions: List[str]):
        self.suggestions_json = json.dumps(suggestions, ensure_ascii=False)

    def get_suggestions(self) -> List[str]:
        if self.suggestions_json:
            return json.loads(self.suggestions_json)
        return []
