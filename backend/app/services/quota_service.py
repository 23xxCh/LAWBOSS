"""
配额限制服务

使用 Redis 原子操作实现配额检查:
- INCR 原子增加计数
- 超限回滚
- 月初自动重置
"""
import os
import logging
from datetime import datetime
from typing import Optional

import redis

logger = logging.getLogger(__name__)

# Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"

# Redis 客户端 (延迟初始化)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端 (单例)"""
    global _redis_client

    if not REDIS_ENABLED:
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(REDIS_URL)
            # 测试连接
            _redis_client.ping()
            logger.info(f"Redis connected: {REDIS_URL}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            _redis_client = None

    return _redis_client


def _get_month_key() -> str:
    """获取当前月份的 key 后缀 (YYYY-MM)"""
    return datetime.now().strftime("%Y-%m")


def _build_key(user_id: str, quota_type: str) -> str:
    """构建 Redis key"""
    month = _get_month_key()
    return f"user:{user_id}:{quota_type}:{month}"


def check_and_increment_quota(user_id: str, quota_type: str, limit: int) -> tuple[bool, int]:
    """
    检查配额并原子增加计数

    使用原子 INCR 操作避免竞态条件:
    1. INCR 增加计数
    2. 如果超限，DECR 回滚
    3. 返回是否允许和当前计数

    Args:
        user_id: 用户 ID
        quota_type: 配额类型 (checks, api)
        limit: 配额上限

    Returns:
        (是否允许, 当前计数)
    """
    client = get_redis_client()

    if client is None:
        # Redis 未启用，允许通过 (降级)
        logger.warning("Redis not available, quota check skipped")
        return True, 0

    key = _build_key(user_id, quota_type)

    try:
        # 原子增加计数
        count = client.incr(key)

        if count > limit:
            # 超限，回滚
            client.decr(key)
            logger.info(f"Quota exceeded for {user_id}/{quota_type}: {count}/{limit}")
            return False, count - 1

        # 设置过期时间 (60 天后过期)
        if count == 1:
            client.expire(key, 60 * 24 * 60 * 60)

        return True, count

    except redis.RedisError as e:
        logger.error(f"Redis error: {e}")
        # Redis 错误时允许通过 (降级)
        return True, 0


def get_current_usage(user_id: str, quota_type: str) -> int:
    """
    获取当前使用量

    Args:
        user_id: 用户 ID
        quota_type: 配额类型

    Returns:
        当前使用量
    """
    client = get_redis_client()

    if client is None:
        return 0

    key = _build_key(user_id, quota_type)

    try:
        count = client.get(key)
        return int(count) if count else 0
    except redis.RedisError:
        return 0


def reset_quota(user_id: str, quota_type: str) -> bool:
    """
    重置配额 (删除 key)

    Args:
        user_id: 用户 ID
        quota_type: 配额类型

    Returns:
        是否成功
    """
    client = get_redis_client()

    if client is None:
        return False

    key = _build_key(user_id, quota_type)

    try:
        client.delete(key)
        return True
    except redis.RedisError:
        return False


def decrement_quota(user_id: str, quota_type: str) -> bool:
    """
    减少配额计数 (用于回滚失败的检测)

    Args:
        user_id: 用户 ID
        quota_type: 配额类型

    Returns:
        是否成功
    """
    client = get_redis_client()

    if client is None:
        return False

    key = _build_key(user_id, quota_type)

    try:
        current = client.get(key)
        if current and int(current) > 0:
            client.decr(key)
            return True
        return False
    except redis.RedisError:
        return False


class QuotaExceeded(Exception):
    """配额超限异常"""
    def __init__(self, quota_type: str, limit: int, current: int):
        self.quota_type = quota_type
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded: {quota_type} ({current}/{limit})")
