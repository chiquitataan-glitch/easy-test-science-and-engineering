# 开发环境说明

## 服务架构

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | postgres:16-alpine | 5432 | PostgreSQL 数据库，volume 持久化 |
| backend | node:20-slim | 3000 | Express + Prisma + DeepSeek |
| frontend | node:20-slim | 5173 | Vue 3 + Vite 5 |

## Docker 启动顺序

```
docker compose up --build
  1. postgres 启动 → healthcheck pg_isready
  2. backend 启动（等待 postgres healthy）
     → prisma migrate deploy（自动建表）
     → npm start
  3. frontend 启动（等待 backend healthy）
```

## 数据库

### PostgreSQL

- 服务名：`postgres`
- 数据库：`easy_test`
- 默认用户：`easy_test`
- 密码：通过 `POSTGRES_PASSWORD` 环境变量设置
- 持久化：`pgdata` Docker volume

### Prisma

```bash
# 生成 Prisma Client
cd backend && npm run prisma:generate

# 开发环境 migration（生成迁移文件）
npm run prisma:migrate

# 生产/CI migration（仅执行）
npm run prisma:deploy

# 初始化种子数据
npm run prisma:seed

# 数据库管理界面
npm run prisma:studio
```

### Migration 工作流

```bash
# 修改 schema.prisma 后
npm run prisma:migrate -- --name describe_your_change
# 自动生成 migration/ 目录文件，提交到 Git

# Docker 启动时自动执行
# Dockerfile CMD: sh -c "npx prisma migrate deploy && npm start"
```

### Seed 数据

`prisma/seed.js` 默认插入：
- `prompt_versions`: generate-v1, selfcheck-v1

```bash
# Docker 内执行
docker compose exec backend npm run prisma:seed

# 本地执行
cd backend && npm run prisma:seed
```

## 环境变量

### 必填变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-xxx` |
| `POSTGRES_PASSWORD` | 数据库密码 | `change_me` |
| `JWT_SECRET` | JWT 签名密钥（≥64字符） | 随机生成 |

### 完整变量列表

```bash
# 见 backend/.env.example
# 共 19 个变量，涵盖数据库、JWT、上传、额度、微信预留等
```

### JWT_SECRET 生成

```bash
# Linux/macOS
openssl rand -hex 64

# Windows PowerShell
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 64 | % {[char]$_})
```

## Docker网络说明

- 前端通过 Vite 代理访问后端：`http://backend:3000`
- 后端访问数据库：`postgresql://easy_test:xxx@postgres:5432/easy_test`
- 浏览器访问前端：`http://localhost:5173`
- 浏览器访问后端：`http://localhost:3000`

## Volumes

| 挂载 | 用途 |
|------|------|
| `./backend:/app` | 后端代码热重载 |
| `./backend/uploads:/app/uploads` | 上传文件持久化 |
| `./frontend:/app` | 前端代码热重载 |
| `pgdata:/var/lib/postgresql/data` | 数据库数据持久化 |

## 端口映射

| 宿主 | 容器 | 服务 |
|------|------|------|
| 5173 | 5173 | 前端 Vite |
| 3000 | 3000 | 后端 Express |
| 5432 | 5432 | PostgreSQL |

## 系统依赖说明

### LibreOffice（解析 .ppt 文件）

后端 Docker 镜像包含 LibreOffice Impress，用于将老格式 `.ppt` 文件转换为 `.pptx` 后再提取文本。

- Docker 环境：已内置，`docker compose up --build` 自动安装
- 本地环境：需手动安装 LibreOffice

### 本地开发（无需 Docker）

```bash
# 1. 启动 PostgreSQL（本地或 Docker 仅启动 postgres）
docker compose up -d postgres

# 2. 后端
cd backend && cp .env.example .env && npm install
npx prisma migrate dev && npx prisma db seed
npm run dev

# 3. 前端
cd frontend && npm install && npm run dev
```

## 文件上传说明

| 格式 | 文本解析 | 图片 OCR | 依赖 |
|------|:---:|:---:|------|
| PDF | ✅ | - | pdf-parse（纯 JS） |
| DOCX | ✅ | - | mammoth（纯 JS） |
| PPTX | ✅ | ⚠️ 需 Vision API | officeparser + JSZip |
| PPT | ✅（转为 PPTX） | ⚠️ 需 Vision API | LibreOffice |

### 图片 OCR 说明

- **API**：`POST /v1/chat/completions`，`image_url` 消息格式
- **限制**：每文件最多 20 张，单张 ≤ 5MB
- **降级**：Vision 不可用时优雅跳过，不影响纯文本解析
