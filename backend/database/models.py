# 微信机器人 — 数据库模型
#
# SQLAlchemy 2.0 ORM 模型，使用 async 引擎 + aiosqlite。

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Helper ──

def _uuid() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.utcnow()


# ── AI 后端配置 ────────────────────────────────────────────

class AIProvider(Base):
    """AI 提供商配置（可创建多个，用于不同联系人）"""

    __tablename__ = "ai_providers"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="openai / claude / custom"
    )
    api_key: Mapped[str] = mapped_column(String(256), default="")
    base_url: Mapped[str] = mapped_column(String(256), default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_tokens: Mapped[int] = mapped_column(default=2048)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="ai_provider"
    )


# ── 联系人 ─────────────────────────────────────────────────

class Contact(Base):
    """微信联系人 / 群聊"""

    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uuid)
    wx_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(128), default="")
    remark: Mapped[str] = mapped_column(String(128), default="")
    is_group: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar: Mapped[str] = mapped_column(String(512), default="")
    # 关联的 AI 配置（None = 使用默认）
    ai_provider_id: Mapped[Optional[str]] = mapped_column(
        String(12), ForeignKey("ai_providers.id"), nullable=True
    )
    # 自动回复开关
    auto_reply: Mapped[bool] = mapped_column(Boolean, default=True)
    # 备注标签（JSON 数组，用于搜索过滤）
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    ai_provider: Mapped[Optional["AIProvider"]] = relationship(
        "AIProvider", back_populates="contacts"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="contact", cascade="all, delete-orphan"
    )


# ── 会话 ───────────────────────────────────────────────────

class Conversation(Base):
    """一次对话会话（包含多条消息）"""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uuid)
    contact_id: Mapped[str] = mapped_column(
        String(12), ForeignKey("contacts.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), default="")
    # 使用的 AI 提供者快照（历史记录用）
    ai_provider_id: Mapped[Optional[str]] = mapped_column(
        String(12), ForeignKey("ai_providers.id"), nullable=True
    )
    ai_provider_name: Mapped[str] = mapped_column(String(64), default="")
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    contact: Mapped["Contact"] = relationship(
        "Contact", back_populates="conversations"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )


# ── 消息 ───────────────────────────────────────────────────

class Message(Base):
    """单条消息"""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(12), ForeignKey("conversations.id"), nullable=False, index=True
    )
    # 'user'=收到, 'ai'=AI回复, 'system'=系统通知
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 原始消息（保留微信原始格式）
    raw_content: Mapped[str] = mapped_column(Text, default="")
    # 使用的 AI 提供者（AI 回复时记录）
    ai_provider_id: Mapped[Optional[str]] = mapped_column(
        String(12), ForeignKey("ai_providers.id"), nullable=True
    )
    ai_model: Mapped[str] = mapped_column(String(64), default="")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
