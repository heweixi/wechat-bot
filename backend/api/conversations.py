# API 路由 — 会话与消息回溯

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import get_db
from database.models import Conversation, Message

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


# ── Schema ──

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    raw_content: str
    ai_model: str
    tokens_used: int
    cost: float
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    contact_id: str
    title: str
    ai_provider_id: str | None = None
    ai_provider_name: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True


# ── API ──

@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    contact_id: str | None = Query(None, description="按联系人过滤"),
    search: str | None = Query(None, description="按内容关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())

    if contact_id:
        stmt = stmt.where(Conversation.contact_id == contact_id)

    if search:
        keyword = f"%{search}%"
        subq = (
            select(Message.conversation_id)
            .where(Message.content.ilike(keyword))
            .distinct()
            .subquery()
        )
        stmt = stmt.where(Conversation.id.in_(select(subq.c.conversation_id)))

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    convs = list(result.scalars().all())

    # 批量查会话消息（N+1 → 1+1）
    if convs:
        conv_ids = [c.id for c in convs]
        msg_stmt = (
            select(Message)
            .where(Message.conversation_id.in_(conv_ids))
            .order_by(Message.created_at.asc())
        )
        msg_result = await db.execute(msg_stmt)
        all_msgs = list(msg_result.scalars().all())
        msgs_by_conv: dict[str, list[Message]] = {}
        for m in all_msgs:
            msgs_by_conv.setdefault(m.conversation_id, []).append(m)
    else:
        msgs_by_conv = {}

    resp = []
    for conv in convs:
        messages = msgs_by_conv.get(conv.id, [])[-5:]  # 仅取最近 5 条
        resp.append(
            ConversationResponse(
                **conv.__dict__,
                messages=[
                    MessageResponse(**m.__dict__) for m in messages
                ],
            )
        )
    return resp


@router.get("/{conv_id}", response_model=ConversationResponse)
async def get_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conv_id)
        .options(joinedload(Conversation.messages))
    )
    conv = result.unique().scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "会话不存在")
    return ConversationResponse(
        **conv.__dict__,
        messages=[MessageResponse(**m.__dict__) for m in conv.messages],
    )


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "会话不存在")
    await db.delete(conv)
    return {"ok": True}


@router.get("/search/messages", response_model=list[MessageResponse])
async def search_messages(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    contact_id: str | None = Query(None, description="按联系人过滤"),
    role: str | None = Query(None, description="user / assistant"),
    db: AsyncSession = Depends(get_db),
):
    """全文搜索消息记录"""
    stmt = select(Message).where(Message.content.ilike(f"%{keyword}%"))

    if contact_id:
        # 通过 conversation 过滤联系人
        conv_ids_subq = (
            select(Conversation.id)
            .where(Conversation.contact_id == contact_id)
            .subquery()
        )
        stmt = stmt.where(Message.conversation_id.in_(select(conv_ids_subq.c.id)))

    if role:
        stmt = stmt.where(Message.role == role)

    stmt = stmt.order_by(Message.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    return [MessageResponse(**m.__dict__) for m in result.scalars().all()]
