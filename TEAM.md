# 🤖 WeChat Bot 开发小组

## 团队架构（单 Agent 全栈模式）

```
┌─────────────────────────────────────────┐
│          wechat-bot-dev 技能              │  ← 总控 Agent
│  (架构师 + 后端 + 前端 + DevOps + QA)     │
└─────────────────────────────────────────┘
```

一套技能、全部角色。开发时通过 `/wechat-bot-dev` 调用技能进入工作模式。

## 角色职责

| 角色 | 负责内容 |
|------|---------|
| 🏗️ **架构师** | 需求分析、技术方案、任务拆解、代码审查 |
| 💻 **后端** | Python/FastAPI/SQLAlchemy/AI 适配器/微信桥接 |
| 🎨 **前端** | Vue3/Element Plus/TypeScript/路由 |
| 🐳 **DevOps** | Docker/Docker Compose/CI/CD/环境配置 |
| 🧪 **QA** | 测试策略/pytest/回归验证/边界检查 |

## 工作规范

### 每次开发任务的流程

```
1. 分析 → 阅读相关代码，理解现有架构
2. 规划 → todo_write 列出具体步骤（两层级）
3. 执行 → 按步骤逐个实施（keep changes minimal）
4. 验证 → 每步完成后语法/逻辑/运行验证
5. 签收 → complete_step 记录证据
```

### 代码规范

- **后端**：Python 3.10+ / FastAPI async / SQLAlchemy 2.0 async
- **前端**：Vue3 Composition API / Element Plus / `<script setup lang="ts">`
- **容器**：Docker Compose 双服务（backend+frontend）
- **AI 适配器**：继承 `AIAdapter` → `AIFactory.register()` 注册
- **API 路由**：放在 `api/`，统一 `Depends(get_db)` 获取数据库

### 沟通原则

- 有架构决策时先提方案（2-4 个选项）让用户拍板
- 改数据库结构要同步更新 `models.py` + `init_db()`
- 改 API 要同步更新前端 `api/index.ts`
- 每次提交保持改动最小化，不搞大规模重构

## 迭代规划

### 迭代一（当前）：完善微信真实接入
- [ ] 修复 itchat-bridge 线程安全 + 自动重连
- [ ] 添加 Web 端扫码登录页面
- [ ] 完善 MockBridge 开发体验

### 迭代二：用户认证系统
- JWT 登录 + 注册
- API Key 鉴权中间件
- 前端登录页面 + 路由守卫

### 迭代三：质量提升
- TypeScript 接口类型
- Pinia 全局状态
- pytest 测试体系

### 迭代四：实时推送
- WebSocket 消息推送
- 前端实时聊天界面
- 消息已读/未读

### 迭代五：数据库升级
- Alembic 迁移
- PostgreSQL 支持
- 数据库管理页面
