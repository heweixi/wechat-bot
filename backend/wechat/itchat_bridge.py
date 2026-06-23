# itchat-uos 微信桥接实现
#
# 依赖：pip install itchat-uos
# 注意：非官方 API，有被封号风险。
# 支持：自动重连 / QR 码保存供 Web 显示 / 线程安全

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

from config import settings
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
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._login_thread: Optional[threading.Thread] = None
        self._qrcode_path: str = str(Path(settings.DATA_DIR) / "qrcode.png")
        self._qrcode_updated_at: float = 0.0
        self._stop_event = threading.Event()

    # ── 登录 / 登出 ──

    async def login(self) -> bool:
        if itchat is None:
            logger.error("itchat-uos 未安装。运行: pip install itchat-uos")
            return False

        self._loop = asyncio.get_running_loop()
        self._stop_event.clear()

        def _login_worker():
            """在独立线程中运行 itchat（阻塞式）"""
            try:
                itchat.auto_login(
                    hotReload=True,
                    enableCmdQR=2,
                    picDir=self._qrcode_path,
                    # 退出回调 — 触发重连
                    exitCallback=lambda: self._loop.call_soon_threadsafe(
                        self._on_disconnected
                    ),
                )
            except Exception:
                logger.exception("itchat 登录异常")
                self._loop.call_soon_threadsafe(setattr, self, "_logged_in", False)
                return

            self._loop.call_soon_threadsafe(setattr, self, "_logged_in", True)
            logger.info("微信登录成功")

            # 注册消息回调
            itchat.msg_register(itchat.content.TEXT, isFriendChat=True)(
                lambda msg: self._on_itchat_msg(msg, is_group=False)
            )
            itchat.msg_register(itchat.content.TEXT, isGroupChat=True)(
                lambda msg: self._on_itchat_msg(msg, is_group=True)
            )
            itchat.msg_register(itchat.content.PICTURE, isFriendChat=True)(
                lambda msg: self._on_itchat_msg(msg, is_group=False)
            )
            itchat.msg_register(itchat.content.FRIENDS)(
                self._on_itchat_friend_request
            )

            # 核心：必须调用 configured_reply() 才能处理消息
            # itchat 会在内部循环等待消息，阻塞当前线程
            try:
                itchat.configured_reply()
            except Exception:
                logger.exception("itchat 消息循环异常")
            finally:
                self._loop.call_soon_threadsafe(setattr, self, "_logged_in", False)

        self._login_thread = threading.Thread(
            target=_login_worker, daemon=True, name="itchat-login"
        )
        self._login_thread.start()

        # 等待一小段时间确认登录是否启动
        await asyncio.sleep(1)
        return True  # 登录在后台进行，调用方通过 is_logged_in 或 API 查询

    def _on_disconnected(self):
        """微信断开连接时的处理"""
        self._logged_in = False
        logger.warning("微信连接已断开")
        # 启动自动重连（延迟 5 秒）
        if not self._stop_event.is_set():
            logger.info("5 秒后尝试自动重连...")
            threading.Timer(5.0, self._auto_reconnect).start()

    def _auto_reconnect(self):
        """自动重连"""
        if self._stop_event.is_set() or self._logged_in:
            return
        logger.info("尝试自动重连微信...")
        try:
            self._login_worker_internal()
        except Exception:
            logger.exception("自动重连失败，30 秒后再试")
            if not self._stop_event.is_set():
                threading.Timer(30.0, self._auto_reconnect).start()

    def _login_worker_internal(self):
        """内部登录（供重连使用）"""
        itchat.auto_login(
            hotReload=True,
            enableCmdQR=2,
            picDir=self._qrcode_path,
            exitCallback=lambda: self._loop.call_soon_threadsafe(
                self._on_disconnected
            ),
        )
        self._loop.call_soon_threadsafe(setattr, self, "_logged_in", True)
        logger.info("微信重连成功")

    async def logout(self):
        self._stop_event.set()
        if itchat and self._logged_in:
            try:
                await asyncio.get_running_loop().run_in_executor(None, itchat.logout)
            except Exception:
                pass
        self._logged_in = False
        logger.info("微信已登出")

    # ── QR 码 ──

    def get_qrcode_path(self) -> Optional[str]:
        """获取当前 QR 码图片路径（供 Web API 使用）"""
        if os.path.exists(self._qrcode_path):
            return self._qrcode_path
        return None

    def get_qrcode_age(self) -> float:
        """QR 码图片的生成时间（秒），用于前端判断是否过期"""
        if os.path.exists(self._qrcode_path):
            return time.time() - os.path.getmtime(self._qrcode_path)
        return -1

    # ── 发送 ──

    async def send_message(self, to_wx: str, content: str) -> bool:
        if not self._logged_in or itchat is None:
            return False

        def _send():
            try:
                # itchat 的 send 可能因为登录态失效而失败
                itchat.send(content, toUserName=to_wx)
                return True
            except Exception:
                logger.exception(f"发送消息失败到 {to_wx}")
                return False

        return await asyncio.get_running_loop().run_in_executor(None, _send)

    async def accept_friend(self, wx_id: str, ticket: str) -> bool:
        if itchat is None:
            return False

        def _accept():
            try:
                itchat.add_friend(userName=wx_id, ticket=ticket)
                return True
            except Exception:
                logger.exception(f"接受好友申请失败: {wx_id}")
                return False

        return await asyncio.get_running_loop().run_in_executor(None, _accept)

    async def get_contacts(self) -> list[ContactInfo]:
        if not self._logged_in or itchat is None:
            return []

        def _fetch():
            try:
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
            except Exception:
                logger.exception("获取联系人失败")
                return []

        return await asyncio.get_running_loop().run_in_executor(None, _fetch)

    def is_logged_in(self) -> bool:
        return self._logged_in

    async def run_forever(self):
        """保持进程运行（login 线程在后台工作）"""
        if itchat is None:
            return
        while not self._stop_event.is_set():
            await asyncio.sleep(1)

    # ── 内部回调 ──

    def _on_itchat_msg(self, msg, is_group: bool):
        if not self._loop:
            return
        # 跳过自己发的消息
        if msg.get("FromUserName") == "filehelper":
            return
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
                logger.exception("消息回调异常")

    def _on_itchat_friend_request(self, msg):
        if not self._loop:
            return
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
                logger.exception("好友申请回调异常")

    async def _call_handler(self, handler, msg):
        try:
            await handler(msg)
        except Exception:
            logger.exception("Handler 异常")
