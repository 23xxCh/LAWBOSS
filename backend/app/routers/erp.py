"""
ERP 集成 API — 供店小秘、马帮等 ERP 系统嵌入调用

提供：
- API Key 认证（ERP 系统使用，区别于用户 JWT）
- 单品合规检测
- 批量合规检测
- Webhook 回调通知
- 检测结果查询
"""
import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel, Field

from ..services.compliance_checker import ComplianceChecker
from ..config import DATA_DIR
from ..models.user import User
from ..routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/erp", tags=["ERP集成"])


# ===== API Key 管理 =====

API_KEYS_FILE = DATA_DIR / "erp_api_keys.json"


def _load_api_keys() -> dict:
    if API_KEYS_FILE.exists():
        return json.loads(API_KEYS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_api_keys(data: dict):
    API_KEYS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


async def verify_erp_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """验证 ERP API Key"""
    keys = _load_api_keys()
    if x_api_key not in keys:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    key_info = keys[x_api_key]
    if not key_info.get("active", True):
        raise HTTPException(status_code=403, detail="API Key 已禁用")
    # 记录最后使用时间
    key_info["last_used"] = datetime.now(timezone.utc).isoformat()
    _save_api_keys(keys)
    return key_info


# ===== 请求/响应模型 =====

class ERPCheckRequest(BaseModel):
    """ERP 单品检测请求"""
    product_id: str = Field(..., description="ERP 系统中的商品ID")
    description: str = Field(..., description="商品描述文本")
    category: str = Field(default="化妆品", description="商品类别")
    market: str = Field(default="EU", description="目标市场: EU, US, SEA_SG, SEA_TH, SEA_MY")
    callback_url: Optional[str] = Field(default=None, description="检测完成后的回调URL")


class ERPBatchCheckRequest(BaseModel):
    """ERP 批量检测请求"""
    items: List[ERPCheckRequest] = Field(..., description="待检测商品列表", max_length=50)
    callback_url: Optional[str] = Field(default=None, description="批量检测完成后的回调URL")


class ERPCheckResponse(BaseModel):
    """ERP 检测响应"""
    task_id: str
    product_id: str
    status: str  # pending, completed, failed
    risk_level: str = "unknown"  # safe, low, medium, high, critical
    violations: List[dict] = []
    suggestions: List[str] = []
    checked_at: Optional[str] = None


class ERPBatchCheckResponse(BaseModel):
    """ERP 批量检测响应"""
    batch_id: str
    total: int
    status: str  # processing, completed
    results: List[ERPCheckResponse] = []


class ERPApiKeyCreate(BaseModel):
    """创建 API Key 请求"""
    erp_name: str = Field(..., description="ERP 系统名称，如：店小秘、马帮")
    contact: str = Field(default="", description="联系人")
    note: str = Field(default="", description="备注")


class ERPApiKeyResponse(BaseModel):
    api_key: str
    erp_name: str
    created_at: str


# ===== ERP 检测端点 =====

@router.post("/check", response_model=ERPCheckResponse, summary="ERP单品合规检测")
async def erp_check(request: ERPCheckRequest, key_info: dict = Depends(verify_erp_api_key)):
    """
    ERP 系统调用：对单个商品进行合规检测

    - 需要在 Header 中提供 X-API-Key
    - 支持异步回调（提供 callback_url 时，检测完成后 POST 回调）
    """
    task_id = str(uuid.uuid4())[:12]
    check_service = ComplianceChecker(data_dir=DATA_DIR)

    try:
        report = await asyncio.to_thread(
            check_service.check_text,
            description=request.description,
            product_category=request.category,
            target_market=request.market,
        )

        risk_level = "safe"
        if report.violations:
            max_score = max((v.get("risk_score", 0) for v in report.violations), default=0)
            if max_score >= 80:
                risk_level = "critical"
            elif max_score >= 60:
                risk_level = "high"
            elif max_score >= 40:
                risk_level = "medium"
            else:
                risk_level = "low"

        response = ERPCheckResponse(
            task_id=task_id,
            product_id=request.product_id,
            status="completed",
            risk_level=risk_level,
            violations=report.violations,
            suggestions=report.suggestions,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        logger.error(f"ERP检测失败: {e}")
        response = ERPCheckResponse(
            task_id=task_id,
            product_id=request.product_id,
            status="failed",
        )

    # 异步回调
    if request.callback_url:
        asyncio.create_task(_send_callback(request.callback_url, response.model_dump()))

    return response


@router.post("/batch", response_model=ERPBatchCheckResponse, summary="ERP批量合规检测")
async def erp_batch_check(request: ERPBatchCheckRequest, key_info: dict = Depends(verify_erp_api_key)):
    """
    ERP 系统调用：批量检测商品合规性（最多50个）

    - 需要在 Header 中提供 X-API-Key
    - 支持异步回调
    """
    batch_id = str(uuid.uuid4())[:12]
    check_service = ComplianceChecker(data_dir=DATA_DIR)
    results = []

    for item in request.items:
        task_id = str(uuid.uuid4())[:12]
        try:
            report = await asyncio.to_thread(
                check_service.check_text,
                description=item.description,
                product_category=item.category,
                target_market=item.market,
            )

            risk_level = "safe"
            if report.violations:
                max_score = max((v.get("risk_score", 0) for v in report.violations), default=0)
                if max_score >= 80:
                    risk_level = "critical"
                elif max_score >= 60:
                    risk_level = "high"
                elif max_score >= 40:
                    risk_level = "medium"
                else:
                    risk_level = "low"

            results.append(ERPCheckResponse(
                task_id=task_id,
                product_id=item.product_id,
                status="completed",
                risk_level=risk_level,
                violations=report.violations,
                suggestions=report.suggestions,
                checked_at=datetime.now(timezone.utc).isoformat(),
            ))
        except Exception as e:
            logger.error(f"ERP批量检测项失败: {e}")
            results.append(ERPCheckResponse(
                task_id=task_id,
                product_id=item.product_id,
                status="failed",
            ))

    response = ERPBatchCheckResponse(
        batch_id=batch_id,
        total=len(request.items),
        status="completed",
        results=results,
    )

    # 异步回调
    if request.callback_url:
        asyncio.create_task(_send_callback(request.callback_url, response.model_dump()))

    return response


# ===== API Key 管理端点 =====

@router.post("/api-keys", response_model=ERPApiKeyResponse, summary="创建ERP API Key")
async def create_api_key(request: ERPApiKeyCreate, current_user: User = Depends(get_current_user)):
    """管理员创建 ERP API Key（需登录）"""
    keys = _load_api_keys()
    api_key = f"cg_erp_{uuid.uuid4().hex[:24]}"
    keys[api_key] = {
        "erp_name": request.erp_name,
        "contact": request.contact,
        "note": request.note,
        "active": True,
        "created_by": current_user.username,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_api_keys(keys)
    return ERPApiKeyResponse(
        api_key=api_key,
        erp_name=request.erp_name,
        created_at=keys[api_key]["created_at"],
    )


@router.get("/api-keys", summary="列出ERP API Keys")
async def list_api_keys(current_user: User = Depends(get_current_user)):
    """管理员查看所有 ERP API Key"""
    keys = _load_api_keys()
    return [
        {
            "api_key": k[:12] + "..." + k[-4:],  # 脱敏显示
            "erp_name": v.get("erp_name", ""),
            "active": v.get("active", True),
            "created_at": v.get("created_at", ""),
            "last_used": v.get("last_used", ""),
        }
        for k, v in keys.items()
    ]


@router.delete("/api-keys/{api_key_prefix}", summary="禁用ERP API Key")
async def deactivate_api_key(api_key_prefix: str, current_user: User = Depends(get_current_user)):
    """管理员禁用 ERP API Key"""
    keys = _load_api_keys()
    for k in keys:
        if k.startswith(api_key_prefix):
            keys[k]["active"] = False
            _save_api_keys(keys)
            return {"message": "API Key 已禁用"}
    raise HTTPException(status_code=404, detail="API Key 不存在")


# ===== Webhook 回调 =====

async def _send_callback(url: str, payload: dict):
    """发送 Webhook 回调"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            logger.info(f"Webhook回调: {url} -> {resp.status_code}")
    except Exception as e:
        logger.error(f"Webhook回调失败: {url} - {e}")
