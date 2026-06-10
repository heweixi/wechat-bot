# 🤖 WeChat Bot — 微信机器人

基于 FastAPI + SQLite + 多 AI 后端的微信自动聊天机器人。

## 功能

- ✅ **自动添加好友** — 自动通过好友申请
- ✅ **智能聊天** — 收到消息后 AI 自动回复
- ✅ **多 AI 后端** — 支持 OpenAI / Claude / 自定义 API（兼容 OpenAI 格式）
- ✅ **按人配置** — 每个联系人可绑定不同的 AI 配置
- ✅ **会话回溯** — 所有聊天记录持久化，按联系人/AI/关键词搜索
- ✅ **Web 管理界面** — 联系人管理、会话查看、AI 配置管理

## 🐳 Docker Compose 一键启动（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 2. 构建并启动所有服务
docker-compose up -d --build

# 3. 查看日志
docker-compose logs -f

# 4. 停止
docker-compose down
```

打开 http://localhost:3000 即可使用 Web 管理界面。

## 手动启动（开发模式）

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key 等配置
```

关键配置项：
| 变量 | 说明 |
|------|------|
| `OPENAI_API_KEY` | OpenAI / 兼容 API 的 Key |
| `OPENAI_MODEL` | 模型名（如 `gpt-4o-mini`） |
| `ANTHROPIC_API_KEY` | Claude 的 API Key（可选） |
| `AI_DEFAULT_PROVIDER` | 默认 AI：`openai` 或 `claude` |

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端跑在 http://localhost:8000

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端跑在 http://localhost:3000（开发模式，自动代理 /api 到后端）

### 4. 连接微信

> ⚠️ **非官方 API 有被封号风险**，建议用小号测试。

```bash
pip install itchat-uos
```

然后在 `.env` 中设置 `WECHAT_AUTO_LOGIN=true`，重启后端。  
扫码弹窗会显示在终端中（Docker 模式下需挂载终端）。

## 项目结构

```
wechat-bot/
├── docker-compose.yml        # 容器编排（一键启动全部服务）
├── .env.example              # 环境变量模板
├── backend/                  # Python FastAPI 后端
│   ├── app.py                # 应用入口
│   ├── config.py             # .env 配置管理
│   ├── Dockerfile            # 后端容器镜像
│   ├── requirements.txt
│   ├── database/             # SQLite + SQLAlchemy 2.0 async
│   │   ├── models.py         # ORM 模型（4 表）
│   │   └── __init__.py       # 数据库会话管理
│   ├── ai/                   # AI 适配器（工厂模式）
│   │   ├── base.py           # 抽象接口
│   │   ├── openai_adapter.py # OpenAI / 兼容 API
│   │   ├── claude_adapter.py # Anthropic Claude
│   │   └── factory.py        # 工厂 + 注册机制
│   ├── wechat/               # 微信桥接层
│   │   ├── bridge.py         # 桥接抽象接口
│   │   ├── itchat_bridge.py  # itchat-uos 真实微信
│   │   ├── mock_bridge.py    # 模拟桥接（开发/测试用）
│   │   └── handler.py        # 消息处理引擎（核心）
│   └── api/                  # RESTful API
│       ├── providers.py      # AI 配置 CRUD
│       ├── contacts.py       # 联系人管理
│       └── conversations.py  # 会话 + 消息 + 全文搜索
├── frontend/                 # Vue 3 + Element Plus SPA
│   ├── Dockerfile            # 多阶段构建：Node → Nginx
│   ├── nginx.conf            # 反向代理 /api → backend
│   ├── src/
│   │   ├── App.vue           # 布局（侧边栏导航）
│   │   ├── views/
│   │   │   ├── Contacts.vue          # 联系人列表
│   │   │   ├── Conversations.vue     # 会话列表
│   │   │   ├── ConversationDetail.vue # 消息查看/搜索
│   │   │   └── Providers.vue         # AI 配置管理
│   │   ├── router/index.ts
│   │   └── api/index.ts      # Axios API 封装
│   └── package.json
└── README.md
```

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 服务状态 |
| GET/POST | `/api/providers` | AI 提供商列表/创建 |
| GET/PUT/DELETE | `/api/providers/:id` | 单个 AI 提供商 |
| GET | `/api/contacts` | 联系人列表（支持搜索/群聊过滤） |
| PUT | `/api/contacts/:id/ai` | 设置联系人 AI 配置 |
| PUT | `/api/contacts/:id/auto_reply` | 开关自动回复 |
| GET | `/api/conversations` | 会话列表（支持搜索/联系人过滤） |
| GET | `/api/conversations/:id` | 会话详情（含全部消息） |
| DELETE | `/api/conversations/:id` | 删除会话 |
| GET | `/api/conversations/search/messages` | 全文搜索消息 |

## 容器架构

```
                      ┌──────────────┐
                      │   Nginx:80   │  ← 前端 SPA  + 反向代理
                      │  frontend/   │
                      └──────┬───────┘
                             │ /api/* 代理
                      ┌──────▼───────┐
                      │  FastAPI:8000 │  ← API + AI + 微信
                      │   backend/    │
                      └──────┬───────┘
                             │ SQLite
                      ┌──────▼───────┐
                      │   data/      │  ← 持久化卷
                      └──────────────┘
```
