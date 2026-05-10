"""
MCP HTTP API — 为 MCP HTTP 服务器提供认证和配额服务

端点:
- GET /mcp/auth/verify — 验证 API Key/Token
- POST /mcp/quota/check — 检查配额
- POST /mcp/quota/increment — 增加使用量
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.user import User
from ..services import auth_service
from ..services.quota_service import check_and_increment_quota, get_current_usage, decrement_quota
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["MCP服务"])


class QuotaCheckRequest(BaseModel):
    quota_type: str  # checks, api


class QuotaCheckResponse(BaseModel):
    allowed: bool
    current: int
    limit: int


class QuotaIncrementResponse(BaseModel):
    success: bool
    current: int


class VerifyResponse(BaseModel):
    valid: bool
    user_id: str
    username: str
    role: str
    subscription_tier: str
    quota_checks_monthly: int


async def verify_mcp_auth(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    """
    验证 MCP 请求的认证

    支持两种认证方式:
    1. Bearer Token (JWT)
    2. ApiKey (API Key)
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少认证凭据")

    # 解析认证类型
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401, detail="无效的认证格式")

    auth_type, credential = parts
    auth_type = auth_type.lower()

    if auth_type == "bearer":
        # JWT Token 认证
        token_data = auth_service.decode_access_token(credential)
        if not token_data:
            raise HTTPException(status_code=401, detail="无效或过期的 Token")

        user = db.query(User).filter(User.username == token_data.username).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="用户不存在或已禁用")

        return user

    elif auth_type == "apikey":
        # API Key 认证 (暂不支持，后续可扩展)
        raise HTTPException(status_code=401, detail="API Key 认证暂未实现")

    else:
        raise HTTPException(status_code=401, detail=f"不支持的认证类型: {auth_type}")


@router.get("/auth/verify", response_model=VerifyResponse, summary="验证认证凭据")
async def verify_auth(user: User = Depends(verify_mcp_auth)):
    """
    验证 API Key/Token

    MCP HTTP 服务器调用此端点验证用户的认证凭据。
    返回用户信息和配额限制。
    """
    return VerifyResponse(
        valid=True,
        user_id=user.id,
        username=user.username,
        role=user.role,
        subscription_tier=user.subscription_tier or "free",
        quota_checks_monthly=user.quota_checks_monthly or 50,
    )


@router.post("/quota/check", response_model=QuotaCheckResponse, summary="检查配额")
async def check_quota(
    request: QuotaCheckRequest,
    user: User = Depends(verify_mcp_auth),
):
    """
    检查配额是否足够

    原子操作，不会增加计数。
    返回当前使用量和配额上限。
    """
    limit = user.quota_checks_monthly or 50
    if request.quota_type == "api":
        limit = user.quota_api_monthly or 0

    current = get_current_usage(user.id, request.quota_type)

    return QuotaCheckResponse(
        allowed=current < limit,
        current=current,
        limit=limit,
    )


@router.post("/quota/increment", response_model=QuotaIncrementResponse, summary="增加使用量")
async def increment_quota(
    request: QuotaCheckRequest,
    user: User = Depends(verify_mcp_auth),
):
    """
    增加配额使用量

    原子操作，如果超限会自动回滚。
    """
    limit = user.quota_checks_monthly or 50
    if request.quota_type == "api":
        limit = user.quota_api_monthly or 0

    allowed, current = check_and_increment_quota(
        user.id,
        request.quota_type,
        limit,
    )

    return QuotaIncrementResponse(
        success=allowed,
        current=current,
    )


@router.post("/quota/decrement", summary="回滚使用量")
async def rollback_quota(
    request: QuotaCheckRequest,
    user: User = Depends(verify_mcp_auth),
):
    """
    回滚配额使用量

    用于检测失败时恢复配额。
    """
    success = decrement_quota(user.id, request.quota_type)

    return {"success": success}
