"""LLM 配置 API 路由"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..routers.auth import get_current_user
from ..schemas.llm_config import (
    LLMProviderInfo,
    LLMConfigCreate,
    LLMConfigResponse,
    LLMTestRequest,
    LLMTestResponse,
    MessageResponse,
)
from ..services import llm_config_service

router = APIRouter(tags=["LLM 配置"])


@router.get("/llm/providers", response_model=List[LLMProviderInfo], summary="获取 LLM 提供商列表")
def list_providers():
    """返回所有支持的 LLM 提供商及默认参数"""
    return llm_config_service.get_providers()


@router.get("/llm/config", response_model=LLMConfigResponse, summary="获取当前用户的 LLM 配置")
def get_my_llm_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的 LLM 配置（API Key 已掩码）"""
    config = llm_config_service.get_config_response(db, current_user.id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置 LLM")
    return config


@router.put("/llm/config", response_model=LLMConfigResponse, summary="保存 LLM 配置")
def save_my_llm_config(
    data: LLMConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """创建或更新 LLM 配置，触发热重载"""
    result = llm_config_service.save_config(db, current_user.id, data)

    # 触发热重载：将用户配置推送到运行时的 AISemanticChecker
    _apply_llm_config(request, current_user.id, db)

    return result


@router.delete("/llm/config", response_model=MessageResponse, summary="删除 LLM 配置")
def delete_my_llm_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """删除用户 LLM 配置，恢复使用环境变量"""
    deleted = llm_config_service.delete_config(db, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置 LLM")
    return MessageResponse(message="LLM 配置已删除")


@router.post("/llm/test", response_model=LLMTestResponse, summary="测试 LLM 连接")
def test_llm_connection(test: LLMTestRequest):
    """测试与 LLM 提供商的连接（不要求先保存）"""
    return llm_config_service.test_connection(test)


def _apply_llm_config(request: Request, user_id: str, db: Session):
    """将用户 LLM 配置推送到运行时的 AISemanticChecker"""
    config = llm_config_service.get_active_config_for_user(db, user_id)
    if not config:
        return

    checker = getattr(request.app.state, "checker", None)
    if not checker:
        return

    checker.update_ai_config(
        api_key=config["api_key"],
        api_base=config["api_base"],
        model=config["model"],
        max_tokens=config["max_tokens"],
        temperature=config["temperature"],
    )
