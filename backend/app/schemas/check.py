"""合规检测请求/响应模型"""
from typing import List, Optional
from pydantic import BaseModel, Field


class CheckRequest(BaseModel):
    """合规检测请求"""
    description: str = Field(..., min_length=1, max_length=10000, description="产品描述")
    category: str = Field(..., description="产品类别")
    market: str = Field(default="EU", description="目标市场")


class ViolationItem(BaseModel):
    """违规项"""
    type: str = Field(..., description="违规类型标识")
    type_label: str = Field(..., description="违规类型中文名")
    content: str = Field(..., description="违规内容")
    regulation: str = Field(..., description="法规依据")
    regulation_detail: str = Field(..., description="法规详情")
    severity: str = Field(..., description="严重度: high/medium/low")
    severity_label: str = Field(..., description="严重度中文名")
    suggestion: str = Field(..., description="修改建议")
    score: int = Field(..., description="扣分")


class CheckResponse(BaseModel):
    """合规检测响应"""
    report_id: str = Field(default="", description="保存的报告ID")
    risk_score: int = Field(..., description="风险评分 0-100")
    risk_level: str = Field(..., description="风险等级")
    risk_description: str = Field(..., description="风险描述")
    market: str = Field(..., description="目标市场")
    category: str = Field(..., description="产品类别")
    violations: List[ViolationItem] = Field(default_factory=list, description="违规列表")
    compliant_version: str = Field(..., description="合规版本")
    required_labels: List[str] = Field(default_factory=list, description="必需标签")
    required_certifications: List[str] = Field(default_factory=list, description="必需认证")
    suggestions: List[str] = Field(default_factory=list, description="修改建议汇总")


class BatchCheckRequest(BaseModel):
    """批量检测请求"""
    items: List[CheckRequest] = Field(..., max_length=100, description="检测项列表")


class BatchCheckResponse(BaseModel):
    """批量检测响应"""
    results: List[CheckResponse] = Field(default_factory=list, description="检测结果列表")
    total: int = Field(..., description="总数")
    high_risk_count: int = Field(default=0, description="高风险数量")
    medium_risk_count: int = Field(default=0, description="中风险数量")
    low_risk_count: int = Field(default=0, description="低风险数量")
