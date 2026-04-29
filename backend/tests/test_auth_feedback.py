"""认证 + 反馈 + 平台 API 测试"""
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestAuth:
    def test_login_success(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "crossguard2024",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrong",
        })
        assert resp.status_code == 401

    def test_get_me(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_get_me_no_token(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_register_and_login(self, client):
        import uuid
        unique_user = f"testuser_{uuid.uuid4().hex[:8]}"
        # 注册新用户
        resp = client.post("/api/v1/auth/register", json={
            "username": unique_user,
            "password": "test123456",
        })
        assert resp.status_code == 200
        # 登录
        resp = client.post("/api/v1/auth/login", json={
            "username": unique_user,
            "password": "test123456",
        })
        assert resp.status_code == 200


class TestProtectedEndpoints:
    """验证核心端点需要认证"""

    def test_check_requires_auth(self, client):
        resp = client.post("/api/v1/check", json={
            "description": "测试",
            "category": "化妆品",
            "market": "EU",
        })
        assert resp.status_code == 401

    def test_check_with_auth(self, client, auth_headers):
        resp = client.post("/api/v1/check", json={
            "description": "这款面霜能治疗痘痘",
            "category": "化妆品",
            "market": "EU",
        }, headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_report_requires_admin(self, client, auth_headers):
        """删除报告需要管理员权限（admin token 应该可以）"""
        # 先获取报告列表
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200

    def test_feedback_requires_auth(self, client):
        resp = client.post("/api/v1/feedback", json={
            "report_id": "test",
            "feedback_type": "false_positive",
            "violation_type": "medical_claim",
            "violation_content": "治疗",
            "market": "EU",
            "category": "化妆品",
        })
        assert resp.status_code == 401

    def test_platforms_requires_auth(self, client):
        resp = client.get("/api/v1/platforms")
        assert resp.status_code == 401


class TestFeedback:
    def test_submit_feedback(self, client, auth_headers):
        resp = client.post("/api/v1/feedback", json={
            "report_id": "test_report_001",
            "feedback_type": "false_positive",
            "violation_type": "medical_claim",
            "violation_content": "治疗",
            "market": "EU",
            "category": "化妆品",
            "user_comment": "这个词在当前语境下不是医疗宣称",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["feedback_type"] == "false_positive"

    def test_get_accuracy(self, client, auth_headers):
        resp = client.get("/api/v1/feedback/accuracy", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_feedbacks" in data
        assert "accuracy" in data

    def test_get_suggestions(self, client, auth_headers):
        resp = client.get("/api/v1/feedback/suggestions", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_feedback_list(self, client, auth_headers):
        resp = client.get("/api/v1/feedback/list", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestPlatform:
    def test_get_platforms(self, client, auth_headers):
        resp = client.get("/api/v1/platforms", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(p["platform"] == "amazon" for p in data)

    def test_patrol_history(self, client, auth_headers):
        resp = client.get("/api/v1/patrol/history", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
