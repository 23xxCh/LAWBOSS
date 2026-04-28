"""法规更新监控 API 路由"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from ..models.user import User
from ..routers.auth import get_current_user, require_role
from ..services.regulation_monitor import RegulationMonitor
from ..config import DATA_DIR
from ..config import PATROL_WEBHOOK_URL

router = APIRouter(tags=["法规监控"])

_webhook = PATROL_WEBHOOK_URL if 'PATROL_WEBHOOK_URL' in dir() else None


def _get_monitor() -> RegulationMonitor:
    return RegulationMonitor(DATA_DIR, webhook_url=_webhook)


@router.get("/regulation/sources", summary="获取法规监控源列表")
async def get_regulation_sources(current_user: User = Depends(get_current_user)):
    """获取所有法规数据源配置"""
    monitor = _get_monitor()
    return {"sources": monitor.get_sources(), "last_check": monitor.get_last_check_times()}


@router.get("/regulation/updates", summary="获取法规更新列表")
async def get_regulation_updates(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """获取待处理的法规更新"""
    monitor = _get_monitor()
    return {"updates": monitor.get_pending_updates(limit=limit)}


@router.post("/regulation/check", summary="手动触发法规更新检查")
async def trigger_regulation_check(current_user: User = Depends(require_role("admin"))):
    """管理员手动触发法规更新检查"""
    monitor = _get_monitor()
    updates = await monitor.check_all_sources()
    return {"checked": True, "new_updates": len(updates)}
