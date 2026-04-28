"""报告查询响应模型"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .check import CheckResponse


class ReportItem(BaseModel):
    """报告列表项"""
    id: str = Field(..., description="报告ID")
    category: str = Field(..., description="产品类别")
    market: str = Field(..., description="目标市场")
    risk_score: int = Field(..., description="风险评分")
    risk_level: str = Field(..., description="风险等级")
    violation_count: int = Field(default=0, description="违规数量")
    created_at: datetime = Field(..., description="创建时间")


class ReportListResponse(BaseModel):
    """报告列表响应"""
    items: List[ReportItem] = Field(default_factory=list, description="报告列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")


class ReportDetailResponse(BaseModel):
    """报告详情响应"""
    id: str = Field(..., description="报告ID")
    description: str = Field(..., description="原始产品描述")
    result: CheckResponse = Field(..., description="检测结果")
    created_at: datetime = Field(..., description="创建时间")
