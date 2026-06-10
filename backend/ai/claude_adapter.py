# Anthropic Claude 适配器

from __future__ import annotations

from typing import AsyncIterator

from anthropic import AsyncAnthropic

from ai.base import AIAdapter, AIResponse, ChatMessage


class ClaudeAdapter(AIAdapter):
    """Anthropic Claude API 适配器"""

    @property
    def provider_type(self) -> str:
        return "claude"

    def _build_client(self) -> AsyncAnthropic:
        return AsyncAnthropic(
            api_key=self.config.get("api_key", ""),
            base_url=self.config.get(
                "base_url", "https://api.anthropic.com"
            ),
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AIResponse:
        client = self._build_client()
        model = self.config.get("model", "claude-sonnet-4-20250514")
        api_messages = []
        for m in messages:
            if m.role == "system":
                continue  # Claude 通过 system 参数传
            api_messages.append({"role": m.role, "content": m.content})

        resp = await client.messages.create(
            model=model,
            system=system_prompt or "",
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = resp.content[0].text if resp.content else ""
        return AIResponse(
            content=content,
            model=resp.model,
            tokens_prompt=resp.usage.input_tokens,
            tokens_completion=resp.usage.output_tokens,
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
        model = self.config.get("model", "claude-sonnet-4-20250514")
        api_messages = []
        for m in messages:
            if m.role == "system":
                continue
            api_messages.append({"role": m.role, "content": m.content})

        async with client.messages.stream(
            model=model,
            system=system_prompt or "",
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    @staticmethod
    def _calc_cost(resp) -> float:
        """Claude Sonnet 4 定价"""
        p_in = 3.0   # 每百万 token 美元
        p_out = 15.0
        return (
            resp.usage.input_tokens / 1_000_000 * p_in
            + resp.usage.output_tokens / 1_000_000 * p_out
        )
