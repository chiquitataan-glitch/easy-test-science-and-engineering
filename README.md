# Easy Test — AI 智能试卷生成系统

基于大语言模型与 RAG（检索增强生成）的智能试卷生成平台。上传课件资料（PDF/DOCX/PPT/PPTX），系统自动提取文本、分类分块、向量化存储，调用 DeepSeek 大模型生成结构化复习试卷，支持 DOCX 导出。

**v0.6.0** — Python 后端 + RAG 知识管道

## 技术栈

| 层 | v0.5（旧版） | v0.6（当前） |
|------|------------|------------|
| 前端 | Vue 3 + Vite 5 + vue-router 4 | 同左 |
| 后端 | Node.js + Express | **Python FastAPI** |
| 数据库 | PostgreSQL 16 + Prisma ORM | PostgreSQL 16 + **SQLAlchemy 2.0（异步）** |
| 向量存储 | — | **ChromaDB** |
| LLM 框架 | 直接调用 DeepSeek API | **LangChain + LangChain-DeepSeek** |
| 鉴权 | JWT + bcrypt | JWT + python-jose + passlib |
| 文件解析 | pdf-parse, mammoth, officeparser | **PyPDF2, python-docx, python-pptx, mammoth** |
| 容器化 | Docker + Docker Compose | 同左 + Nginx 反向代理 |

## 核心功能

### 文件处理
- **多格式解析**：PDF、DOCX、PPT、PPTX 文本提取
- **智能分类**：自动识别文档学科类别
- **智能分块**：按语义边界切分文档，保留上下文完整性
- **向量嵌入**：分块内容向量化，写入 ChromaDB 向量数据库

### 试卷生成
- **RAG 增强**：基于向量检索召回最相关知识点，注入 LLM 上下文
- **多题型支持**：单选题、多选题、填空题、简答题、论述题
- **灵活配置**：各题型数量、分值、难度比例可自定义
- **Few-shot 示例**：内置少样本示例提升生成质量
- **DOCX 导出**：一键导出标准 Word 格式试卷

### 用户系统
- **注册/登录**：邮箱 + 密码注册登录，JWT 鉴权
- **额度控制**：免费用户 20 次生成额度，数据库事务防并发超扣
- **数据隔离**：用户资源完全隔离，只能访问自己的文件和试卷
- **试卷历史**：生成记录永久保存，支持列表、详情、重新生成

### 部署运维
- **Docker 一键部署**：`docker compose up -d`
- **Nginx 反向代理**：前端静态资源 + API 代理 + SSL 预留
- **数据库迁移**：Alembic 自动迁移
- **健康检查**：`/health` 端点 + 容器健康检查

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                      用户浏览器                            │
└─────────────┬────────────────────────────────────────────┘
              │ HTTP
