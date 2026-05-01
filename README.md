# Easy Test - AI试卷生成系统

基于 DeepSeek AI 的智能试卷生成 Web 应用。上传课件资料（PDF/DOCX/PPT/PPTX），自动提取文本内容，调用 DeepSeek 大语言模型生成结构化复习试卷。

**v0.5.0** — MVP 可用版

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | Vue 3 (Composition API) + Vite 5 + vue-router 4 |
| 后端 | Node.js + Express |
| 数据库 | PostgreSQL 16 + Prisma ORM |
| 鉴权 | JWT + bcrypt |
| AI | DeepSeek API (`deepseek-chat`) |
| 文件解析 | pdf-parse, mammoth, officeparser, JSZip |
| PPT 转换 | LibreOffice Impress (headless) |
| 容器化 | Docker + Docker Compose |

## V0.5 功能

- **用户系统**：邮箱注册/登录，JWT 鉴权，token 自动恢复
- **数据持久化**：PostgreSQL + Prisma，10 张业务表
- **文件管理**：上传 PDF/DOCX/PPT/PPTX 自动入库，用户资源隔离
- **试卷历史**：生成记录永久保存，支持列表/详情/重新生成
- **题目拆分**：每道题独立存储，支持按题查询
- **额度控制**：默认 10 次生成额度，Prisma 事务防并发超扣
- **质量报告**：评分（0-100）、校验警告、知识点覆盖统计
- **前端路由**：6 个页面（首页/历史/详情/个人中心/登录/注册）
- **V1.0 预留**：微信登录/小程序/支付/对象存储字段已就绪

## 快速开始

### 前置要求

- Docker Desktop
- DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）

### 1. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，至少填入以下 3 项：
#   DEEPSEEK_API_KEY=sk-xxx
#   POSTGRES_PASSWORD=your_password
#   JWT_SECRET=随机生成64字符以上
```

### 2. Docker Compose 启动

```bash
docker compose up --build
```

启动顺序：postgres → backend（自动 migrate + 启动）→ frontend。首次构建约 5-8 分钟。

### 3. 初始化种子数据（可选）

```bash
docker compose exec backend npm run prisma:seed
```

### 4. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端界面 |
| http://localhost:3000/health | 后端健康检查 |

### 本地启动（无需 Docker）

```bash
# 1. 启动 PostgreSQL
docker compose up -d postgres

# 2. 后端
cd backend && cp .env.example .env && npm install
npx prisma migrate dev && npx prisma db seed
npm run dev

# 3. 前端
cd frontend && npm install && npm run dev
```

## 接口概览

| 模块 | 接口数 | 说明 |
|------|:---:|------|
| System | 2 | 健康检查、DeepSeek 连通测试 |
| Auth | 5 | 注册/登录/me/退出/微信占位 |
| Files | 4 | 上传(鉴权)/列表/详情/删除 |
| Papers | 4 | 生成(扣quota)/列表/详情/重新生成 |
| Quota | 2 | 额度查询/使用流水 |

> 详细文档见 [docs/API.md](docs/API.md)，完整 17 个接口含 curl 示例和错误码。

## 支持文件格式

| 格式 | 文本解析 | 图片 OCR | 依赖 |
|------|:---:|:---:|------|
| PDF | ✅ | - | pdf-parse（纯 JS） |
| DOCX | ✅ | - | mammoth（纯 JS） |
| PPTX | ✅ | ⚠️ 需 Vision API | officeparser + JSZip |
| PPT | ✅（转为 PPTX） | ⚠️ 需 Vision API | LibreOffice |

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|:---:|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | - | DeepSeek API 密钥 |
| `POSTGRES_PASSWORD` | ✅ | - | 数据库密码 |
| `JWT_SECRET` | ✅ | - | JWT 签名密钥（≥64字符） |
| `NODE_ENV` | ❌ | development | 运行环境 |
| `PORT` | ❌ | 3000 | 后端端口 |
| `DATABASE_URL` | ❌ | postgresql://easy_test:xxx@postgres:5432/easy_test | 数据库连接 |
| `POSTGRES_USER` | ❌ | easy_test | 数据库用户 |
| `POSTGRES_DB` | ❌ | easy_test | 数据库名 |
| `JWT_EXPIRES_IN` | ❌ | 24h | Token 有效期 |
| `JWT_REFRESH_SECRET` | ❌ | - | Refresh Token 密钥（V1.0） |
| `JWT_REFRESH_EXPIRES_IN` | ❌ | 7d | Refresh Token 有效期（V1.0） |
| `DEEPSEEK_API_URL` | ❌ | https://api.deepseek.com/v1/chat/completions | API 地址 |
| `UPLOAD_DIR` | ❌ | ./uploads | 上传目录 |
| `MAX_FILE_SIZE` | ❌ | 20971520（20MB） | 文件大小限制 |
| `DEFAULT_USER_QUOTA` | ❌ | 10 | 新用户默认额度 |
| `CORS_ORIGIN` | ❌ | http://localhost:5173 | CORS 白名单 |
| `WECHAT_APP_ID` | ❌ | - | 微信 AppID（V1.0） |
| `WECHAT_APP_SECRET` | ❌ | - | 微信 AppSecret（V1.0） |
| `STORAGE_PROVIDER` | ❌ | local | 存储后端（V1.0 可切 s3） |
| `LOCAL_STORAGE_DIR` | ❌ | ./uploads | 本地存储目录 |

## 前端页面

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | 邮箱 + 密码 |
| `/register` | 注册 | 昵称 + 邮箱 + 密码 |
| `/` | 首页 | 上传文件 + 配置 + 生成试卷 |
| `/papers` | 试卷历史 | 分页列表 |
| `/papers/:id` | 试卷详情 | 完整试卷 + 重新生成 |
| `/profile` | 个人中心 | 用户信息 + 额度 |

## V1.0 预留

详见 [docs/TASKS.md](docs/TASKS.md#v10-小程序预留说明)，关键预留点：

- `user_identities` 支持微信 openid/unionid
- `ClientType` 枚举已含 `wechat_mini_program`
- `POST /api/auth/wechat-mini-program-login` 占位接口
- `storage_provider`/`storage_key` 对象存储
- `plans` 表支付套餐
- `usage_records.client_type` 区分端用量

## 项目结构

```
easy test/
├── backend/
│   ├── prisma/
│   │   ├── schema.prisma      # 数据模型（10 表 5 枚举）
│   │   └── seed.js            # 种子数据
│   ├── src/
│   │   ├── config/            # 配置（env/fileTypes/paperConfig）
│   │   ├── middleware/        # auth + errorHandler
│   │   ├── routes/            # auth/files/papers/quota + V0.2 兼容
│   │   ├── services/          # 业务逻辑 + parsers + DeepSeek
│   │   ├── utils/             # response + errors
│   │   └── index.js           # 入口
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/               # apiClient fetch 封装
│       ├── components/        # NavBar + PaperContent
│       ├── stores/            # authStore reactive
│       ├── views/             # 6 个页面组件
│       ├── router.js          # vue-router
│       └── App.vue            # 布局壳
├── docs/                      # API/ROADMAP/TASKS/DEV_ENV
├── docker-compose.yml
└── CHANGELOG.md
```
