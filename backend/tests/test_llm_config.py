"""测试 LLM 配置 — 加密 / CRUD / 热重载 / Provider 预设"""
import pytest
from unittest.mock import patch, MagicMock

from app.utils.encryption import encrypt_api_key, decrypt_api_key, mask_api_key


class TestEncryption:
    """加密工具测试"""

    def test_encrypt_decrypt_roundtrip(self):
        plain = "sk-test1234567890abcdef"
        encrypted = encrypt_api_key(plain)
        assert encrypted != plain
        assert decrypt_api_key(encrypted) == plain

    def test_encrypt_empty(self):
        assert encrypt_api_key("") == ""

    def test_decrypt_empty(self):
        assert decrypt_api_key("") == ""

    def test_decrypt_corrupted(self):
        assert decrypt_api_key("invalid!data") == ""

    def test_mask_api_key(self):
        assert mask_api_key("sk-test1234567890abcdef") == "****cdef"
        assert mask_api_key("short") == "****"
        assert mask_api_key("") == ""


class TestLLMConfigAPI:
    """LLM 配置 API 端点测试"""

    def test_list_providers(self, client):
        resp = client.get("/api/v1/llm/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        provider_ids = [p["id"] for p in data]
        assert "openai" in provider_ids
        assert "deepseek" in provider_ids
        assert "kimi" in provider_ids
        assert "glm" in provider_ids
        assert "ollama" in provider_ids
        assert "custom" in provider_ids

    def test_get_config_requires_auth(self, client):
        resp = client.get("/api/v1/llm/config")
        assert resp.status_code == 401

    def test_save_config_requires_auth(self, client):
        resp = client.put("/api/v1/llm/config", json={
            "provider": "deepseek",
            "api_key": "sk-test",
            "api_base": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
        })
        assert resp.status_code == 401

    def test_delete_config_requires_auth(self, client):
        resp = client.delete("/api/v1/llm/config")
        assert resp.status_code == 401

    def test_test_connection_not_found_endpoint(self, client):
        resp = client.post("/api/v1/llm/test", json={
            "provider": "openai",
            "api_key": "",
            "api_base": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
        })
        # Should return 200 (the request is valid, just connection fails)
        assert resp.status_code in (200, 422)

    def test_providers_have_defaults(self, client):
        resp = client.get("/api/v1/llm/providers")
        data = resp.json()
        for p in data:
            assert "name" in p
            assert "default_api_base" in p or p["id"] == "custom"
            assert "models" in p
            assert "requires_api_key" in p

    @patch("app.services.llm_config_service.httpx.Client")
    def test_test_connection_success(self, mock_client, client, auth_headers):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "gpt-4o-mini",
            "choices": [{"message": {"content": "OK"}}],
        }
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        resp = client.post("/api/v1/llm/test", json={
            "provider": "openai",
            "api_key": "sk-test",
            "api_base": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestLLMConfigAuthFlow:
    """认证用户 LLM 配置 CRUD 流程测试"""

    def test_save_and_get_config(self, client, auth_headers):
        # Save
        save_resp = client.put("/api/v1/llm/config", json={
            "provider": "deepseek",
            "api_key": "sk-test-key-12345",
            "api_base": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
        }, headers=auth_headers)
        assert save_resp.status_code == 200
        saved = save_resp.json()
        assert saved["provider"] == "deepseek"
        assert saved["api_key_masked"] == "****2345"
        assert saved["api_base"] == "https://api.deepseek.com/v1"
        assert saved["model"] == "deepseek-chat"

        # Get
        get_resp = client.get("/api/v1/llm/config", headers=auth_headers)
        assert get_resp.status_code == 200
        got = get_resp.json()
        assert got["provider"] == "deepseek"
        assert got["api_key_masked"] == "****2345"

    def test_delete_config(self, client, auth_headers):
        # Save first
        client.put("/api/v1/llm/config", json={
            "provider": "openai",
            "api_key": "sk-abc",
            "api_base": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
        }, headers=auth_headers)

        # Delete
        del_resp = client.delete("/api/v1/llm/config", headers=auth_headers)
        assert del_resp.status_code == 200

        # Get after delete -> 404
        get_resp = client.get("/api/v1/llm/config", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_config_saves_encrypted(self, client, auth_headers, db_session):
        """验证 DB 中存储的是密文而非明文"""
        from app.models.llm_config import UserLLMConfig

        client.put("/api/v1/llm/config", json={
            "provider": "openai",
            "api_key": "sk-plaintext-secret",
            "api_base": "https://api.openai.com/v1",
            "model": "gpt-4o",
        }, headers=auth_headers)

        config = db_session.query(UserLLMConfig).first()
        assert config is not None
        assert config.api_key_encrypted != "sk-plaintext-secret"
        assert config.api_key_encrypted != ""
