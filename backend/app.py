# 微信机器人 — FastAPI 应用入口

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ai import AIFactory
from config import settings
from database import async_session_factory, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── 全局桥接实例 ──

_bridge_instance = None


def get_bridge():
    """获取当前微信桥接实例（API 路由使用）"""
    return _bridge_instance




def set_bridge(bridge):
    global _bridge_instance
    _bridge_instance = bridge


_bridge_task = None


async def start_bridge():
    """手动/自动启动微信桥接（可被 API 调用）"""
    global _bridge_task
    if _bridge_task and not _bridge_task.done():
        logger.info("桥接已在运行，跳过")
        return False
    _bridge_task = asyncio.create_task(_start_wechat())
    # 等 2 秒让桥接初始化
    await asyncio.sleep(2)
    bridge = get_bridge()
    return bridge is not None


async def _seed_default_provider():
    """启动时：若数据库无 AI 配置，从 .env 自动创建默认"""
    from database.models import AIProvider
    from database import sync_engine
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    with Session(sync_engine) as db:
        existing = db.execute(select(AIProvider)).scalar_one_or_none()
        if existing:
            logger.info(f"数据库已有 AI 配置: {existing.name}，跳过自动创建")
            return

        if not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY:
            logger.info("未配置任何 API Key，跳过自动创建 AI 配置")
            return

        if settings.OPENAI_API_KEY:
            provider = AIProvider(
                name="默认 OpenAI",
                provider_type="openai",
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                model=settings.OPENAI_MODEL,
                is_default=True,
            )
        elif settings.ANTHROPIC_API_KEY:
            provider = AIProvider(
                name="默认 Claude",
                provider_type="claude",
                api_key=settings.ANTHROPIC_API_KEY,
                base_url=settings.ANTHROPIC_BASE_URL,
                model=settings.ANTHROPIC_MODEL,
                is_default=True,
            )
        else:
            return

        db.add(provider)
        db.commit()
        logger.info(f"已自动创建默认 AI 配置: {provider.name} ({provider.model})")


# ── 生命周期 ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭"""
    logger.info("初始化数据库...")
    init_db()
    await _seed_default_provider()

    if settings.WECHAT_AUTO_LOGIN:
        asyncio.create_task(start_bridge())

    logger.info(f"服务启动: http://{settings.HOST}:{settings.PORT}")
    yield

    bridge = get_bridge()
    if bridge:
        await bridge.logout()
    logger.info("服务已关闭")


async def _start_wechat():
    """后台启动微信桥接"""
    try:
        # 尝试真实桥接，失败则回退模拟
        bridge = None
        try:
            import itchat  # noqa: F401

            from wechat.itchat_bridge import ItChatBridge

            bridge = ItChatBridge()
            logger.info("使用 itchat-uos 桥接")
        except ImportError:
            from wechat.mock_bridge import MockBridge

            bridge = MockBridge()
            logger.warning("itchat-uos 未安装，使用 MockBridge（模拟模式）")

        from wechat.handler import MessageHandler

        MessageHandler(bridge, async_session_factory)
        set_bridge(bridge)

        ok = await bridge.login()
        if ok:
            logger.info("微信桥接已启动")
            await bridge.run_forever()
        else:
            logger.error("微信桥接启动失败")
    except Exception:
        logger.exception("微信桥接启动异常")


# ── FastAPI ──

app = FastAPI(
    title="WeChat Bot",
    description="微信机器人 — AI 自动回复 + 会话管理",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 路由注册 ──

from api.providers import router as providers_router
from api.contacts import router as contacts_router
from api.conversations import router as conversations_router
from api.wechat import router as wechat_router

app.include_router(providers_router)
app.include_router(contacts_router)
app.include_router(conversations_router)
app.include_router(wechat_router)


@app.get("/api/status")
async def get_status():
    bridge = get_bridge()
    return {
        "status": "running",
        "wechat_logged_in": bridge.is_logged_in() if bridge else False,
        "wechat_bridge_type": (
            "itchat" if bridge and hasattr(bridge, "get_qrcode_path") else
            "mock" if bridge else None
        ),
        "connected": bridge is not None,
    }


# ── 静态文件（前端构建产物） ──

try:
    frontend_dist = settings.PROJECT_ROOT / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_dist), html=True),
            name="frontend",
        )
except Exception:
    pass


# ── 入口 ──

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
