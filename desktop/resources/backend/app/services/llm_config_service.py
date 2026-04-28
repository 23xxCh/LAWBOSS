"""LLM 配置业务逻辑 — CRUD + 连接测试 + 提供商预设"""
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..models.llm_config import UserLLMConfig
from ..schemas.llm_config import (
    LLMProviderInfo,
    LLMConfigCreate,
    LLMConfigUpdate,
    LLMConfigResponse,
    LLMTestRequest,
    LLMTestResponse,
)
from ..utils.encryption import encrypt_api_key, decrypt_api_key, mask_api_key

logger = logging.getLogger(__name__)

# ===== 提供商预设 =====

PROVIDER_PRESETS: Dict[str, dict] = {
    "openai": {
        "name": "OpenAI",
        "default_api_base": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "requires_api_key": True,
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_api_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "requires_api_key": True,
    },
    "kimi": {
        "name": "Kimi / Moonshot",
        "default_api_base": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "requires_api_key": True,
    },
    "glm": {
        "name": "GLM / Zhipu",
        "default_api_base": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4",
        "models": ["glm-4", "glm-4v", "glm-3-turbo"],
        "requires_api_key": True,
    },
    "ollama": {
        "name": "Ollama (Local)",
        "default_api_base": "http://localhost:11434/v1",
        "default_model": "llama3",
        "models": ["llama3", "llama3:70b", "mistral", "qwen2.5"],
        "requires_api_key": False,
    },
    "custom": {
        "name": "Custom",
        "default_api_base": "",
        "default_model": "",
        "models": [],
        "requires_api_key": True,
    },
}


def get_providers() -> List[LLMProviderInfo]:
    """返回所有支持的提供商列表"""
    return [
        LLMProviderInfo(id=pid, **preset)
        for pid, preset in PROVIDER_PRESETS.items()
    ]


def get_config(db: Session, user_id: str) -> Optional[UserLLMConfig]:
    """获取用户 LLM 配置"""
    return db.query(UserLLMConfig).filter(
        UserLLMConfig.user_id == user_id,
        UserLLMConfig.is_active == True,
    ).first()


def get_config_response(db: Session, user_id: str) -> Optional[LLMConfigResponse]:
    """获取 LLM 配置响应（API Key 已掩码）"""
    config = get_config(db, user_id)
    if not config:
        return None
    return LLMConfigResponse(
        provider=config.provider,
        api_key_masked=mask_api_key(decrypt_api_key(config.api_key_encrypted)),
        api_base=config.api_base,
        model=config.model,
        max_tokens=config.max_tokens,
        temperature=config.temperature,
        is_active=config.is_active,
        updated_at=config.updated_at,
    )


def save_config(db: Session, user_id: str, data: LLMConfigCreate) -> LLMConfigResponse:
    """创建或更新 LLM 配置（upsert）"""
    existing = db.query(UserLLMConfig).filter(UserLLMConfig.user_id == user_id).first()

    if existing:
        existing.provider = data.provider
        if data.api_key:
            existing.api_key_encrypted = encrypt_api_key(data.api_key)
        existing.api_base = data.api_base
        existing.model = data.model
        existing.max_tokens = data.max_tokens
        existing.temperature = data.temperature
        existing.updated_at = datetime.now(timezone.utc)
    else:
        encrypted = encrypt_api_key(data.api_key)
        existing = UserLLMConfig(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=data.provider,
            api_key_encrypted=encrypted,
            api_base=data.api_base,
            model=data.model,
            max_tokens=data.max_tokens,
            temperature=data.temperature,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)

    return LLMConfigResponse(
        provider=existing.provider,
        api_key_masked=mask_api_key(data.api_key or decrypt_api_key(existing.api_key_encrypted)),
        api_base=existing.api_base,
        model=existing.model,
        max_tokens=existing.max_tokens,
        temperature=existing.temperature,
        is_active=existing.is_active,
        updated_at=existing.updated_at,
    )


def update_config(db: Session, user_id: str, data: LLMConfigUpdate) -> Optional[LLMConfigResponse]:
    """部分更新 LLM 配置"""
    existing = get_config(db, user_id)
    if not existing:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if "api_key" in update_data:
        if update_data["api_key"]:
            existing.api_key_encrypted = encrypt_api_key(update_data["api_key"])
        del update_data["api_key"]

    for field, value in update_data.items():
        setattr(existing, field, value)

    existing.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(existing)

    return LLMConfigResponse(
        provider=existing.provider,
        api_key_masked=mask_api_key(decrypt_api_key(existing.api_key_encrypted)),
        api_base=existing.api_base,
        model=existing.model,
        max_tokens=existing.max_tokens,
        temperature=existing.temperature,
        is_active=existing.is_active,
        updated_at=existing.updated_at,
    )


def delete_config(db: Session, user_id: str) -> bool:
    """删除用户 LLM 配置"""
    existing = db.query(UserLLMConfig).filter(UserLLMConfig.user_id == user_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        return True
    return False


def get_active_config_for_user(db: Session, user_id: str) -> Optional[dict]:
    """获取解密后的活跃配置（供运行时的 AISemanticChecker 使用）"""
    config = get_config(db, user_id)
    if not config:
        return None
    return {
        "api_key": decrypt_api_key(config.api_key_encrypted),
        "api_base": config.api_base,
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "provider": config.provider,
    }


def test_connection(request: LLMTestRequest) -> LLMTestResponse:
    """测试 LLM 连接 — 发送最小 prompt 验证连通性"""
    if not request.api_key and PROVIDER_PRESETS.get(request.provider, {}).get("requires_api_key", True):
        return LLMTestResponse(success=False, message="API Key 不能为空")

    try:
        import httpx
    except ImportError:
        return LLMTestResponse(success=False, message="httpx 未安装")

    headers = {"Content-Type": "application/json"}
    if request.api_key:
        headers["Authorization"] = f"Bearer {request.api_key}"

    payload = {
        "model": request.model,
        "messages": [
            {"role": "system", "content": "你是一个助手。"},
            {"role": "user", "content": "回复仅包含 OK 一词。"},
        ],
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
    }

    try:
        start = time.monotonic()
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{request.api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
        elapsed = int((time.monotonic() - start) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            model_info = data.get("model", request.model)
            return LLMTestResponse(
                success=True,
                message="连接成功",
                latency_ms=elapsed,
                model_info=model_info,
            )
        else:
            detail = resp.text[:200]
            return LLMTestResponse(
                success=False,
                message=f"API 返回错误 (HTTP {resp.status_code}): {detail}",
                latency_ms=elapsed,
            )
    except httpx.ConnectError:
        return LLMTestResponse(success=False, message=f"无法连接到 {request.api_base}")
    except httpx.TimeoutException:
        return LLMTestResponse(success=False, message="连接超时（15秒）")
    except Exception as e:
        return LLMTestResponse(success=False, message=f"连接异常: {str(e)[:200]}")
