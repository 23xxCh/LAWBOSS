"""
Billing API 请求/响应模型
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CheckoutRequest(BaseModel):
    """创建 Checkout Session 请求"""
    tier: str = Field(..., description="订阅层级: pro, enterprise")
    success_url: str = Field(..., description="支付成功跳转 URL")
    cancel_url: str = Field(..., description="取消支付跳转 URL")


class CheckoutResponse(BaseModel):
    """Checkout Session 响应"""
    checkout_url: str = Field(..., description="Stripe Checkout 页面 URL")


class SubscriptionInfo(BaseModel):
    """订阅信息"""
    status: str = Field(..., description="订阅状态: free, trialing, active, past_due, canceled")
    tier: str = Field(..., description="订阅层级: free, pro, enterprise")
    trial_ends_at: Optional[datetime] = Field(None, description="试用结束时间")
    quota_checks_monthly: int = Field(..., description="月度检测配额")
    quota_used: int = Field(0, description="已使用配额")


class QuotaResponse(BaseModel):
    """配额信息响应"""
    checks_monthly: int = Field(..., description="月度检测上限")
    checks_used: int = Field(..., description="已使用检测次数")
    checks_remaining: int = Field(..., description="剩余检测次数")
    api_calls_monthly: int = Field(0, description="月度 API 调用上限")
    api_calls_used: int = Field(0, description="已使用 API 调用次数")
