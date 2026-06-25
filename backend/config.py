# 微信机器人 — 配置管理
#
# 读取环境变量 / .env 文件，集中管理所有配置项。
# 使用 pydantic-settings 提供类型安全 + 自动补全。

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# ── 项目路径 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── FastAPI ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # ── 数据库 ──
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR / 'wechat_bot.db'}"
    # 同步 URL（Alembic / 工具用）
    DATABASE_URL_SYNC: str = f"sqlite:///{DATA_DIR / 'wechat_bot.db'}"

    # ── AI 默认配置 ──
    AI_DEFAULT_PROVIDER: Literal["openai", "claude", "custom"] = "openai"
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    # Anthropic Claude
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    # 自定义（兼容 OpenAI 格式）
    CUSTOM_API_KEY: str = ""
    CUSTOM_BASE_URL: str = ""
    CUSTOM_MODEL: str = ""

    # ── 微信 ──
    # 桥接类型：wkteam（iPad协议） / mock（模拟）
    WECHAT_BRIDGE_TYPE: str = "wkteam"
    # 是否在启动时自动连接
    WECHAT_AUTO_LOGIN: bool = True
    # 自动通过好友申请关键词过滤（逗号分隔，为空则全自动通过）
    WECHAT_AUTO_ACCEPT_KEYWORDS: str = ""

    # ── wkteam (Eyun iPad 协议) ──
    WKTEAM_API_URL: str = "http://125.122.152.142:9899"
    WKTEAM_TOKEN: str = ""         # Bearer Token (per account)
    WKTEAM_WX_ID: str = ""         # 当前登录的微信号 wxid

    # ── 自动回复 ──
    # 对私聊消息自动回复（@all = 所有联系人，逗号分隔列表）
    AUTO_REPLY_TARGETS: str = "@all"
    # 自动回复频率限制（每条消息之间最小秒数，0=不限）
    AUTO_REPLY_COOLDOWN: int = 3


settings = Settings(_env_file=PROJECT_ROOT / ".env", _env_file_encoding="utf-8")
