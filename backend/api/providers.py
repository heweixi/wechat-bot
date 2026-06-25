# API 路由 — AI 提供商管理

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from database.models import AIProvider

router = APIRouter(prefix="/api/providers", tags=["AI Providers"])


# ── Schema ──

class ProviderCreate(BaseModel):
    name: str
    provider_type: str = "openai"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
    is_default: bool = False


class ProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    is_default: bool | None = None
    enabled: bool | None = None


class ProviderPublic(BaseModel):
    """对外返回（不暴露 api_key）"""
    id: str
    name: str
    provider_type: str
    has_key: bool = False
    base_url: str
    model: str
    system_prompt: str
    temperature: float
    max_tokens: int
    is_default: bool
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, provider: AIProvider) -> "ProviderPublic":
        return cls(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            has_key=bool(provider.api_key),
            base_url=provider.base_url,
            model=provider.model,
            system_prompt=provider.system_prompt,
            temperature=provider.temperature,
            max_tokens=provider.max_tokens,
            is_default=provider.is_default,
            enabled=provider.enabled,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )


# ── API ──

@router.get("", response_model=list[ProviderPublic])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProvider).order_by(AIProvider.created_at.desc()))
    providers = result.scalars().all()
    return [ProviderPublic.from_orm(p) for p in providers]


@router.post("", response_model=ProviderPublic, status_code=201)
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)):
    provider = AIProvider(**data.model_dump())
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return ProviderPublic.from_orm(provider)


@router.get("/{provider_id}", response_model=ProviderPublic)
async def get_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "AI 提供商不存在")
    return ProviderPublic.from_orm(provider)


@router.put("/{provider_id}", response_model=ProviderPublic)
async def update_provider(
    provider_id: str, data: ProviderUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "AI 提供商不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(provider, key, value)

    await db.flush()
    await db.refresh(provider)
    return ProviderPublic.from_orm(provider)


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AIProvider).where(AIProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "AI 提供商不存在")
    await db.delete(provider)
    return {"ok": True}
