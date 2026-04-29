"""
配额限制服务测试

测试场景:
1. 配额检查 - 未超限
2. 配额检查 - 已超限
3. Redis 未启用时降级
4. 原子 INCR 竞态处理
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.services.quota_service import (
    check_and_increment_quota,
    get_current_usage,
    decrement_quota,
    QuotaExceeded,
)


class TestQuotaCheck:
    """配额检查测试"""

    @patch("app.services.quota_service.get_redis_client")
    def test_quota_allowed(self, mock_redis):
        """未超限时允许通过"""
        mock_client = MagicMock()
        mock_client.incr.return_value = 1
        mock_redis.return_value = mock_client

        allowed, count = check_and_increment_quota("user1", "checks", 50)

        assert allowed is True
        assert count == 1
        mock_client.incr.assert_called_once()

    @patch("app.services.quota_service.get_redis_client")
    def test_quota_exceeded(self, mock_redis):
        """超限时拒绝"""
        mock_client = MagicMock()
        mock_client.incr.return_value = 51  # 超过限制
        mock_client.decr.return_value = 50
        mock_redis.return_value = mock_client

        allowed, count = check_and_increment_quota("user1", "checks", 50)

        assert allowed is False
        assert count == 50
        mock_client.decr.assert_called_once()

    @patch("app.services.quota_service.get_redis_client")
    def test_redis_disabled_graceful_degradation(self, mock_redis):
        """Redis 未启用时允许通过"""
        mock_redis.return_value = None

        allowed, count = check_and_increment_quota("user1", "checks", 50)

        assert allowed is True
        assert count == 0

    @patch("app.services.quota_service.get_redis_client")
    def test_redis_error_graceful_degradation(self, mock_redis):
        """Redis 错误时允许通过"""
        from redis import RedisError

        mock_client = MagicMock()
        mock_client.incr.side_effect = RedisError("Connection refused")
        mock_redis.return_value = mock_client

        allowed, count = check_and_increment_quota("user1", "checks", 50)

        assert allowed is True
        assert count == 0


class TestQuotaUsage:
    """配额使用查询测试"""

    @patch("app.services.quota_service.get_redis_client")
    def test_get_current_usage(self, mock_redis):
        """获取当前使用量"""
        mock_client = MagicMock()
        mock_client.get.return_value = b"25"
        mock_redis.return_value = mock_client

        usage = get_current_usage("user1", "checks")

        assert usage == 25

    @patch("app.services.quota_service.get_redis_client")
    def test_get_current_usage_zero(self, mock_redis):
        """未使用时返回 0"""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        usage = get_current_usage("user1", "checks")

        assert usage == 0


class TestQuotaDecrement:
    """配额回滚测试"""

    @patch("app.services.quota_service.get_redis_client")
    def test_decrement_success(self, mock_redis):
        """回滚成功"""
        mock_client = MagicMock()
        mock_client.get.return_value = b"25"
        mock_client.decr.return_value = 24
        mock_redis.return_value = mock_client

        result = decrement_quota("user1", "checks")

        assert result is True

    @patch("app.services.quota_service.get_redis_client")
    def test_decrement_zero(self, mock_redis):
        """使用量为 0 时不回滚"""
        mock_client = MagicMock()
        mock_client.get.return_value = b"0"
        mock_redis.return_value = mock_client

        result = decrement_quota("user1", "checks")

        assert result is False


class TestQuotaExceeded:
    """QuotaExceeded 异常测试"""

    def test_exception_message(self):
        """异常消息正确"""
        exc = QuotaExceeded("checks", 50, 51)

        assert exc.quota_type == "checks"
        assert exc.limit == 50
        assert exc.current == 51
        assert "Quota exceeded" in str(exc)
