# 微信机器人 — FastAPI 应用入口

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import async_session_factory, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── 生命周期 ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭"""
    # 启动
    logger.info("初始化数据库...")
    init_db()
    logger.info(f"服务启动: http://{settings.HOST}:{settings.PORT}")

    if settings.WECHAT_AUTO_LOGIN:
        asyncio.create_task(_start_wechat())

    yield

    # 关闭
    if hasattr(app.state, "bridge") and app.state.bridge:
        await app.state.bridge.logout()
    logger.info("服务已关闭")


async def _start_wechat():
    """后台启动微信桥接"""
    try:
        from wechat.mock_bridge import MockBridge
        from wechat.handler import MessageHandler

        bridge = MockBridge()
        MessageHandler(bridge, async_session_factory)
        await bridge.login()

        # 挂到 app.state 供 API 查询
        import fastapi
        app = fastapi.request.lifespan()
        # 简单方案：用全局变量
        _store_bridge(bridge)

        await bridge.run_forever()
    except Exception:
        logger.exception("微信桥接启动失败")


_bridge_instance = None


def _store_bridge(bridge):
    global _bridge_instance
    _bridge_instance = bridge


def get_bridge():
    return _bridge_instance


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

app.include_router(providers_router)
app.include_router(contacts_router)
app.include_router(conversations_router)


@app.get("/api/status")
async def get_status():
    bridge = get_bridge()
    return {
        "status": "running",
        "wechat_logged_in": bridge.is_logged_in() if bridge else False,
    }


# ── 静态文件（前端构建产物） ──

try:
    frontend_dist = settings.PROJECT_ROOT / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
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
