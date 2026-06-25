# wkteam (Eyun) iPad 协议桥接实现
#
# 技术路线：
#   收消息: wkteam webhook 回调 → FastAPI endpoint → on_message
#   发消息: HTTP POST → wkteam REST API
#   登录:   wkteam 平台管理（非本地扫码）
#
# API 地址: http://125.122.152.142:9899
# 认证方式: Bearer Token (per account)

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

import httpx

from config import settings
from wechat.bridge import ContactInfo, WeChatBridge, WeChatMessage

logger = logging.getLogger(__name__)


class WkteamBridge(WeChatBridge):
    """基于 wkteam iPad 协议的微信桥接"""

    def __init__(self):
        self._logged_in = False
        self._base_url = settings.WKTEAM_API_URL.rstrip("/")
        self._token = settings.WKTEAM_TOKEN
        self._wx_id = settings.WKTEAM_WX_ID  # 当前登录的微信号 wxid
        self._client: Optional[httpx.AsyncClient] = None
        # 消息去重 (msg_id -> timestamp)
        self._seen_msgs: dict[str, float] = {}
        self._seen_max = 5000

    # ── 登录 / 登出 ──

    async def login(self) -> bool:
        """wkteam 不需要本地扫码，验证 token 有效性即可"""
        if not self._token:
            logger.error("WKTEAM_TOKEN 未配置")
            return False

        self._client = httpx.AsyncClient(timeout=30.0)

        # 验证连接 —— 尝试获取登录状态
        try:
            resp = await self._api_post("/isOnline", {"wcId": self._wx_id})
            if resp and resp.get("code") == 200:
                online = resp.get("data", {})
                self._logged_in = bool(online)
                logger.info(f"wkteam 连接成功，在线状态: {self._logged_in}")
            else:
                # 即使状态检查失败也算连接成功（webhook 回调仍然可用）
                self._logged_in = True
                logger.warning(f"wkteam 状态检查返回: {resp}，假定在线")
        except Exception as e:
            logger.warning(f"wkteam 状态检查异常: {e}，假定在线（webhook 仍可工作）")
            self._logged_in = True

        return self._logged_in

    async def logout(self):
        self._logged_in = False
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("wkteam 桥接已关闭")

    # ── 发送消息 ──

    async def send_message(self, to_wx: str, content: str) -> bool:
        """发送文本消息"""
        resp = await self._api_post("/sendText", {
            "wcId": self._wx_id,
            "toWxId": to_wx,
            "content": content,
        })
        if resp and resp.get("code") == 200:
            logger.info(f"[wkteam] → 发送给 {to_wx}: {content[:60]}")
            return True
        else:
            logger.error(f"[wkteam] 发送失败: {resp}")
            return False

    async def send_image(self, to_wx: str, image_url: str) -> bool:
        """发送图片（URL 方式）"""
        resp = await self._api_post("/sendImage2", {
            "wcId": self._wx_id,
            "toWxId": to_wx,
            "imgUrl": image_url,
        })
        return bool(resp and resp.get("code") == 200)

    async def send_file(self, to_wx: str, file_url: str, file_name: str = "") -> bool:
        """发送文件"""
        resp = await self._api_post("/sendFile", {
            "wcId": self._wx_id,
            "toWxId": to_wx,
            "fileUrl": file_url,
            "fileName": file_name,
        })
        return bool(resp and resp.get("code") == 200)

    # ── 接受好友 ──

    async def accept_friend(self, wx_id: str, ticket: str) -> bool:
        """接受好友申请（通过 wkteam API）"""
        resp = await self._api_post("/acceptFriend", {
            "wcId": self._wx_id,
            "friendWxId": wx_id,
            "ticket": ticket,
        })
        if resp and resp.get("code") == 200:
            logger.info(f"[wkteam] ✓ 接受好友: {wx_id}")
            return True
        return False

    # ── 联系人 ──

    async def get_contacts(self) -> list[ContactInfo]:
        """获取联系人列表"""
        resp = await self._api_post("/getContactList", {
            "wcId": self._wx_id,
        })
        if not resp or resp.get("code") != 200:
            return []

        contacts = []
        for item in resp.get("data", []):
            contacts.append(ContactInfo(
                wx_id=item.get("wxId", ""),
                nickname=item.get("nickName", ""),
                remark=item.get("remark", ""),
                is_group=item.get("wxId", "").endswith("@chatroom"),
                avatar=item.get("avatar", ""),
            ))
        return contacts

    # ── 状态 ──

    def is_logged_in(self) -> bool:
        return self._logged_in

    async def run_forever(self):
        """wkteam 模式不需要 run_forever（消息通过 webhook 接收）"""
        # 保持桥接存活即可
        import asyncio
        while self._logged_in:
            await asyncio.sleep(5)

    # ── Webhook 消息处理（由 API 路由调用） ──

    async def handle_webhook(self, payload: dict):
        """
        处理 wkteam webhook 回调的消息。
        由 /api/wechat/webhook 路由调用。
        """
        msg_type = payload.get("type", "")
        from_wx = payload.get("fromWxId", "") or payload.get("finalFromWxId", "")
        content = payload.get("content", "") or payload.get("msg", "")
        msg_id = payload.get("msgId", "") or payload.get("newMsgId", "")
        from_nick = payload.get("fromNickName", "") or payload.get("fromName", "")
        to_wx = payload.get("toWxId", "")

        # 跳过自己发的消息
        if from_wx == self._wx_id:
            return

        # 只处理发给自己的消息（排除自己发出去的）
        if to_wx and to_wx != self._wx_id:
            # 群消息: toWxId 是群 ID，也需要处理
            if not to_wx.endswith("@chatroom"):
                return

        # 消息去重
        if msg_id and not self._dedupe(msg_id):
            return

        is_group = bool(from_wx and from_wx.endswith("@chatroom")) or \
                   bool(to_wx and to_wx.endswith("@chatroom"))

        # 群消息：真实发送者在 finalFromWxId
        actual_from = payload.get("finalFromWxId", "") or from_wx
        if is_group and actual_from == self._wx_id:
            return  # 群里自己发的

        # 好友申请
        if msg_type in ("37", "verify"):
            wx_msg = WeChatMessage(
                msg_id=msg_id,
                from_wx=from_wx,
                from_nick=from_nick,
                content=content,
                raw=payload,
                is_friend_request=True,
            )
            if self.on_friend_request:
                await self.on_friend_request(wx_msg)
            return

        # 文本消息 (type=1 或 "text")
        if msg_type in ("1", "text", ""):
            wx_msg = WeChatMessage(
                msg_id=msg_id,
                from_wx=actual_from if is_group else from_wx,
                from_nick=from_nick,
                content=content,
                raw=payload,
                is_group=is_group,
            )
            if self.on_message:
                await self.on_message(wx_msg)
            return

        # 图片消息 (type=3)
        if msg_type in ("3", "image"):
            # 下载图片
            img_url = await self._download_media(payload, "image")
            wx_msg = WeChatMessage(
                msg_id=msg_id,
                from_wx=actual_from if is_group else from_wx,
                from_nick=from_nick,
                content=f"[图片] {img_url}" if img_url else "[图片]",
                raw=payload,
                is_group=is_group,
            )
            if self.on_message:
                await self.on_message(wx_msg)
            return

        # 语音消息 (type=34)
        if msg_type in ("34", "voice"):
            wx_msg = WeChatMessage(
                msg_id=msg_id,
                from_wx=actual_from if is_group else from_wx,
                from_nick=from_nick,
                content="[语音消息]",
                raw=payload,
                is_group=is_group,
            )
            if self.on_message:
                await self.on_message(wx_msg)
            return

        # 其他消息类型记录日志
        logger.debug(f"[wkteam] 未处理的消息类型 {msg_type}: {payload}")

    # ── 内部方法 ──

    async def _api_post(self, endpoint: str, data: dict) -> Optional[dict]:
        """调用 wkteam API"""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)

        url = f"{self._base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        try:
            resp = await self._client.post(url, json=data, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"[wkteam] API {endpoint} HTTP {e.response.status_code}: {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"[wkteam] API {endpoint} 异常: {e}")
            return None

    async def _download_media(self, payload: dict, media_type: str) -> str:
        """下载媒体文件（图片/语音），返回可访问的 URL 或本地路径"""
        try:
            if media_type == "image":
                resp = await self._api_post("/getMsgImg", {
                    "wcId": self._wx_id,
                    "content": payload.get("content", ""),
                    "msgId": payload.get("msgId", ""),
                })
            elif media_type == "voice":
                resp = await self._api_post("/getMsgVoice", {
                    "wcId": self._wx_id,
                    "content": payload.get("content", ""),
                    "msgId": payload.get("msgId", ""),
                })
            else:
                return ""

            if resp and resp.get("code") == 200:
                return resp.get("data", {}).get("url", "")
        except Exception as e:
            logger.warning(f"[wkteam] 下载 {media_type} 失败: {e}")
        return ""

    def _dedupe(self, msg_id: str) -> bool:
        """消息去重，返回 True 表示是新消息"""
        now = time.time()
        if msg_id in self._seen_msgs:
            return False
        self._seen_msgs[msg_id] = now
        # 清理过期记录
        if len(self._seen_msgs) > self._seen_max:
            cutoff = now - 300  # 5 分钟前的丢弃
            self._seen_msgs = {
                k: v for k, v in self._seen_msgs.items() if v > cutoff
            }
        return True
