# 模拟微信桥接（开发/测试用，不连真实微信）

from __future__ import annotations

import asyncio
import logging
import random
import string

from wechat.bridge import ContactInfo, WeChatBridge, WeChatMessage

logger = logging.getLogger(__name__)


class MockBridge(WeChatBridge):
    """模拟桥接器 — 不连微信，用于开发前端和测试"""

    def __init__(self):
        self._logged_in = False

    async def login(self) -> bool:
        self._logged_in = True
        logger.info("[MockBridge] 模拟登录成功")
        return True

    async def logout(self):
        self._logged_in = False
        logger.info("[MockBridge] 模拟登出")

    async def send_message(self, to_wx: str, content: str) -> bool:
        logger.info(f"[MockBridge] 发送消息给 {to_wx}: {content[:50]}...")
        return True

    async def accept_friend(self, wx_id: str, ticket: str) -> bool:
        logger.info(f"[MockBridge] 接受好友申请: {wx_id}")
        return True

    async def get_contacts(self) -> list[ContactInfo]:
        return [
            ContactInfo(wx_id="mock_user_1", nickname="张三", remark="老张"),
            ContactInfo(wx_id="mock_user_2", nickname="李四", remark=""),
            ContactInfo(wx_id="mock_group_1", nickname="项目群", is_group=True),
        ]

    def is_logged_in(self) -> bool:
        return self._logged_in

    async def run_forever(self):
        while self._logged_in:
            await asyncio.sleep(1)
