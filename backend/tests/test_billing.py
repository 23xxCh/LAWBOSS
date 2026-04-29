"""
Billing API 测试

测试场景:
1. 创建 Checkout Session
2. 获取订阅状态
3. 获取配额信息
4. 开始试用
"""
import sys
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


@pytest.fixture(scope="module")
def auth_token(client):
    """获取管理员 JWT Token"""
    resp = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "crossguard2024",
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestCheckout:
    """支付会话测试"""

    @patch("app.routers.billing.stripe_service.create_checkout_session")
    def test_create_checkout_pro(self, mock_create, client, auth_headers):
        """创建专业版支付会话"""
        mock_create.return_value = "https://checkout.stripe.com/session/xxx"

        resp = client.post(
            "/api/v1/billing/checkout",
            json={
                "tier": "pro",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert "checkout_url" in resp.json()

    def test_create_checkout_invalid_tier(self, client, auth_headers):
        """无效订阅层级"""
        resp = client.post(
            "/api/v1/billing/checkout",
            json={
                "tier": "invalid",
                "success_url": "https://example.com/success",
                "cancel_url": "https://example.com/cancel",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 400


class TestSubscription:
    """订阅状态测试"""

    def test_get_subscription(self, client, auth_headers):
        """获取订阅状态"""
        resp = client.get("/api/v1/billing/subscription", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "tier" in data
        assert "quota_checks_monthly" in data


class TestQuota:
    """配额测试"""

    def test_get_quota(self, client, auth_headers):
        """获取配额信息"""
        resp = client.get("/api/v1/billing/quota", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "checks_monthly" in data
        assert "checks_used" in data
        assert "checks_remaining" in data


class TestTrial:
    """试用测试"""

    def test_start_trial(self, client, auth_headers):
        """开始试用"""
        # 注意：这个测试可能因为用户已有订阅而失败
        resp = client.post("/api/v1/billing/trial", headers=auth_headers)

        # 可能成功或失败（已有订阅）
        assert resp.status_code in [200, 400]

        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "trialing"
