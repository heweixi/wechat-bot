# 模拟微信桥接（开发/测试用，不连真实微信）
#
# 功能：
# - 模拟登录/登出
# - 可通过 API 注入模拟消息，测试自动回复流程
# - 预置联系人列表，可扩展
# - 自动回复模拟（当 on_message 注册后，发送的消息会触发 AI）

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from wechat.bridge import ContactInfo, WeChatBridge, WeChatMessage

logger = logging.getLogger(__name__)


class MockBridge(WeChatBridge):
    """模拟桥接器 — 不连微信，用于开发前端和测试"""

    def __init__(self):
        self._logged_in = False
        # 预置联系人
        self._contacts: list[ContactInfo] = [
            ContactInfo(wx_id="mock_user_1", nickname="张三", remark="老张"),
            ContactInfo(wx_id="mock_user_2", nickname="李四", remark=""),
            ContactInfo(wx_id="mock_user_3", nickname="王五", remark="测试用户"),
            ContactInfo(wx_id="mock_group_1", nickname="项目群", remark="", is_group=True),
        ]
        # 收到的消息日志
        self.sent_messages: list[dict] = []
        # 模拟自动聊天（每 30 秒自动发一条消息）
        self._auto_chat_task: Optional[asyncio.Task] = None

    async def login(self) -> bool:
        self._logged_in = True
        logger.info("[MockBridge] 模拟登录成功")
        logger.info("[MockBridge] 预置联系人: 张三, 李四, 王五, 项目群")
        logger.info("[MockBridge] 可用测试命令: POST /api/wechat/mock/send 发送模拟消息")

        # 启动自动聊天模拟（首次登录 5 秒后发一条）
        self._auto_chat_task = asyncio.create_task(self._auto_chat_loop())
        return True

    async def logout(self):
        self._logged_in = False
        if self._auto_chat_task:
            self._auto_chat_task.cancel()
            self._auto_chat_task = None
        logger.info("[MockBridge] 模拟登出")

    async def send_message(self, to_wx: str, content: str) -> bool:
        self.sent_messages.append({
            "to": to_wx,
            "content": content,
            "time": datetime.utcnow().isoformat(),
        })
        logger.info(f"[MockBridge] → 发送给 {to_wx}: {content[:80]}")
        return True

    async def accept_friend(self, wx_id: str, ticket: str) -> bool:
        logger.info(f"[MockBridge] ✓ 接受好友申请: {wx_id}")
        return True

    async def get_contacts(self) -> list[ContactInfo]:
        return self._contacts

    def add_contact(self, wx_id: str, nickname: str, remark: str = "", is_group: bool = False):
        """动态添加联系人"""
        self._contacts.append(
            ContactInfo(wx_id=wx_id, nickname=nickname, remark=remark, is_group=is_group)
        )

    def is_logged_in(self) -> bool:
        return self._logged_in

    def get_sent_messages(self, limit: int = 20) -> list[dict]:
        return self.sent_messages[-limit:]

    async def inject_message(self, from_wx: str, content: str):
        """注入一条模拟消息（从 API 调用）"""
        contact = next((c for c in self._contacts if c.wx_id == from_wx), None)
        if not contact:
            logger.warning(f"[MockBridge] 未知发送者: {from_wx}，请先 add_contact")
            return

        msg = WeChatMessage(
            msg_id=f"mock_{datetime.utcnow().timestamp()}",
            from_wx=from_wx,
            from_nick=contact.nickname,
            content=content,
            raw=None,
            is_group=contact.is_group,
        )
        logger.info(f"[MockBridge] ← 收到来自 {contact.nickname}({from_wx}): {content[:80]}")

        if self.on_message:
            try:
                await self.on_message(msg)
            except Exception:
                logger.exception("[MockBridge] on_message 处理异常")

    async def _auto_chat_loop(self):
        """定时发送模拟消息（仅当 on_message 注册了才发）"""
        if not self.on_message:
            return

        # 等待 8 秒后发第一条
        await asyncio.sleep(8)
        if not self._logged_in:
            return

        for wx_id, nickname, text, delay in self._get_auto_messages():
            if not self._logged_in:
                break
            await asyncio.sleep(delay)
            msg = WeChatMessage(
                msg_id=f"mock_auto_{datetime.utcnow().timestamp()}",
                from_wx=wx_id,
                from_nick=nickname,
                content=text,
                raw=None,
                is_group=False,
            )
            try:
                await self.on_message(msg)
            except Exception:
                pass

    @staticmethod
    def _get_auto_messages():
        """预置的自动测试消息序列"""
        return [
            ("mock_user_1", "张三",  "你好", 3),
            ("mock_user_2", "李四",  "在吗？帮我查个东西", 8),
            ("mock_user_1", "张三",  "你叫什么名字？", 6),
            ("mock_user_3", "王五",  "你是什么 AI 模型？", 10),
        ]

    async def run_forever(self):
        while self._logged_in:
            await asyncio.sleep(1)
