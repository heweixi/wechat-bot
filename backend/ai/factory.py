# AI 适配器工厂

from __future__ import annotations

from ai.base import AIAdapter
from ai.claude_adapter import ClaudeAdapter
from ai.openai_adapter import OpenAIAdapter


class AIFactory:
    """根据配置创建 AI 适配器实例"""

    _registry: dict[str, type[AIAdapter]] = {
        "openai": OpenAIAdapter,
        "claude": ClaudeAdapter,
        "custom": OpenAIAdapter,  # 自定义（兼容 OpenAI 格式）
    }

    @classmethod
    def register(cls, provider_type: str, adapter_cls: type[AIAdapter]):
        """注册自定义适配器"""
        cls._registry[provider_type] = adapter_cls

    @classmethod
    def create(cls, config: dict) -> AIAdapter:
        """根据 provider_type 创建适配器"""
        provider_type = config.get("provider_type", "openai")
        adapter_cls = cls._registry.get(provider_type)
        if not adapter_cls:
            raise ValueError(
                f"不支持的 AI 提供者: {provider_type}，可用: {list(cls._registry.keys())}"
            )
        return adapter_cls(config)

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._registry.keys())
