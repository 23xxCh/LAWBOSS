"""WebSocket 实时批量检测进度推送"""
import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # batch_id -> websockets

    async def connect(self, websocket: WebSocket, batch_id: str):
        await websocket.accept()
        if batch_id not in self.active_connections:
            self.active_connections[batch_id] = set()
        self.active_connections[batch_id].add(websocket)

    def disconnect(self, websocket: WebSocket, batch_id: str):
        if batch_id in self.active_connections:
            self.active_connections[batch_id].discard(websocket)
            if not self.active_connections[batch_id]:
                del self.active_connections[batch_id]

    async def broadcast(self, batch_id: str, message: dict):
        """向指定 batch 的所有连接广播消息"""
        if batch_id not in self.active_connections:
            return
        stale = set()
        for ws in self.active_connections[batch_id]:
            try:
                await ws.send_json(message)
            except Exception:
                stale.add(ws)
        for ws in stale:
            self.active_connections[batch_id].discard(ws)


manager = ConnectionManager()


@router.websocket("/ws/batch-check/{batch_id}")
async def batch_check_websocket(websocket: WebSocket, batch_id: str):
    """WebSocket 端点：实时监控批量检测进度"""
    await manager.connect(websocket, batch_id)
    try:
        while True:
            # 保持连接，接收 ping 或数据
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, batch_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        manager.disconnect(websocket, batch_id)


async def notify_batch_progress(batch_id: str, current: int, total: int, item_result: dict = None):
    """广播批量检测进度"""
    await manager.broadcast(batch_id, {
        "type": "progress",
        "current": current,
        "total": total,
        "percent": int(current / total * 100) if total > 0 else 0,
        "item_result": item_result,
    })
