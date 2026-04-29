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
    ComparisonCheckResponse,
    ComparisonResult,
)
from ..services.compliance_checker import ComplianceChecker, ViolationType
from ..services import report_service
from ..services.quota_service import check_and_increment_quota, decrement_quota
from ..config import SUPPORTED_MARKETS, SUPPORTED_CATEGORIES
from ..models.user import User
from ..routers.auth import get_current_user
from ..utils.converters import report_to_response
from ..schemas.check import (
    MultiMarketCheckResponse, MultiMarketResult,
    LLMComparisonRequest, LLMComparisonResponse, LLMComparisonResult,
)
from ..services.llm_config_service import PROVIDER_PRESETS

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

    # 配额检查
    allowed, current = check_and_increment_quota(
        current_user.id,
        "checks",
        current_user.quota_checks_monthly,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"月度检测配额已用尽 ({current}/{current_user.quota_checks_monthly})，请升级订阅",
        )

    checker = _get_checker(http_request)

    # 同步当前用户的 LLM 配置到 AI 检测器
    checker.sync_ai_config_for_user(current_user.id, db)

    try:
        report = await asyncio.to_thread(
            checker.check_text,
            description=request.description,
            product_category=request.category,
            target_market=request.market,
        )

        db_report = report_service.save_report(db, request.description, report)
        return report_to_response(report, report_id=db_report.id)
    except Exception as e:
        # 检测失败时回滚配额
        decrement_quota(current_user.id, "checks")
        raise e


def _report_to_comparison_result(report) -> ComparisonResult:
    """将 ComplianceReport 转换为 ComparisonResult"""
    return ComparisonResult(
        risk_score=report.risk_score,
        risk_level=report.risk_level,
        risk_description=report.risk_description,
        violations=[
            ViolationItem(
                type=v.type.value if hasattr(v.type, 'value') else v.type,
                type_label=v.type_label,
                content=v.content,
                regulation=v.regulation,
                regulation_detail=v.regulation_detail,
                severity=v.severity.value if hasattr(v.severity, 'value') else v.severity,
                severity_label=v.severity_label,
                suggestion=v.suggestion,
                score=v.score,
            )
            for v in report.violations
        ],
        violation_count=len(report.violations),
        compliant_version=report.compliant_version,
    )


