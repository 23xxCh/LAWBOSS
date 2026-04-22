"""通用响应模型"""
from typing import List
from pydantic import BaseModel, Field


class MarketResponse(BaseModel):
    """市场信息"""
    code: str = Field(..., description="市场代码")
    name: str = Field(..., description="市场名称")
    categories: List[str] = Field(default_factory=list, description="支持的产品类别")


class CategoryResponse(BaseModel):
    """产品类别信息"""
    name: str = Field(..., description="类别名称")
    market: str = Field(..., description="所属市场")


class LabelResponse(BaseModel):
    """标签要求响应"""
    market: str = Field(..., description="市场")
    category: str = Field(..., description="产品类别")
    labels: List[str] = Field(default_factory=list, description="必需标签列表")


class CertificationResponse(BaseModel):
    """认证要求响应"""
    market: str = Field(..., description="市场")
    category: str = Field(..., description="产品类别")
    certifications: List[str] = Field(default_factory=list, description="必需认证列表")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="消息内容")
