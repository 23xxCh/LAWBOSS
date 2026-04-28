"""合规检测 API 路由"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas.check import (
    CheckRequest,
    CheckResponse,
    ViolationItem,
    BatchCheckRequest,
    BatchCheckResponse,
)
from ..services.compliance_checker import ComplianceChecker, ViolationType
from ..services import report_service
from ..config import SUPPORTED_MARKETS, SUPPORTED_CATEGORIES
from ..models.user import User
from ..routers.auth import get_current_user
from ..utils.converters import report_to_response

router = APIRouter(tags=["合规检测"])


def _get_checker(request: Request) -> ComplianceChecker:
    """通过 Request 依赖注入获取检测引擎，避免循环导入"""
    return request.app.state.checker


def _validate_market_category(market: str, category: str):
    """验证市场和类别是否支持"""
    if market not in SUPPORTED_MARKETS:
        raise HTTPException(status_code=400, detail=f"不支持的市场: {market}，支持: {SUPPORTED_MARKETS}")
    if category not in SUPPORTED_CATEGORIES.get(market, []):
        raise HTTPException(
            status_code=400,
            detail=f"市场 {market} 不支持类别: {category}，支持: {SUPPORTED_CATEGORIES.get(market, [])}",
        )


@router.post("/check", response_model=CheckResponse, summary="合规检测")
async def check_compliance(request: CheckRequest, http_request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """提交产品描述进行合规检测，并保存报告"""
    _validate_market_category(request.market, request.category)
    checker = _get_checker(http_request)

    report = await asyncio.to_thread(
        checker.check_text,
        description=request.description,
        product_category=request.category,
        target_market=request.market,
    )

    report_service.save_report(db, request.description, report)
    return report_to_response(report)


@router.post("/check/batch", response_model=BatchCheckResponse, summary="批量合规检测")
async def batch_check_compliance(request: BatchCheckRequest, http_request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """批量提交产品描述进行合规检测"""
    checker = _get_checker(http_request)

    results: List[CheckResponse] = []
    high_risk = 0
    medium_risk = 0
    low_risk = 0

    for item in request.items:
        _validate_market_category(item.market, item.category)

        report = await asyncio.to_thread(
            checker.check_text,
            description=item.description,
            product_category=item.category,
            target_market=item.market,
        )
        resp = report_to_response(report)
        results.append(resp)

        report_service.save_report(db, item.description, report)

        if report.risk_score >= 70:
            high_risk += 1
        elif report.risk_score >= 40:
            medium_risk += 1
        else:
            low_risk += 1

    return BatchCheckResponse(
        results=results,
        total=len(results),
        high_risk_count=high_risk,
        medium_risk_count=medium_risk,
        low_risk_count=low_risk,
    )