@router.post("/check/comparison", response_model=ComparisonCheckResponse, summary="对比模式合规检测")
async def check_comparison(request: CheckRequest, http_request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """对比模式：分别返回关键词检测、AI检测、混合检测的结果对比"""
    _validate_market_category(request.market, request.category)
    checker = _get_checker(http_request)
    checker.sync_ai_config_for_user(current_user.id, db)

    # 关键词检测（仅规则）
    keyword_report = await asyncio.to_thread(
        checker.check_text,
        description=request.description,
        product_category=request.category,
        target_market=request.market,
        check_mode="keyword_only",
    )

    # AI 检测（仅语义）
    ai_report = None
    try:
        ai_result = await asyncio.to_thread(
            checker.check_text,
            description=request.description,
            product_category=request.category,
            target_market=request.market,
            check_mode="ai_only",
        )
        if ai_result.violations:
            ai_report = _report_to_comparison_result(ai_result)
    except Exception:
        pass  # AI 检测失败时静默处理

    # 混合检测（标准模式）
    hybrid_report = await asyncio.to_thread(
        checker.check_text,
        description=request.description,
        product_category=request.category,
        target_market=request.market,
    )

    db_report = report_service.save_report(db, request.description, hybrid_report)

    return ComparisonCheckResponse(
        report_id=db_report.id,
        description=request.description,
        market=request.market,
        category=request.category,
        keyword_result=_report_to_comparison_result(keyword_report),
        ai_result=ai_report,
        hybrid_result=_report_to_comparison_result(hybrid_report),
        required_labels=hybrid_report.required_labels,
        required_certifications=hybrid_report.required_certifications,
        suggestions=hybrid_report.suggestions,
    )


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


_MARKET_NAMES = {
    "EU": "欧盟", "US": "美国",
    "SEA_SG": "新加坡", "SEA_TH": "泰国", "SEA_MY": "马来西亚",
}


@router.post("/check/multi-market", response_model=MultiMarketCheckResponse, summary="跨市场对比检测（Demo 模式）")
async def check_multi_market(request: CheckRequest, http_request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """同一商品描述在所有支持的市场中检测，返回各市场结果对比"""
    checker = _get_checker(http_request)
    checker.sync_ai_config_for_user(current_user.id, db)

    results = []
    for market in SUPPORTED_MARKETS:
        report = await asyncio.to_thread(
            checker.check_text,
            description=request.description,
            product_category=request.category,
            target_market=market,
        )
        results.append(MultiMarketResult(
            market=market,
            market_name=_MARKET_NAMES.get(market, market),
            risk_score=report.risk_score,
            risk_level=report.risk_level,
            risk_description=report.risk_description,
            violations=[ViolationItem(
                type=v.type.value if hasattr(v.type, 'value') else v.type,
                type_label=v.type_label,
                content=v.content,
                regulation=v.regulation,
                regulation_detail=v.regulation_detail,
                severity=v.severity.value if hasattr(v.severity, 'value') else v.severity,
                severity_label=v.severity_label,
                suggestion=v.suggestion,
                score=v.score,
            ) for v in report.violations],
            violation_count=len(report.violations),
            compliant_version=report.compliant_version,
            required_labels=report.required_labels,
            required_certifications=report.required_certifications,
            suggestions=report.suggestions,
        ))

    # 找出最优和最差市场
    sorted_results = sorted(results, key=lambda r: r.risk_score, reverse=True)
    best_market = sorted_results[-1].market if sorted_results else ""
    worst_market = sorted_results[0].market if sorted_results else ""

    return MultiMarketCheckResponse(
        description=request.description,
        category=request.category,
        results=results,
        best_market=best_market,
        worst_market=worst_market,
    )


@router.post("/check/llm-comparison", response_model=LLMComparisonResponse, summary="多 LLM 并排对比")
async def check_llm_comparison(request: LLMComparisonRequest, http_request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """用多个 LLM 提供商分析同一商品，返回各提供商检测结果对比"""
    checker = _get_checker(http_request)
    checker.sync_ai_config_for_user(current_user.id, db)

    results = []

    # 获取用户当前配置的 API Key（作为共享 key 尝试不同提供商）
    from ..services.llm_config_service import get_active_config_for_user
    user_llm_config = get_active_config_for_user(db, current_user.id)
    shared_api_key = user_llm_config["api_key"] if user_llm_config else ""

    for provider_id in request.providers:
        preset = PROVIDER_PRESETS.get(provider_id)
        if not preset:
            continue

        import time
        start = time.time()

        # 临时重配置 AI 检测器为指定提供商
        checker.update_ai_config(
            api_key=shared_api_key,
            api_base=preset["default_api_base"],
            model=preset["default_model"],
            max_tokens=2048,
            temperature=0.1,
        )

        report = await asyncio.to_thread(
            checker.check_text,
            description=request.description,
            product_category=request.category,
            target_market=request.market,
            check_mode="ai_only",
        )

        elapsed = int((time.time() - start) * 1000)

        results.append(LLMComparisonResult(
            provider=provider_id,
            provider_name=preset.get("name", provider_id),
            model=preset["default_model"],
            risk_score=report.risk_score,
            risk_level=report.risk_level,
            violations=[ViolationItem(
                type=v.type.value if hasattr(v.type, 'value') else v.type,
                type_label=v.type_label,
                content=v.content,
                regulation=v.regulation,
                regulation_detail=v.regulation_detail,
                severity=v.severity.value if hasattr(v.severity, 'value') else v.severity,
                severity_label=v.severity_label,
                suggestion=v.suggestion,
                score=v.score,
            ) for v in report.violations],
            violation_count=len(report.violations),
            latency_ms=elapsed if elapsed > 0 else None,
        ))

    # 恢复用户配置
    checker.sync_ai_config_for_user(current_user.id, db)

    return LLMComparisonResponse(
        description=request.description,
        category=request.category,
        market=request.market,
        results=results,
    )
