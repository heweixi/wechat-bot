# API 路由 — 联系人管理

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import get_db
from database.models import Contact, Conversation, Message

router = APIRouter(prefix="/api/contacts", tags=["Contacts"])


# ── Schema ──

class ContactResponse(BaseModel):
    id: str
    wx_id: str
    nickname: str
    remark: str
    is_group: bool
    avatar: str
    ai_provider_id: str | None = None
    auto_reply: bool
    tags: list
    created_at: datetime
    updated_at: datetime
    conversation_count: int = 0

    class Config:
        from_attributes = True


# ── API ──

@router.get("", response_model=list[ContactResponse])
async def list_contacts(
    search: str = Query("", description="搜索昵称/备注/微信ID"),
    group_only: bool = Query(False, description="仅群聊"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Contact)
    if search:
        keyword = f"%{search}%"
        stmt = stmt.where(
            or_(
                Contact.nickname.ilike(keyword),
                Contact.remark.ilike(keyword),
                Contact.wx_id.ilike(keyword),
            )
        )
    if group_only:
        stmt = stmt.where(Contact.is_group == True)  # noqa: E712

    stmt = stmt.order_by(Contact.updated_at.desc())
    result = await db.execute(stmt)
    contacts = list(result.scalars().all())

    # 统计每个联系人的会话数
    resp = []
    for c in contacts:
        count_result = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.contact_id == c.id
            )
        )
        conv_count = count_result.scalar() or 0
        resp.append(
            ContactResponse(
                **c.__dict__,
                conversation_count=conv_count,
                tags=c.tags or [],
            )
        )
    return resp


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "联系人不存在")

    count_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.contact_id == c.id)
    )
    conv_count = count_result.scalar() or 0
    return ContactResponse(**c.__dict__, conversation_count=conv_count, tags=c.tags or [])


@router.put("/{contact_id}/ai")
async def set_contact_ai(
    contact_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """设置联系人绑定的 AI 提供商"""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "联系人不存在")
    c.ai_provider_id = data.get("ai_provider_id")
    await db.flush()
    return {"ok": True}


@router.put("/{contact_id}/auto_reply")
async def set_auto_reply(
    contact_id: str, data: dict, db: AsyncSession = Depends(get_db)
):
    """开关自动回复"""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "联系人不存在")
    c.auto_reply = data.get("auto_reply", True)
    await db.flush()
    return {"ok": True}
