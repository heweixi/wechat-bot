# 数据库会话管理

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from config import settings
from database.models import Base


# ── 异步引擎（FastAPI 中使用） ─────────────────────────────

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)

async_session_factory = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入用"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── 同步引擎（初始化、脚本用） ─────────────────────────────

sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)


def init_db():
    """创建所有表（首次运行）"""
    Base.metadata.create_all(sync_engine)


# ── 快速 ──

__all__ = ["async_engine", "async_session_factory", "get_db", "sync_engine", "init_db"]
