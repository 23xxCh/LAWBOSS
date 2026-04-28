"""报告存储与查询服务"""
import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models.report import CheckReport
from ..services.compliance_checker import ComplianceReport, ViolationType


def save_report(
    db: Session,
    description: str,
    report: ComplianceReport,
) -> CheckReport:
    """保存检测报告到数据库"""
    report_id = str(uuid.uuid4())

    # 将 violations dataclass 列表转为可序列化字典
    violations_data = []
    for v in report.violations:
        violations_data.append({
            "type": v.type.value if isinstance(v.type, ViolationType) else v.type,
            "type_label": v.type_label,
            "content": v.content,
            "regulation": v.regulation,
            "regulation_detail": v.regulation_detail,
            "severity": v.severity.value if hasattr(v.severity, "value") else v.severity,
            "severity_label": v.severity_label,
            "suggestion": v.suggestion,
            "score": v.score,
        })

    db_report = CheckReport(
        id=report_id,
        description=description,
        category=report.category,
        market=report.market,
        risk_score=report.risk_score,
        risk_level=report.risk_level,
        risk_description=report.risk_description,
        violations_json=json.dumps(violations_data, ensure_ascii=False),
        compliant_version=report.compliant_version,
        required_labels_json=json.dumps(report.required_labels, ensure_ascii=False),
        required_certifications_json=json.dumps(report.required_certifications, ensure_ascii=False),
        suggestions_json=json.dumps(report.suggestions, ensure_ascii=False),
        created_at=datetime.now(timezone.utc),
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report


def get_report(db: Session, report_id: str) -> Optional[CheckReport]:
    """获取单条报告"""
    return db.query(CheckReport).filter(CheckReport.id == report_id).first()


def get_reports(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    market: Optional[str] = None,
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> tuple:
    """分页查询报告列表，返回 (items, total)"""
    query = db.query(CheckReport)

    if market:
        query = query.filter(CheckReport.market == market)
    if category:
        query = query.filter(CheckReport.category == category)
    if risk_level:
        query = query.filter(CheckReport.risk_level == risk_level)

    total = query.count()
    items = (
        query.order_by(CheckReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def delete_report(db: Session, report_id: str) -> bool:
    """删除报告，返回是否成功"""
    db_report = db.query(CheckReport).filter(CheckReport.id == report_id).first()
    if db_report:
        db.delete(db_report)
        db.commit()
        return True
    return False
