"""
Stripe Webhook 路由

处理 Stripe 发送的 Webhook 事件:
- checkout.session.completed
- invoice.paid
- invoice.payment_failed
- customer.subscription.deleted
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..services import stripe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhook"])


# Webhook 事件处理器映射
EVENT_HANDLERS = {
    "checkout.session.completed": "handle_checkout_completed",
    "invoice.paid": "handle_invoice_paid",
    "invoice.payment_failed": "handle_payment_failed",
    "customer.subscription.deleted": "handle_subscription_deleted",
}


@router.post("/stripe", summary="Stripe Webhook 端点")
async def stripe_webhook(request: Request):
    """
    接收并处理 Stripe Webhook 事件

    签名验证确保请求来自 Stripe
    """
    # 获取原始请求体
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # 验证签名
    event = stripe_service.verify_webhook_signature(payload, sig_header)
    if not event:
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_id = event.id
    event_type = event.type

    logger.info(f"Received Stripe webhook: {event_type} ({event_id})")

    # 创建数据库会话
    db = SessionLocal()
    try:
        # 幂等检查：是否已处理
        if stripe_service.is_event_processed(db, event_id):
            logger.info(f"Event already processed: {event_id}")
            return {"status": "already_processed"}

        # 查找处理器
        handler_name = EVENT_HANDLERS.get(event_type)
        if handler_name:
            handler = getattr(stripe_service, handler_name)
            success = handler(db, event)
            if success:
                logger.info(f"Successfully handled: {event_type}")
                return {"status": "success"}
            else:
                logger.error(f"Failed to handle: {event_type}")
                return Response(content="Handler failed", status_code=500)
        else:
            # 未知事件类型，记录但返回成功
            logger.warning(f"Unhandled event type: {event_type}")
            # 记录事件以便追踪
            stripe_service.record_event(db, event_id, event_type)
            return {"status": "unhandled", "event_type": event_type}

    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        return Response(content="Internal error", status_code=500)
    finally:
        db.close()
