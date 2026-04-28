"""数据看板统计模型"""
from typing import List, Dict
from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    """看板统计响应"""
    weekly_volume: List[dict] = []
    violation_type_distribution: Dict[str, int] = {}
    risk_score_trend: List[dict] = []
    total_reports: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
