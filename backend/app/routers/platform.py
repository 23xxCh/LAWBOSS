"""电商平台对接 + 合规巡检 API 路由"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field

from ..services.platform_client import get_available_platforms, get_platform_client
from ..services.patrol_engine import PatrolEngine
from ..config import DATA_DIR
from ..models.user import User
from ..routers.auth import get_current_user, require_role

router = APIRouter(tags=["平台对接"])


class PatrolRequest(BaseModel):
    """巡检请求"""
    platform: str = Field(..., description="电商平台: amazon, shopee")
    market: str = Field(..., description="目标市场")
    category: Optional[str] = Field(default=None, description="产品类别筛选")
    limit: int = Field(default=50, ge=1, le=200, description="拉取数量上限")


class PatrolSummaryResponse(BaseModel):
    """巡检结果摘要"""
    id: str
    patrol_time: str
    platform: str
    market: str
    total_listings: int
    checked_listings: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    compliant_count: int
    alert_count: int


class PlatformStatusResponse(BaseModel):
    """平台连接状态"""
    platform: str
    status: str  # connected, not_configured


@router.get("/platforms", response_model=List[PlatformStatusResponse], summary="获取平台连接状态")
async def list_platforms(current_user: User = Depends(get_current_user)):
    """查看各电商平台 API 的配置和连接状态"""
    return get_available_platforms()


@router.post("/patrol", summary="触发合规巡检")
async def trigger_patrol(
    request: PatrolRequest,
    http_request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """
    手动触发一次合规巡检（需管理员权限）：
    1. 从电商平台拉取 Listing
    2. 逐条执行合规检测
    3. 高风险项生成告警
    4. 返回巡检结果
    """
    # 验证平台可用
    client = get_platform_client(request.platform)
    if not client:
        raise HTTPException(
            status_code=400,
            detail=f"平台 {request.platform} 未配置或不可用，请先配置 API 凭据",
        )

    # 获取巡检引擎
    checker = http_request.app.state.checker
    engine = PatrolEngine(checker=checker, data_dir=DATA_DIR)

    # 执行巡检
    result = await engine.run_patrol(
        platform=request.platform,
        market=request.market,
        category=request.category,
        limit=request.limit,
    )

    return {
        "id": result.id,
        "patrol_time": result.patrol_time,
        "platform": result.platform,
        "market": result.market,
        "total_listings": result.total_listings,
        "checked_listings": result.checked_listings,
        "high_risk_count": result.high_risk_count,
        "medium_risk_count": result.medium_risk_count,
        "low_risk_count": result.low_risk_count,
        "compliant_count": result.compliant_count,
        "alert_count": len(result.alerts),
        "alerts": result.alerts[:20],
        "top_risk_listings": sorted(result.details, key=lambda x: x["risk_score"], reverse=True)[:10],
    }


@router.get("/patrol/history", response_model=List[PatrolSummaryResponse], summary="巡检历史")
async def patrol_history(
    platform: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    http_request: Request = None,
    current_user: User = Depends(get_current_user),
):
    """查询巡检历史记录"""
    checker = http_request.app.state.checker
    engine = PatrolEngine(checker=checker, data_dir=DATA_DIR)
    return engine.get_patrol_history(platform=platform, limit=limit)
