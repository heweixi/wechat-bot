# API 路由 — 微信桥接状态 + wkteam Webhook

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request

from app import get_bridge, start_bridge
from wechat.wkteam_bridge import WkteamBridge
from wechat.mock_bridge import MockBridge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wechat", tags=["WeChat"])


# ── Webhook 接收（wkteam 消息回调） ──

@router.post("/webhook")
async def wechat_webhook(request: Request):
    """
    接收 wkteam 的消息推送回调。
    wkteam 配置 webhook URL 为: http://your-server:8010/api/wechat/webhook
    """
    try:
        payload = await request.json()
    except Exception:
        # 有些回调可能是 form 格式
        form = await request.form()
        payload = dict(form)

    logger.debug(f"[webhook] 收到回调: {payload}")

    bridge = get_bridge()
    if not bridge:
        logger.warning("[webhook] 桥接未初始化，丢弃消息")
        return {"code": 200, "msg": "bridge not ready"}

    if isinstance(bridge, WkteamBridge):
        try:
            await bridge.handle_webhook(payload)
        except Exception:
            logger.exception("[webhook] 处理消息异常")
    elif isinstance(bridge, MockBridge):
        # MockBridge 也可以通过 webhook 注入消息（测试用）
        from_wx = payload.get("fromWxId", "mock_user_1")
        content = payload.get("content", "") or payload.get("msg", "")
        if content:
            await bridge.inject_message(from_wx, content)

    return {"code": 200, "msg": "ok"}


# ── 状态 ──

@router.get("/status")
async def wechat_status():
    """微信连接状态"""
    bridge = get_bridge()
    if not bridge:
        return {
            "logged_in": False,
            "connected": False,
            "bridge_type": None,
        }

    bridge_type = "wkteam" if isinstance(bridge, WkteamBridge) else "mock"

    return {
        "logged_in": bridge.is_logged_in(),
        "connected": True,
        "bridge_type": bridge_type,
    }


# ── 手动启动 ──

@router.post("/login")
async def manual_login():
    """手动启动微信桥接"""
    ok = await start_bridge()
    if ok:
        return {"ok": True, "message": "桥接已启动"}
    return {"ok": False, "message": "桥接启动失败，请查看后端日志"}


# ── 发送消息（手动测试用） ──

@router.post("/send")
async def send_message(data: dict):
    """手动发送消息（调试用）"""
    bridge = get_bridge()
    if not bridge:
        raise HTTPException(400, "桥接未连接")

    to_wx = data.get("to_wx", "")
    content = data.get("content", "")
    if not to_wx or not content:
        raise HTTPException(422, "to_wx 和 content 不能为空")

    ok = await bridge.send_message(to_wx, content)
    return {"ok": ok}


# ── Mock 调试 ──

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
