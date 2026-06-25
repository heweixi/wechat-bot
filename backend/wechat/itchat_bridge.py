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

from config import settings, DATA_DIR
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
        self._qrcode_path: str = str(DATA_DIR / "qrcode.png")
        self._qrcode_updated_at: float = 0.0
        self._stop_event = threading.Event()

    # ── 登录 / 登出 ──

    async def login(self) -> bool:
        if itchat is None:
            logger.error("itchat-uos 未安装。运行: pip install itchat-uos")
            return False

        self._loop = asyncio.get_running_loop()
        self._stop_event.clear()
        self._start_login()

        # 等待一小段时间确认登录是否启动
        await asyncio.sleep(1)
        return True  # 登录在后台进行，调用方通过 is_logged_in 或 API 查询

    def refresh_qrcode(self):
        """强制刷新二维码——终止当前登录进程并重新开始"""
        if self._logged_in:
            logger.info("已登录，无需刷新二维码")
            return False
        if self._login_thread and self._login_thread.is_alive():
            logger.info("终止当前登录线程，重新生成二维码...")
            # 先让 itchat 退出
            try:
                itchat.logout()
            except Exception:
                pass
            self._login_thread = None
        # 启动新线程重新登录
        self._start_login()
        return True

    def _start_login(self):
        """启动登录线程"""
        # 必须在 auto_login 之前注册消息处理器，否则登录后收不到消息
        self._register_handlers()

        def _worker():
            try:
                logger.info("itchat 开始登录流程...")
                # loginCallback / exitCallback 用于状态通知
                # statusStorageDir 指定缓存目录避免路径问题
                itchat.auto_login(
                    hotReload=True,
                    statusStorageDir=str(DATA_DIR / "itchat.pkl"),
                    enableCmdQR=2,
                    picDir=self._qrcode_path,
                    loginCallback=self._on_login_success,
                    exitCallback=self._on_exit,
                )
            except Exception:
                logger.exception("itchat 登录异常")
                self._loop.call_soon_threadsafe(setattr, self, "_logged_in", False)
                return
            # auto_login 返回意味着登录成功
            logger.info("微信登录成功，启动消息循环")
            self._loop.call_soon_threadsafe(setattr, self, "_logged_in", True)
            try:
                itchat.run(blockThread=True)
            except Exception:
                logger.exception("itchat 消息循环异常")
            finally:
                self._loop.call_soon_threadsafe(setattr, self, "_logged_in", False)

        self._login_thread = threading.Thread(
            target=_worker, daemon=True, name="itchat-login"
        )
        self._login_thread.start()

    def _on_login_success(self):
        """itchat loginCallback — 登录确认成功后立即触发"""
        logger.info("✅ 微信扫码确认成功，正在初始化...")
        self._logged_in = True

    def _on_exit(self):
        """itchat exitCallback — 退出/断开时触发"""
        if self._loop:
            self._loop.call_soon_threadsafe(self._on_disconnected)

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
        self._register_handlers()
        itchat.auto_login(
            hotReload=True,
            statusStorageDir=str(DATA_DIR / "itchat.pkl"),
            enableCmdQR=2,
            picDir=self._qrcode_path,
            loginCallback=self._on_login_success,
            exitCallback=self._on_exit,
        )
        self._loop.call_soon_threadsafe(setattr, self, "_logged_in", True)
        logger.info("微信重连成功")
        itchat.run(blockThread=True)

    def _register_handlers(self):
        """注册 itchat 消息回调"""
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
