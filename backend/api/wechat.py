# API 路由 — 微信桥接状态

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app import get_bridge
from wechat.itchat_bridge import ItChatBridge
from wechat.mock_bridge import MockBridge

router = APIRouter(prefix="/api/wechat", tags=["WeChat"])


@router.get("/status")
async def wechat_status():
    """微信连接状态 + QR 码信息"""
    bridge = get_bridge()
    if not bridge:
        return {"logged_in": False, "connected": False}

    info = {
        "logged_in": bridge.is_logged_in(),
        "connected": True,
    }

    # 如果是 itchat 桥接，提供 QR 码信息
    if isinstance(bridge, ItChatBridge):
        qr_age = bridge.get_qrcode_age()
        info["qrcode_available"] = bridge.get_qrcode_path() is not None
        info["qrcode_age"] = round(qr_age, 1)
        info["qrcode_expired"] = qr_age > 60  # QR 码 60 秒过期
    else:
        info["qrcode_available"] = False

    return info


@router.get("/qrcode")
async def get_qrcode():
    """获取微信登录 QR 码图片"""
    bridge = get_bridge()
    if not bridge or not isinstance(bridge, ItChatBridge):
        raise HTTPException(404, "未使用 itchat 桥接")

    path = bridge.get_qrcode_path()
    if not path:
        raise HTTPException(404, "QR 码尚未生成，请先尝试登录")

    return FileResponse(
        path,
        media_type="image/png",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# ── 模拟桥接调试 API（仅 MockBridge 模式下可用） ──


@router.post("/mock/send")
async def mock_send_message(data: dict):
    """向机器人发送一条模拟消息（开发测试用）"""
    bridge = get_bridge()
    if not isinstance(bridge, MockBridge):
        raise HTTPException(400, "仅 MockBridge 模式下可用")

    from_wx = data.get("from_wx", "mock_user_1")
    content = data.get("content", "")

    if not content:
        raise HTTPException(422, "content 不能为空")

    await bridge.inject_message(from_wx, content)
    return {"ok": True, "from_wx": from_wx, "content": content}


@router.get("/mock/messages")
async def mock_get_sent_messages(limit: int = 20):
    """查看机器人已发送的模拟消息"""
    bridge = get_bridge()
    if not isinstance(bridge, MockBridge):
        raise HTTPException(400, "仅 MockBridge 模式下可用")

    return {"messages": bridge.get_sent_messages(limit)}
