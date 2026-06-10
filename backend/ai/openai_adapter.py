# OpenAI 适配器

from __future__ import annotations

from typing import AsyncIterator

from openai import AsyncOpenAI

from ai.base import AIAdapter, AIResponse, ChatMessage


class OpenAIAdapter(AIAdapter):
    """兼容 OpenAI API 格式的所有后端（含 deepseek / groq / 本地 ollama 等）"""

    @property
    def provider_type(self) -> str:
        return "openai"

    def _build_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=self.config.get("api_key", ""),
            base_url=self.config.get("base_url", "https://api.openai.com/v1"),
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse:
        client = self._build_client()
        model = self.config.get("model", "gpt-4o-mini")
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        for m in messages:
            api_messages.append({"role": m.role, "content": m.content})

        resp = await client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = resp.choices[0]
        return AIResponse(
            content=choice.message.content or "",
            model=resp.model,
            tokens_prompt=resp.usage.prompt_tokens if resp.usage else 0,
            tokens_completion=resp.usage.completion_tokens if resp.usage else 0,
            cost=self._calc_cost(resp),
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        client = self._build_client()
        model = self.config.get("model", "gpt-4o-mini")
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        for m in messages:
            api_messages.append({"role": m.role, "content": m.content})

        stream = await client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    @staticmethod
    def _calc_cost(resp) -> float:
        """粗略估算成本（美元）"""
        if not resp.usage:
            return 0.0
        # GPT-4o-mini 定价
        prices = {
            "gpt-4o-mini": (0.15, 0.60),   # 输入/输出 每百万 token 美元
            "gpt-4o": (2.50, 10.00),
            "gpt-4-turbo": (10.00, 30.00),
        }
        model_key = resp.model
        for key, (p_in, p_out) in prices.items():
            if model_key.startswith(key):
                break
        else:
            p_in, p_out = 0.0, 0.0
        return (
            resp.usage.prompt_tokens / 1_000_000 * p_in
            + resp.usage.completion_tokens / 1_000_000 * p_out
        )
