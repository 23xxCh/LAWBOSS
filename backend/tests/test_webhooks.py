"""
Stripe Webhook 测试

测试场景:
1. 签名验证
2. checkout.session.completed 处理
3. invoice.payment_failed 处理
4. 幂等处理
"""
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def create_mock_event(event_type: str, event_id: str = "evt_test123") -> dict:
    """创建模拟 Stripe 事件"""
    return {
        "id": event_id,
        "type": event_type,
        "data": {
            "object": {
                "id": "cs_test123",
                "customer": "cus_test123",
                "subscription": "sub_test123",
                "metadata": {
                    "user_id": "admin",
                    "tier": "pro",
                },
            }
        },
    }


class TestWebhookSignature:
    """Webhook 签名验证测试"""

    @patch("app.routers.webhooks.stripe_service.verify_webhook_signature")
    def test_invalid_signature(self, mock_verify, client):
        """无效签名返回 400"""
        mock_verify.return_value = None

        resp = client.post(
            "/webhooks/stripe",
            content=b'{"id": "evt_test"}',
            headers={"stripe-signature": "invalid"},
        )

        assert resp.status_code == 400

    @patch("app.routers.webhooks.stripe_service.verify_webhook_signature")
    @patch("app.routers.webhooks.stripe_service.is_event_processed")
    @patch("app.services.stripe_service.handle_checkout_completed")
    def test_checkout_completed(
        self, mock_handle, mock_processed, mock_verify, client
    ):
        """处理 checkout.session.completed"""
        mock_verify.return_value = MagicMock(
            id="evt_test123",
            type="checkout.session.completed",
            data=MagicMock(object={
                "customer": "cus_test123",
                "subscription": "sub_test123",
                "metadata": {"user_id": "admin", "tier": "pro"},
            }),
        )
        mock_processed.return_value = False
        mock_handle.return_value = True

        resp = client.post(
            "/webhooks/stripe",
            content=b'{"id": "evt_test123", "type": "checkout.session.completed"}',
            headers={"stripe-signature": "valid"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    @patch("app.routers.webhooks.stripe_service.verify_webhook_signature")
    @patch("app.routers.webhooks.stripe_service.is_event_processed")
    def test_already_processed(self, mock_processed, mock_verify, client):
        """重复事件返回 already_processed"""
        mock_verify.return_value = MagicMock(
            id="evt_test123",
            type="checkout.session.completed",
        )
        mock_processed.return_value = True

        resp = client.post(
            "/webhooks/stripe",
            content=b'{"id": "evt_test123"}',
            headers={"stripe-signature": "valid"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "already_processed"

    @patch("app.routers.webhooks.stripe_service.verify_webhook_signature")
    @patch("app.routers.webhooks.stripe_service.is_event_processed")
    @patch("app.routers.webhooks.stripe_service.record_event")
    def test_unhandled_event_type(
        self, mock_record, mock_processed, mock_verify, client
    ):
        """未知事件类型记录并返回 unhandled"""
        mock_verify.return_value = MagicMock(
            id="evt_test123",
            type="some.unknown.event",
        )
        mock_processed.return_value = False

        resp = client.post(
            "/webhooks/stripe",
            content=b'{"id": "evt_test123", "type": "some.unknown.event"}',
            headers={"stripe-signature": "valid"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "unhandled"


class TestPaymentFailed:
    """支付失败处理测试"""

    @patch("app.routers.webhooks.stripe_service.verify_webhook_signature")
    @patch("app.routers.webhooks.stripe_service.is_event_processed")
    @patch("app.services.stripe_service.handle_payment_failed")
    def test_payment_failed(
        self, mock_handle, mock_processed, mock_verify, client
    ):
        """处理 invoice.payment_failed"""
        mock_verify.return_value = MagicMock(
            id="evt_test123",
            type="invoice.payment_failed",
            data=MagicMock(object={
                "customer": "cus_test123",
                "subscription": "sub_test123",
            }),
        )
        mock_processed.return_value = False
        mock_handle.return_value = True

        resp = client.post(
            "/webhooks/stripe",
            content=b'{"id": "evt_test123", "type": "invoice.payment_failed"}',
            headers={"stripe-signature": "valid"},
        )

        assert resp.status_code == 200
