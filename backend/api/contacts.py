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

class ContactPublic(BaseModel):
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

@router.get("", response_model=list[ContactPublic])
async def list_contacts(
    search: str = Query("", description="搜索昵称/备注/微信ID"),
    group_only: bool = Query(False, description="仅群聊"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
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

    # 批量查会话数（一次查询替代 N+1）
    count_subq = (
        select(
            Conversation.contact_id,
            func.count(Conversation.id).label("conv_count"),
        )
        .group_by(Conversation.contact_id)
        .subquery()
    )

    stmt = stmt.outerjoin(count_subq, Contact.id == count_subq.c.contact_id).add_columns(
        func.coalesce(count_subq.c.conv_count, 0).label("conversation_count")
    )
    stmt = stmt.order_by(Contact.updated_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    rows = result.all()

    resp = []
    for c, conv_count in rows:
        resp.append(
            ContactPublic(
                **c.__dict__,
                conversation_count=conv_count,
                tags=c.tags or [],
            )
        )
    return resp


@router.get("/{contact_id}", response_model=ContactPublic)
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
    return ContactPublic(**c.__dict__, conversation_count=conv_count, tags=c.tags or [])


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