┌─────────────▼────────────────────────────────────────────┐
│                  Nginx (:80/:443)                         │
│         静态资源 /  API 代理 / SSL                         │
└──────┬────────────────────────────────┬──────────────────┘
       │ /api/*                         │ /*
┌──────▼──────────┐          ┌──────────▼──────────┐
│  FastAPI :8000  │          │ 前端静态文件 (dist)   │
│  Python 后端     │          │  Vue 3 SPA           │
└──────┬──────────┘          └─────────────────────┘
       │
       ├──► PostgreSQL 16    — 用户/文件/试卷/额度/日志
       ├──► ChromaDB         — 文档向量存储与检索
       └──► DeepSeek API     — LLM 推理（通过 LangChain）
```

### 文件处理管道

```
上传文件 → 文本解析 → 学科分类 → 语义分块 → 向量嵌入 → ChromaDB
                                                        │
                                                        ▼
                                                   准备就绪 (ready)
```

### 试卷生成管道

```
用户配置 ──► RAG 检索相关块 ──► 构建 Prompt ──► DeepSeek 推理
                                                    │
                     ┌──────────────────────────────┘
                     ▼
           JSON 解析 → 校验 → 入库 → 返回 / DOCX 导出
```

## 快速开始

### 前置要求

- Docker Desktop
- DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）

### 1. 配置环境变量

```bash
cp backend-py/.env.example backend-py/.env
```

编辑 `backend-py/.env`，填入必填项：

```env
DEEPSEEK_API_KEY=sk-你的密钥
DATABASE_URL=postgresql+asyncpg://easy_test:你的密码@postgres:5432/easy_test
JWT_SECRET=随机生成64位以上的字符串
```

### 2. 启动服务

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

启动顺序：postgres → backend（FastAPI）→ nginx。首次构建约 5–8 分钟。

### 3. 访问

| 地址 | 说明 |
|------|------|
| `http://localhost` | 前端界面 |
| `http://localhost/api/health` | 后端健康检查 |
| `http://localhost/docs` | Swagger API 文档 |

### 本地开发（无需 Docker 全部服务）

```bash
# 1. 启动 PostgreSQL（Docker）
docker compose -f docker-compose.prod.yml up -d postgres

# 2. 启动 Python 后端
cd backend-py
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env        # 编辑配置
uvicorn app.main:app --reload --port 8000

# 3. 启动前端
cd frontend
npm install
npm run dev
```

## API 概览

| 模块 | 接口数 | 说明 |
|------|:---:|------|
| System | 2 | 健康检查、DeepSeek 连通测试 |
| Auth | 5 | 注册/登录/当前用户/退出/微信预留 |
| Files | 5 | 上传/列表/详情/删除/重解析 |
| Papers | 5 | 生成/列表/详情/重新生成/DOCX 导出 |
| Quota | 2 | 额度查询/使用流水 |
| Admin | 1 | 管理接口 |

> 完整接口文档请访问运行中的 Swagger UI：`http://localhost/docs`

## 支持的文件格式

| 格式 | 文本解析 | 依赖 |
|------|:---:|------|
| PDF | ✅ | PyPDF2 |
| DOCX | ✅ | python-docx / mammoth |
| PPTX | ✅ | python-pptx |
| PPT | ⚠️ | 需转换为 PPTX 后解析 |

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|:---:|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | — | DeepSeek API 密钥 |
| `DATABASE_URL` | ✅ | — | PostgreSQL 连接串（asyncpg） |
| `JWT_SECRET` | ✅ | — | JWT 签名密钥（≥64字符） |
| `NODE_ENV` | ❌ | development | 运行环境 |
| `JWT_EXPIRES_IN` | ❌ | 24h | Token 有效期 |
| `DEEPSEEK_BASE_URL` | ❌ | `https://api.deepseek.com/v1` | API 地址 |
| `UPLOAD_DIR` | ❌ | /data/uploads | 上传目录 |
| `CHROMA_PERSIST_DIR` | ❌ | /data/chroma | ChromaDB 持久化目录 |
| `MAX_FILE_SIZE` | ❌ | 20971520（20MB） | 文件大小限制 |
| `DEFAULT_FREE_GENERATIONS` | ❌ | 20 | 新用户免费生成额度 |
| `CORS_ORIGIN` | ❌ | `http://localhost:5173` | CORS 白名单 |
| `WECHAT_APP_ID` | ❌ | — | 微信 AppID（预留） |
| `WECHAT_APP_SECRET` | ❌ | — | 微信 AppSecret（预留） |

## 前端页面

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | 邮箱 + 密码 |
| `/register` | 注册 | 昵称 + 邮箱 + 密码 |
| `/` | 首页 | 上传文件 + 配置 + 生成试卷 |
| `/papers` | 试卷历史 | 分页列表 |
| `/papers/:id` | 试卷详情 | 完整试卷 + 重新生成 + DOCX 导出 |
| `/profile` | 个人中心 | 用户信息 + 额度 |

## 项目结构

```
easy-test/
├── backend/                    # Node.js 后端（v0.5 旧版，保留兼容）
│   ├── prisma/
│   │   ├── schema.prisma       # 数据模型
│   │   ├── migrations/         # Prisma 迁移文件
│   │   └── seed.js             # 种子数据
│   ├── src/
│   │   ├── config/             # 配置
│   │   ├── middleware/         # 中间件
│   │   ├── routes/             # 路由
│   │   ├── services/           # 业务逻辑 + 解析器
│   │   ├── utils/              # 工具函数
│   │   └── index.js
│   ├── Dockerfile
│   └── .env.example
├── backend-py/                 # Python FastAPI 后端（v0.6 当前版）
│   ├── app/
│   │   ├── api/                # auth / files / papers / quota / admin
│   │   ├── middleware/         # auth / response
│   │   ├── models/             # SQLAlchemy 数据模型
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 业务服务
│   │   │   ├── auth_service.py       # 注册/登录/JWT
│   │   │   ├── file_service.py       # 上传/解析/管理
│   │   │   ├── paper_generator.py    # 试卷生成
│   │   │   ├── quota_service.py      # 额度管理
│   │   │   ├── classifier.py         # 文档分类
│   │   │   ├── chunker.py            # 语义分块
│   │   │   ├── embedder.py           # 向量嵌入
│   │   │   ├── chroma_store.py       # ChromaDB 操作
│   │   │   ├── rag_engine.py         # RAG 检索引擎
│   │   │   └── docx_exporter.py      # DOCX 导出
│   │   ├── config.py           # 全局配置
│   │   ├── database.py         # 数据库连接
│   │   └── main.py             # FastAPI 入口
│   ├── prompts/
│   │   └── fewshot_examples.json  # Few-shot 示例
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── api/                # API 客户端
│       ├── components/         # 公共组件
│       ├── stores/             # 状态管理
│       ├── views/              # 页面组件
│       ├── router.js           # 路由配置
│       └── App.vue
├── nginx/                      # Nginx 配置
│   ├── Dockerfile
│   ├── nginx.conf
│   └── ssl/                    # SSL 证书（预留）
├── docs/                       # 文档
├── data/                       # 数据目录（运行时）
│   ├── uploads/                # 上传文件
│   ├── chroma/                 # ChromaDB 向量数据
│   └── pgdata/                 # PostgreSQL 数据
├── docker-compose.prod.yml     # 生产环境编排
├── deploy.sh                   # 部署脚本
├── CHANGELOG.md                # 更新日志
└── README.md
```

## 路线图

### 已完成
- [x] v0.1 — 基础文件上传与 DeepSeek 试卷生成
- [x] v0.2 — PPTX/PPT 支持、题型配置、质量评分、知识点提取
- [x] v0.5 — 用户系统、PostgreSQL 持久化、额度控制、前端完整页面
- [x] v0.6 — Python FastAPI 后端、RAG 知识管道、ChromaDB、DOCX 导出

### 计划中
- [ ] v0.7 — 管理后台、会员套餐、微信小程序登录
- [ ] v1.0 — 微信小程序端、对象存储、支付集成、Refresh Token

## License

MIT
