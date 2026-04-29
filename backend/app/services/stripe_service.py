"""
Stripe 支付服务

功能:
- 创建 Checkout Session
- 管理 Stripe 客户
- Webhook 签名验证
- 订阅状态查询
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session

from ..models.user import User
from ..models.stripe_event import StripeEvent

logger = logging.getLogger(__name__)

# Stripe API 密钥配置
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")
STRIPE_ENTERPRISE_PRICE_ID = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "")

# 初始化 Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# 订阅层级配置
TIER_CONFIG = {
    "free": {
        "checks_monthly": 50,
        "markets": 1,
        "patrol_skus": 0,
        "api_calls": 0,
    },
    "pro": {
        "checks_monthly": 500,
        "markets": 5,
        "patrol_skus": 50,
        "api_calls": 500,
        "price_id": STRIPE_PRO_PRICE_ID,
    },
    "enterprise": {
        "checks_monthly": 2000,
        "markets": 5,
        "patrol_skus": 200,
        "api_calls": 2000,
        "price_id": STRIPE_ENTERPRISE_PRICE_ID,
    },
}


def get_tier_config(tier: str) -> Dict[str, Any]:
    """获取订阅层级配置"""
    return TIER_CONFIG.get(tier, TIER_CONFIG["free"])


def create_checkout_session(
    user: User,
    tier: str,
    success_url: str,
    cancel_url: str,
) -> Optional[str]:
    """
    创建 Stripe Checkout Session

    Args:
        user: 用户对象
        tier: 订阅层级 (pro, enterprise)
        success_url: 支付成功后跳转 URL
        cancel_url: 取消支付后跳转 URL

    Returns:
        Checkout Session URL 或 None
    """
    if not STRIPE_SECRET_KEY:
        logger.warning("Stripe API key not configured")
        return None

    config = TIER_CONFIG.get(tier)
    if not config or not config.get("price_id"):
        logger.error(f"Invalid tier or missing price_id: {tier}")
        return None

    try:
        # 创建或获取 Stripe 客户
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": user.id},
            )
            customer_id = customer.id

        # 创建 Checkout Session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{
                "price": config["price_id"],
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user.id,
                "tier": tier,
            },
        )

        return session.url

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        return None


def verify_webhook_signature(payload: bytes, sig_header: str) -> Optional[stripe.Event]:
    """
    验证 Webhook 签名并解析事件

    Args:
        payload: 请求体原始字节
        sig_header: Stripe-Signature 头

    Returns:
        stripe.Event 对象或 None
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured")
        return None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Webhook parsing error: {e}")
        return None


def is_event_processed(db: Session, event_id: str) -> bool:
    """检查事件是否已处理"""
    existing = db.query(StripeEvent).filter(StripeEvent.id == event_id).first()
    return existing is not None


def record_event(
    db: Session,
    event_id: str,
    event_type: str,
    customer_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
) -> StripeEvent:
    """记录已处理事件"""
    record = StripeEvent(
        id=event_id,
        event_type=event_type,
        customer_id=customer_id,
        subscription_id=subscription_id,
    )
    db.add(record)
    db.commit()
    return record


def handle_checkout_completed(db: Session, event: stripe.Event) -> bool:
    """
    处理 checkout.session.completed 事件

    激活用户订阅
    """
    session = event.data.object
    user_id = session.get("metadata", {}).get("user_id")
    tier = session.get("metadata", {}).get("tier", "pro")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not user_id:
        logger.error("No user_id in checkout session metadata")
        return False

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"User not found: {user_id}")
        return False

    # 更新用户订阅状态
    user.stripe_customer_id = customer_id
    user.subscription_status = "active"
    user.subscription_tier = tier
    user.quota_checks_monthly = TIER_CONFIG[tier]["checks_monthly"]

    db.commit()

    # 记录事件
    record_event(db, event.id, event.type, customer_id, subscription_id)

    logger.info(f"Subscription activated for user {user_id}: {tier}")
    return True


def handle_invoice_paid(db: Session, event: stripe.Event) -> bool:
    """
    处理 invoice.paid 事件

    续费成功
    """
    invoice = event.data.object
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")

    if not customer_id:
        return False

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return False

    # 确保 active 状态
    if user.subscription_status != "active":
        user.subscription_status = "active"
        db.commit()

    record_event(db, event.id, event.type, customer_id, subscription_id)
    return True


def handle_payment_failed(db: Session, event: stripe.Event) -> bool:
    """
    处理 invoice.payment_failed 事件

    支付失败，更新状态
    """
    invoice = event.data.object
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")

    if not customer_id:
        return False

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return False

    user.subscription_status = "past_due"
    db.commit()

    record_event(db, event.id, event.type, customer_id, subscription_id)

    logger.warning(f"Payment failed for user {user.id}")
    return True


def handle_subscription_deleted(db: Session, event: stripe.Event) -> bool:
    """
    处理 customer.subscription.deleted 事件

    订阅取消，降级为免费版
    """
    subscription = event.data.object
    customer_id = subscription.get("customer")

    if not customer_id:
        return False

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return False

    user.subscription_status = "canceled"
    user.subscription_tier = "free"
    user.quota_checks_monthly = TIER_CONFIG["free"]["checks_monthly"]
    db.commit()

    record_event(db, event.id, event.type, customer_id, subscription.id)

    logger.info(f"Subscription canceled for user {user.id}")
    return True


def start_trial(user: User, db: Session, days: int = 14) -> bool:
    """
    开始试用期

    Args:
        user: 用户对象
        db: 数据库会话
        days: 试用天数

    Returns:
        是否成功
    """
    from datetime import timedelta

    user.subscription_status = "trialing"
    user.subscription_tier = "pro"
    user.trial_ends_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
    user.quota_checks_monthly = TIER_CONFIG["pro"]["checks_monthly"]
    db.commit()

    logger.info(f"Trial started for user {user.id}, ends at {user.trial_ends_at}")
    return True


def check_and_expire_trial(user: User, db: Session) -> bool:
    """
    检查并过期试用期

    Returns:
        是否已过期
    """
    if user.subscription_status != "trialing":
        return False

    if not user.trial_ends_at:
        return False

    if datetime.now(timezone.utc).replace(tzinfo=None) > user.trial_ends_at:
        user.subscription_status = "free"
        user.subscription_tier = "free"
        user.trial_ends_at = None
        user.quota_checks_monthly = TIER_CONFIG["free"]["checks_monthly"]
        db.commit()
        logger.info(f"Trial expired for user {user.id}")
        return True

    return False
