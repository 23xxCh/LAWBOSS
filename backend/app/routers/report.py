"""报告查询 API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.check import CheckResponse, ViolationItem
from ..schemas.report import ReportItem, ReportListResponse, ReportDetailResponse
from ..schemas.common import MessageResponse
from ..models.report import CheckReport
from ..models.user import User
from ..services import report_service
from ..routers.auth import get_current_user, require_role

router = APIRouter(tags=["检测报告"])


@router.get("/reports", response_model=ReportListResponse, summary="获取检测报告列表")
async def list_reports(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    market: Optional[str] = Query(default=None, description="市场筛选"),
    category: Optional[str] = Query(default=None, description="类别筛选"),
    risk_level: Optional[str] = Query(default=None, description="风险等级筛选"),
    db: Session = Depends(get_db),
):
    """分页查询检测历史报告"""
    items, total = report_service.get_reports(
        db, page=page, page_size=page_size,
        market=market, category=category, risk_level=risk_level,
    )
    return ReportListResponse(
        items=[
            ReportItem(
                id=r.id,
                category=r.category,
                market=r.market,
                risk_score=r.risk_score,
                risk_level=r.risk_level,
                violation_count=len(r.get_violations()),
                created_at=r.created_at,
            )
            for r in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/{report_id}", response_model=ReportDetailResponse, summary="获取报告详情")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    """获取单条检测报告详情"""
    db_report = report_service.get_report(db, report_id)
    if not db_report:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 重建 CheckResponse
    violations = [
        ViolationItem(**v) for v in db_report.get_violations()
    ]
    result = CheckResponse(
        risk_score=db_report.risk_score,
        risk_level=db_report.risk_level,
        risk_description=db_report.risk_description or "",
        market=db_report.market,
        category=db_report.category,
        violations=violations,
        compliant_version=db_report.compliant_version or "",
        required_labels=db_report.get_required_labels(),
        required_certifications=db_report.get_required_certifications(),
        suggestions=db_report.get_suggestions(),
    )
    return ReportDetailResponse(
        id=db_report.id,
        description=db_report.description,
        result=result,
        created_at=db_report.created_at,
    )


@router.delete("/reports/{report_id}", response_model=MessageResponse, summary="删除报告")
async def delete_report(report_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    """删除检测报告"""
    success = report_service.delete_report(db, report_id)
    if not success:
        raise HTTPException(status_code=404, detail="报告不存在")
    return MessageResponse(message="删除成功")


@router.get("/reports/{report_id}/export/pdf", summary="导出报告 PDF")
async def export_report_pdf(report_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """导出检测报告为 PDF"""
    from ..services.export_service import generate_report_pdf
    from ..services.compliance_checker import ComplianceReport, Violation, ViolationType, Severity

    db_report = report_service.get_report(db, report_id)
    if not db_report:
        raise HTTPException(status_code=404, detail="报告不存在")

    # 重建 ComplianceReport
    violations = []
    for v_data in db_report.get_violations():
        vtype_str = v_data.get("type", "false_advertising")
        vtype_map = {
            "medical_claim": ViolationType.MEDICAL_CLAIM,
            "absolute_term": ViolationType.ABSOLUTE_TERM,
            "false_advertising": ViolationType.FALSE_ADVERTISING,
            "missing_label": ViolationType.MISSING_LABEL,
            "banned_ingredient": ViolationType.BANNED_INGREDIENT,
        }
        severity_str = v_data.get("severity", "medium")
        severity = Severity.HIGH if severity_str == "high" else Severity.LOW if severity_str == "low" else Severity.MEDIUM

        violations.append(Violation(
            type=vtype_map.get(vtype_str, ViolationType.FALSE_ADVERTISING),
            type_label=v_data.get("type_label", ""),
            content=v_data.get("content", ""),
            regulation=v_data.get("regulation", ""),
            regulation_detail=v_data.get("regulation_detail", ""),
            severity=severity,
            severity_label=v_data.get("severity_label", ""),
            suggestion=v_data.get("suggestion", ""),
            score=v_data.get("score", 0),
        ))

    report = ComplianceReport(
        risk_score=db_report.risk_score,
        risk_level=db_report.risk_level,
        risk_description=db_report.risk_description or "",
        market=db_report.market,
        category=db_report.category,
        violations=violations,
        compliant_version=db_report.compliant_version or "",
        required_labels=db_report.get_required_labels(),
        required_certifications=db_report.get_required_certifications(),
        suggestions=db_report.get_suggestions(),
    )

    pdf_bytes = generate_report_pdf(db_report.description, report, report_id=db_report.id)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=crossguard_report_{report_id[:8]}.pdf"},
    )
