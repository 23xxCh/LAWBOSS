"""数据看板统计 API 路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.dashboard import DashboardStatsResponse
from ..services import report_service

router = APIRouter(tags=["数据看板"])


@router.get("/dashboard/stats", response_model=DashboardStatsResponse, summary="获取看板统计数据")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """获取看板统计数据：周检测量、违规类型分布、风险趋势等"""
    return report_service.get_dashboard_stats(db)
