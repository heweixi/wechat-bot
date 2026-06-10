# 微信桥接器 — 抽象接口
#
# 定义 WeChatBridge 接口，底层具体实现可切换（itchat / wechaty / 企业微信等）。

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class WeChatMessage:
    msg_id: str = ""
    from_wx: str = ""       # 发送者 wx_id
    from_nick: str = ""     # 发送者昵称
    content: str = ""       # 文本内容
    raw: object = None      # 原始消息对象
    is_group: bool = False  # 是否群聊
    is_friend_request: bool = False  # 是否好友申请


@dataclass
class ContactInfo:
    wx_id: str = ""
    nickname: str = ""
    remark: str = ""
    is_group: bool = False
    avatar: str = ""


class WeChatBridge(ABC):
    """微信桥接抽象层"""

    on_message: Optional[Callable[[WeChatMessage], None]] = None
    on_friend_request: Optional[Callable[[WeChatMessage], None]] = None

    @abstractmethod
    async def login(self) -> bool:
        """登录微信"""
        ...

    @abstractmethod
    async def logout(self):
        """登出"""
        ...

    @abstractmethod
    async def send_message(self, to_wx: str, content: str) -> bool:
        """发送消息"""
        ...

    @abstractmethod
    async def accept_friend(self, wx_id: str, ticket: str) -> bool:
        """接受好友申请"""
        ...

    @abstractmethod
    async def get_contacts(self) -> list[ContactInfo]:
        """获取联系人列表"""
        ...

    @abstractmethod
    def is_logged_in(self) -> bool:
        """是否已登录"""
        ...

    @abstractmethod
    async def run_forever(self):
        """持续运行（阻塞）"""
        ...
