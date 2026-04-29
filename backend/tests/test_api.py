"""
API 集成测试
"""
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
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestRootEndpoint:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "出海法盾 - CrossGuard"


class TestCheckEndpoint:
    def test_check_compliance(self, client, auth_headers):
        resp = client.post("/api/v1/check", json={
            "description": "这款面霜能治疗痘痘，7天见效，是市面上最好的产品",
            "category": "化妆品",
            "market": "EU",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_score"] >= 70
        assert data["risk_level"] == "高风险"
        assert len(data["violations"]) >= 3

    def test_check_compliant_text(self, client, auth_headers):
        resp = client.post("/api/v1/check", json={
            "description": "这款面霜具有舒缓保湿功效，持续使用效果更佳",
            "category": "化妆品",
            "market": "EU",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # 缺失标签可能导致分数偏高，只检查非标签违规为0
        non_label = [v for v in data["violations"] if v["type"] != "missing_label"]
        assert len(non_label) == 0

    def test_check_invalid_market(self, client, auth_headers):
        resp = client.post("/api/v1/check", json={
            "description": "测试",
            "category": "化妆品",
            "market": "JP",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_check_invalid_category(self, client, auth_headers):
        resp = client.post("/api/v1/check", json={
            "description": "测试",
            "category": "武器",
            "market": "EU",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_check_us_market(self, client, auth_headers):
        resp = client.post("/api/v1/check", json={
            "description": "This cream treats acne, best product guaranteed",
            "category": "化妆品",
            "market": "US",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["violations"]) >= 2

    def test_check_no_false_positive(self, client, auth_headers):
        """误报测试：painting/restaurant/desktop 不应触发医疗/绝对化违规"""
        resp = client.post("/api/v1/check", json={
            "description": "This painting is beautiful, the restaurant is great, desktop computer",
            "category": "化妆品",
            "market": "EU",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        non_label_violations = [v for v in data["violations"] if v["type"] != "missing_label"]
        assert len(non_label_violations) == 0


class TestBatchCheckEndpoint:
    def test_batch_check(self, client, auth_headers):
        resp = client.post("/api/v1/check/batch", json={
            "items": [
                {"description": "治疗痘痘", "category": "化妆品", "market": "EU"},
                {"description": "舒缓保湿", "category": "化妆品", "market": "EU"},
            ]
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["high_risk_count"] >= 1


class TestMarketsEndpoint:
    def test_get_markets(self, client):
        resp = client.get("/api/v1/markets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        assert any(m["code"] == "EU" for m in data)
        assert any(m["code"] == "US" for m in data)

    def test_get_categories(self, client):
        resp = client.get("/api/v1/markets/EU/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1


class TestLabelsAndCertsEndpoint:
    def test_get_labels(self, client):
        resp = client.get("/api/v1/labels", params={"market": "EU", "category": "化妆品"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["labels"]) >= 1

    def test_get_certifications(self, client):
        resp = client.get("/api/v1/certifications", params={"market": "EU", "category": "化妆品"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["certifications"]) >= 1


class TestReportsEndpoint:
    def test_get_reports(self, client, auth_headers):
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
