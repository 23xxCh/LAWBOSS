"""公共工具函数"""
from ..schemas.check import CheckResponse, ViolationItem
from ..services.compliance_checker import ViolationType


def violation_to_item(v) -> ViolationItem:
    """将 dataclass Violation 转为 Pydantic ViolationItem"""
    return ViolationItem(
        type=v.type.value if isinstance(v.type, ViolationType) else v.type,
        type_label=v.type_label,
        content=v.content,
        regulation=v.regulation,
        regulation_detail=v.regulation_detail,
        severity=v.severity.value if hasattr(v.severity, "value") else v.severity,
        severity_label=v.severity_label,
        suggestion=v.suggestion,
        score=v.score,
    )


def report_to_response(report, report_id: str = "") -> CheckResponse:
    """将 ComplianceReport dataclass 转为 CheckResponse"""
    return CheckResponse(
        report_id=report_id,
        risk_score=report.risk_score,
        risk_level=report.risk_level,
        risk_description=report.risk_description,
        market=report.market,
        category=report.category,
        violations=[violation_to_item(v) for v in report.violations],
        compliant_version=report.compliant_version,
        required_labels=report.required_labels,
        required_certifications=report.required_certifications,
        suggestions=report.suggestions,
    )
