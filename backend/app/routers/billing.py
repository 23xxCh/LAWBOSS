"""
Billing API 路由

端点:
- POST /billing/checkout — 创建支付会话
- GET /billing/subscription — 获取订阅状态
- GET /billing/quota — 获取配额使用情况
- POST /billing/cancel — 取消订阅
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionInfo,
    QuotaResponse,
)
from ..services import stripe_service
from ..services.quota_service import get_current_usage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["支付"])


@router.post("/checkout", response_model=CheckoutResponse, summary="创建支付会话")
async def create_checkout(
    request: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    创建 Stripe Checkout Session

    用户将被重定向到 Stripe 托管页面完成支付
    """
    if request.tier not in ["pro", "enterprise"]:
        raise HTTPException(status_code=400, detail="无效的订阅层级")

    # 如果已有活跃订阅，不允许重复订阅
    if current_user.subscription_status == "active":
        raise HTTPException(status_code=400, detail="已有活跃订阅")

    checkout_url = stripe_service.create_checkout_session(
        user=current_user,
        tier=request.tier,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )

    if not checkout_url:
        raise HTTPException(status_code=500, detail="创建支付会话失败")

    return CheckoutResponse(checkout_url=checkout_url)


@router.get("/subscription", response_model=SubscriptionInfo, summary="获取订阅状态")
async def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的订阅状态和配额信息
    """
    # 检查试用是否过期
    stripe_service.check_and_expire_trial(current_user, db)

    # 获取已使用配额
    quota_used = get_current_usage(current_user.id, "checks")

    return SubscriptionInfo(
        status=current_user.subscription_status,
        tier=current_user.subscription_tier,
        trial_ends_at=current_user.trial_ends_at,
        quota_checks_monthly=current_user.quota_checks_monthly,
        quota_used=quota_used,
    )


@router.get("/quota", response_model=QuotaResponse, summary="获取配额使用情况")
async def get_quota(
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户的配额使用情况
    """
    tier_config = stripe_service.get_tier_config(current_user.subscription_tier)

    # 从 Redis 获取实际使用量
    checks_used = get_current_usage(current_user.id, "checks")
    api_calls_used = get_current_usage(current_user.id, "api")

    return QuotaResponse(
        checks_monthly=current_user.quota_checks_monthly,
        checks_used=checks_used,
        checks_remaining=max(0, current_user.quota_checks_monthly - checks_used),
        api_calls_monthly=tier_config.get("api_calls", 0),
        api_calls_used=api_calls_used,
    )


@router.post("/cancel", summary="取消订阅")
async def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    取消当前订阅

    订阅将在当前周期结束后取消
    """
    if current_user.subscription_status not in ["active", "trialing"]:
        raise HTTPException(status_code=400, detail="无活跃订阅")

    # 如果是试用期，直接取消
    if current_user.subscription_status == "trialing":
        current_user.subscription_status = "canceled"
        current_user.subscription_tier = "free"
        current_user.trial_ends_at = None
        current_user.quota_checks_monthly = stripe_service.TIER_CONFIG["free"]["checks_monthly"]
        db.commit()
        return {"status": "canceled", "message": "试用期已取消"}

    # TODO: 调用 Stripe API 取消订阅
    # stripe.Subscription.delete(current_user.stripe_subscription_id)

    return {"status": "pending", "message": "订阅将在周期结束后取消"}


@router.post("/trial", summary="开始试用")
async def start_trial(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    开始 14 天免费试用

    仅对新用户有效
    """
    if current_user.subscription_status != "free":
        raise HTTPException(status_code=400, detail="已有订阅或试用过")

    stripe_service.start_trial(current_user, db)

    return {
        "status": "trialing",
        "message": "试用已开始，有效期 14 天",
        "trial_ends_at": current_user.trial_ends_at,
    }
