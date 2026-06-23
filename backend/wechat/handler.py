# 消息自动化处理 — 接收微信消息 → AI 处理 → 回复
#
# 核心逻辑：收到消息 → 查找/创建会话 → 调用 AI → 回复 → 保存记录

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai import AIFactory
from ai.base import ChatMessage
from config import settings
from database.models import AIProvider, Contact, Conversation, Message
from wechat.bridge import WeChatBridge, WeChatMessage

logger = logging.getLogger(__name__)


class MessageHandler:
    """消息处理核心"""

    def __init__(self, bridge: WeChatBridge, db_factory):
        self.bridge = bridge
        self.db_factory = db_factory
        self._cooldowns: dict[str, float] = {}  # wx_id -> last_reply_time
        bridge.on_message = self._on_message
        bridge.on_friend_request = self._on_friend_request

    # ── 收到消息 ──

    async def _on_message(self, msg: WeChatMessage):
        """收到微信消息 → AI → 回复"""
        # 频率限制
        if not self._check_cooldown(msg.from_wx):
            logger.debug(f"频率限制，跳过: {msg.from_wx}")
            return

        async with self.db_factory() as db:
            # 查找或创建联系人
            contact = await self._get_or_create_contact(db, msg)
            if not contact or not contact.auto_reply:
                return

            # 查找或创建会话
            conv = await self._get_or_create_conversation(db, contact, msg)

            # 保存用户消息
            db.add(
                Message(
                    conversation_id=conv.id,
                    role="user",
                    content=msg.content,
                    raw_content=msg.content,
                )
            )
            conv.message_count += 1
            await db.flush()

            # 获取历史消息（最近 20 条作为上下文）
            history = await self._get_history(db, conv.id, limit=20)

            # 获取 AI 配置
            ai_config = await self._get_ai_config(db, contact)

            # 调用 AI
            try:
                adapter = AIFactory.create(ai_config)
                ai_messages = [ChatMessage(role=m.role, content=m.content) for m in history]
                ai_messages.append(ChatMessage(role="user", content=msg.content))

                response = await adapter.chat(
                    messages=ai_messages[-10:],  # 取最近 10 条作为上下文
                    system_prompt=ai_config.get("system_prompt", ""),
                    temperature=ai_config.get("temperature", 0.7),
                    max_tokens=ai_config.get("max_tokens", 2048),
                )

                # 发送回复
                await self.bridge.send_message(msg.from_wx, response.content)

                # 保存 AI 回复
                db.add(
                    Message(
                        conversation_id=conv.id,
                        role="assistant",
                        content=response.content,
                        ai_provider_id=ai_config.get("id"),
                        ai_model=response.model,
                        tokens_used=response.tokens_prompt + response.tokens_completion,
                        cost=response.cost,
                    )
                )
                conv.message_count += 1
                await db.commit()

            except Exception as e:
                logger.exception(f"AI 调用失败: {e}")
                # 回复错误提示
                await self.bridge.send_message(
                    msg.from_wx, f"🤖 AI 回复失败: {str(e)[:100]}"
                )

    # ── 好友申请 ──

    async def _on_friend_request(self, msg: WeChatMessage):
        """自动通过好友申请"""
        try:
            ok = await self.bridge.accept_friend(msg.from_wx, msg.content)
            if ok:
                logger.info(f"已通过好友申请: {msg.from_nick} ({msg.from_wx})")
        except Exception:
            logger.exception("通过好友申请失败")

    # ── 辅助方法 ──

    def _check_cooldown(self, wx_id: str) -> bool:
        cooldown = settings.AUTO_REPLY_COOLDOWN
        if cooldown <= 0:
            return True
        now = time.time()
        last = self._cooldowns.get(wx_id, 0)
        if now - last < cooldown:
            return False
        self._cooldowns[wx_id] = now
        return True

    async def _get_or_create_contact(
        self, db: AsyncSession, msg: WeChatMessage
    ) -> Optional[Contact]:
        """查找或创建联系人"""
        stmt = select(Contact).where(Contact.wx_id == msg.from_wx)
        result = await db.execute(stmt)
        contact = result.scalar_one_or_none()

        if not contact:
            # 获取默认 AI 配置
            default_ai = await self._get_default_ai(db)
            contact = Contact(
                wx_id=msg.from_wx,
                nickname=msg.from_nick,
                is_group=msg.is_group,
                ai_provider_id=default_ai.id if default_ai else None,
            )
            db.add(contact)
            await db.flush()
            logger.info(f"新联系人: {msg.from_nick} ({msg.from_wx})")

        return contact

    async def _get_or_create_conversation(
        self, db: AsyncSession, contact: Contact, msg: WeChatMessage
    ) -> Conversation:
        """获取或创建当前会话（每日一会话，按日期分组）"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        stmt = (
            select(Conversation)
            .where(Conversation.contact_id == contact.id)
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        conv = result.scalar_one_or_none()

        if conv and conv.created_at.strftime("%Y-%m-%d") == today:
            return conv

        # 创建新会话
        ai_name = contact.ai_provider.nickname if contact.ai_provider else "default"
        conv = Conversation(
            contact_id=contact.id,
            title=f"会话 {today}",
            ai_provider_id=contact.ai_provider_id,
            ai_provider_name=ai_name,
        )
        db.add(conv)
        await db.flush()
        return conv

    async def _get_history(
        self, db: AsyncSession, conv_id: str, limit: int = 20
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _get_ai_config(self, db: AsyncSession, contact: Contact) -> dict:
        """获取联系人绑定的 AI 配置"""
        if contact.ai_provider_id:
            stmt = select(AIProvider).where(AIProvider.id == contact.ai_provider_id)
            result = await db.execute(stmt)
            provider = result.scalar_one_or_none()
            if provider and provider.enabled:
                return {
                    "id": provider.id,
                    "provider_type": provider.provider_type,
                    "api_key": provider.api_key,
                    "base_url": provider.base_url,
                    "model": provider.model,
                    "system_prompt": provider.system_prompt,
                    "temperature": provider.temperature,
                    "max_tokens": provider.max_tokens,
                }

        # 返回默认配置
        defaults = {
            "id": None,
            "provider_type": settings.AI_DEFAULT_PROVIDER,
            "api_key": settings.OPENAI_API_KEY,
            "base_url": settings.OPENAI_BASE_URL,
            "model": settings.OPENAI_MODEL,
            "system_prompt": "",
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        if settings.AI_DEFAULT_PROVIDER == "claude":
            defaults["api_key"] = settings.ANTHROPIC_API_KEY
            defaults["base_url"] = settings.ANTHROPIC_BASE_URL
            defaults["model"] = settings.ANTHROPIC_MODEL
        return defaults

    async def _get_default_ai(self, db: AsyncSession) -> Optional[AIProvider]:
        stmt = select(AIProvider).where(AIProvider.is_default == True)  # noqa: E712
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
