# AI 适配器 — 基础抽象类

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class ChatMessage:
    role: str          # "user" | "assistant" | "system"
    content: str


@dataclass
class AIResponse:
    content: str
    model: str = ""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    cost: float = 0.0


class AIAdapter(ABC):
    """所有 AI 后端必须实现的接口"""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse:
        """发送消息并获取 AI 回复"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """流式回复（逐 token 返回）"""
        ...
        yield ""  # pragma: no cover

    @property
    @abstractmethod
    def provider_type(self) -> str:
        ...
