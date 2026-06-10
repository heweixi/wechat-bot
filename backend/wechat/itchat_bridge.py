# itchat-uos 微信桥接实现
#
# 依赖：pip install itchat-uos
# 注意：非官方 API，有被封号风险。

from __future__ import annotations

import asyncio
import logging
import queue
import threading
from typing import Optional

from wechat.bridge import ContactInfo, WeChatBridge, WeChatMessage

logger = logging.getLogger(__name__)


try:
    import itchat
except ImportError:
    itchat = None  # type: ignore[assignment]


class ItChatBridge(WeChatBridge):
    """基于 itchat-uos 的微信桥接"""

    def __init__(self):
        self._logged_in = False
        self._msg_queue: queue.Queue = queue.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── 登录 / 登出 ──

    async def login(self) -> bool:
        if itchat is None:
            logger.error("itchat-uos 未安装，无法登录微信。pip install itchat-uos")
            return False

        loop = asyncio.get_running_loop()
        self._loop = loop

        def _login():
            itchat.auto_login(
                hotReload=True,
                enableCmdQR=2,
                picDir="./data/qrcode.png",
            )
            loop.call_soon_threadsafe(setattr, self, "_logged_in", True)
            # 注册消息回调
            itchat.msg_register(itchat.content.TEXT, isFriendChat=True)(
                lambda msg: self._on_itchat_msg(msg, is_group=False)
            )
            itchat.msg_register(itchat.content.TEXT, isGroupChat=True)(
                lambda msg: self._on_itchat_msg(msg, is_group=True)
            )
            # 好友申请
            itchat.msg_register(itchat.content.FRIENDS)(
                self._on_itchat_friend_request
            )
            logger.info("微信登录成功")

        await asyncio.get_running_loop().run_in_executor(None, _login)
        return self._logged_in

    async def logout(self):
        if itchat and self._logged_in:
            itchat.logout()
        self._logged_in = False

    # ── 发送 ──

    async def send_message(self, to_wx: str, content: str) -> bool:
        if not self._logged_in or itchat is None:
            return False

        def _send():
            itchat.send(content, toUserName=to_wx)

        await asyncio.get_running_loop().run_in_executor(None, _send)
        return True

    async def accept_friend(self, wx_id: str, ticket: str) -> bool:
        if itchat is None:
            return False

        def _accept():
            itchat.add_friend(userName=wx_id, ticket=ticket)

        await asyncio.get_running_loop().run_in_executor(None, _accept)
        return True

    async def get_contacts(self) -> list[ContactInfo]:
        if not self._logged_in or itchat is None:
            return []

        def _fetch():
            friends = itchat.get_friends(update=True)
            result = []
            for f in friends:
                result.append(
                    ContactInfo(
                        wx_id=f.get("UserName", ""),
                        nickname=f.get("NickName", ""),
                        remark=f.get("RemarkName", ""),
                        is_group=False,
                        avatar=f.get("HeadImgUrl", ""),
                    )
                )
            return result

        return await asyncio.get_running_loop().run_in_executor(None, _fetch)

    def is_logged_in(self) -> bool:
        return self._logged_in

    async def run_forever(self):
        """阻塞运行（itchat 需要）"""
        if itchat is None:
            return
        while self._logged_in:
            await asyncio.sleep(1)

    # ── 内部回调 ──

    def _on_itchat_msg(self, msg, is_group: bool):
        wx_msg = WeChatMessage(
            msg_id=msg.get("MsgId", ""),
            from_wx=msg.get("FromUserName", ""),
            from_nick=msg.get("NickName", ""),
            content=msg.get("Text", ""),
            raw=msg,
            is_group=is_group,
        )
        if self.on_message:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._call_handler(self.on_message, wx_msg), self._loop
                )
            except Exception:
                logger.exception("消息处理异常")

    def _on_itchat_friend_request(self, msg):
        wx_msg = WeChatMessage(
            msg_id=msg.get("MsgId", ""),
            from_wx=msg.get("UserName", ""),
            from_nick=msg.get("NickName", ""),
            content=msg.get("Content", ""),
            raw=msg,
            is_friend_request=True,
        )
        if self.on_friend_request:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._call_handler(self.on_friend_request, wx_msg), self._loop
                )
            except Exception:
                logger.exception("好友申请处理异常")

    async def _call_handler(self, handler, msg):
        try:
            await handler(msg)
        except Exception:
            logger.exception("Handler 异常")
