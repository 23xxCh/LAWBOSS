"""规则缓存服务

使用 Redis 缓存热点规则，提升检测性能。

缓存策略:
- 禁用词列表: 按市场+类别+违规类型缓存
- 替换建议: 全局缓存
- 缓存 TTL: 1 小时
- 规则变更时自动失效
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 导入 Redis 客户端
from .quota_service import get_redis_client

# 缓存 TTL (秒)
CACHE_TTL = 60 * 60  # 1 小时

# 缓存 key 前缀
CACHE_PREFIX = "cg:rules:"


def _cache_key(key: str) -> str:
    """构建缓存 key"""
    return f"{CACHE_PREFIX}{key}"


def get_banned_words_from_cache(
    market: str,
    category: str,
    violation_type: str
) -> Optional[List[str]]:
    """
    从缓存获取禁用词列表

    Args:
        market: 市场
        category: 产品类别
        violation_type: 违规类型

    Returns:
        禁用词列表，缓存未命中返回 None
    """
    client = get_redis_client()
    if client is None:
        return None

    key = _cache_key(f"bw:{market}:{category}:{violation_type}")

    try:
        cached = client.get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.error(f"Cache read error: {e}")
        return None


def set_banned_words_to_cache(
    market: str,
    category: str,
    violation_type: str,
    words: List[str]
) -> bool:
    """
    将禁用词列表写入缓存

    Args:
        market: 市场
        category: 产品类别
        violation_type: 违规类型
        words: 禁用词列表

    Returns:
        是否成功
    """
    client = get_redis_client()
    if client is None:
        return False

    key = _cache_key(f"bw:{market}:{category}:{violation_type}")

    try:
        client.setex(key, CACHE_TTL, json.dumps(words, ensure_ascii=False))
        return True
    except Exception as e:
        logger.error(f"Cache write error: {e}")
        return False


def get_replacements_from_cache(market: str, category: str) -> Optional[Dict[str, str]]:
    """
    从缓存获取替换建议

    Args:
        market: 市场
        category: 产品类别

    Returns:
        替换映射，缓存未命中返回 None
    """
    client = get_redis_client()
    if client is None:
        return None

    key = _cache_key(f"rp:{market}:{category}")

    try:
        cached = client.get(key)
        if cached:
            return json.loads(cached)
        return None
    except Exception as e:
        logger.error(f"Cache read error: {e}")
        return None


def set_replacements_to_cache(
    market: str,
    category: str,
    replacements: Dict[str, str]
) -> bool:
    """
    将替换建议写入缓存

    Args:
        market: 市场
        category: 产品类别
        replacements: 替换映射

    Returns:
        是否成功
    """
    client = get_redis_client()
    if client is None:
        return False

    key = _cache_key(f"rp:{market}:{category}")

    try:
        client.setex(key, CACHE_TTL, json.dumps(replacements, ensure_ascii=False))
        return True
    except Exception as e:
        logger.error(f"Cache write error: {e}")
        return False


def invalidate_banned_words_cache(
    market: str = None,
    category: str = None,
    violation_type: str = None
) -> int:
    """
    使禁用词缓存失效

    Args:
        market: 市场 (None 表示所有市场)
        category: 产品类别 (None 表示所有类别)
        violation_type: 违规类型 (None 表示所有类型)

    Returns:
        删除的 key 数量
    """
    client = get_redis_client()
    if client is None:
        return 0

    # 构建匹配模式
    if market and category and violation_type:
        pattern = _cache_key(f"bw:{market}:{category}:{violation_type}")
    elif market and category:
        pattern = _cache_key(f"bw:{market}:{category}:*")
    elif market:
        pattern = _cache_key(f"bw:{market}:*")
    else:
        pattern = _cache_key("bw:*")

    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        return 0


def invalidate_replacements_cache(market: str = None, category: str = None) -> int:
    """
    使替换建议缓存失效

    Args:
        market: 市场 (None 表示所有市场)
        category: 产品类别 (None 表示所有类别)

    Returns:
        删除的 key 数量
    """
    client = get_redis_client()
    if client is None:
        return 0

    if market and category:
        pattern = _cache_key(f"rp:{market}:{category}")
    elif market:
        pattern = _cache_key(f"rp:{market}:*")
    else:
        pattern = _cache_key("rp:*")

    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        return 0


def invalidate_all_rules_cache() -> int:
    """
    使所有规则缓存失效

    Returns:
        删除的 key 数量
    """
    client = get_redis_client()
    if client is None:
        return 0

    pattern = _cache_key("*")

    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        return 0


def get_cache_stats() -> Dict:
    """
    获取缓存统计信息

    Returns:
        缓存统计
    """
    client = get_redis_client()
    if client is None:
        return {"enabled": False, "keys": 0}

    try:
        bw_keys = len(client.keys(_cache_key("bw:*")))
        rp_keys = len(client.keys(_cache_key("rp:*")))
        return {
            "enabled": True,
            "banned_words_keys": bw_keys,
            "replacements_keys": rp_keys,
            "total_keys": bw_keys + rp_keys,
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {"enabled": False, "error": str(e)}
