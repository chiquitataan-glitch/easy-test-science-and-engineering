# Changelog

## [0.5.0] - 2026-05-02

### Added
- 用户注册/登录（JWT + bcrypt），`POST /api/auth/register`、`POST /api/auth/login`
- `GET /api/auth/me` 当前用户信息、`POST /api/auth/logout` 退出
- `POST /api/auth/wechat-mini-program-login` V1.0 预留占位（返回 501）
- `requireAuth` / `optionalAuth` Express 鉴权中间件
- JWT token payload 包含 `sub`/`userId`/`clientType`/`identityProvider`
- PostgreSQL 16 + Prisma ORM（10 张表，5 个枚举）
- `users` + `user_identities` 用户身份分离模型（支持 password/wechat/phone）
- `uploaded_files` 文件记录持久化，用户资源隔离
- `generated_papers` 试卷持久化，`paper_json`/`config`/`quality_report` JSONB 存储
- `paper_questions` 题目拆分入库
- `user_quotas` + `usage_records` 额度控制，Prisma 事务防并发超扣
- `generation_logs` 生成日志（duration/error/token_usage）
- `prompt_versions` 表 + seed 脚本
- `plans` 表 V1.0 预留
- `POST /api/files/upload`（鉴权版）上传入库 + 自动解析
- `GET /api/files` 文件列表、`GET /api/files/:id` 详情、`DELETE /api/files/:id` 删除
- `POST /api/papers/generate` 生成入库 + 关联文件
- `GET /api/papers` 历史列表（分页）、`GET /api/papers/:id` 完整详情
- `POST /api/papers/:id/regenerate` 重新生成（`original_paper_id` 关联）
- `GET /api/quota/me` 额度查询、`GET /api/quota/usage-records` 使用流水
- 统一响应工具（`successResponse`/`errorResponse`）+ 13 个错误码
- 全局错误处理中间件 + `AppError` 类体系
- 环境变量校验（启动时检查必填项）
- 前端 `/login`、`/register` 页面
- 前端 `/papers` 历史列表、`/papers/:id` 详情 + 重新生成
- 前端 `/profile` 个人中心 + 额度进度条
- 前端 NavBar（登录态/用户名/quota/退出）+ 路由守卫 + localStorage 恢复
- `apiClient` fetch 封装（自动 Authorization + 401 跳转）
- `PaperContent.vue` 可复用试卷展示组件
- `authStore` 轻量 reactive 状态管理

### Changed
- 后端路由目录重构：新增 `routes/auth.js`、`routes/files.js`、`routes/papers.js`、`routes/quota.js`
- `src/index.js` 挂载全量路由 + `validateEnv()` + `errorHandler`
- `paperService.js`：`generateAndSave` / `regeneratePaper` 注入 quota 检查扣减
- `docker-compose.yml` 新增 `postgres` 容器 + `pgdata` volume
- 后端 `Dockerfile`：CMD 增加 `prisma migrate deploy` 自动执行
- `backend/package.json`：新增 `@prisma/client`、`prisma`、`bcryptjs`、`jsonwebtoken`
- `backend/.env.example` 从 2 个变量扩展到 19 个
- 前端 `package.json`：新增 `vue-router`
- `README.md` 更新至 V0.5 功能列表
- `docs/API.md` 完整重写（17 个接口，5 个模块）

### Fixed
- CHANGELOG.md 重复的 `[0.1.0]` 版本块（修复于 V0.5 启动前）

### Known Issues
- 无自动化测试覆盖
- `deepseek-chat` 对 Vision API 支持因区域而异
- PPT 解析依赖 LibreOffice（镜像 +400MB）
- Token 存储于 localStorage（有 XSS 风险，V1.0 建议 CSP + httpOnly refresh token）
- V0.5 不做 refresh token，access token 过期需重新登录

### Dependencies
- 新增：`@prisma/client ^6.0.0`、`prisma ^6.0.0`（dev）
- 新增：`bcryptjs ^2.4.3`、`jsonwebtoken ^9.0.0`
- 新增：`vue-router ^4.3.0`
- 新增：`postgres:16-alpine`（Docker 服务）
- 保留：V0.2 全部依赖（express、axios、pdf-parse、mammoth、officeparser、multer、vue 3、vite 5）

## [0.2.0] - 2026-05-01

### Added
- 支持 PPTX 文件上传和文本解析（officeparser）
- 支持 PPT 文件上传和解析（LibreOffice headless 转换为 PPTX）
- PPTX 内嵌图片 OCR（DeepSeek Vision API，支持优雅降级）
- 文件类型配置统一管理（`config/fileTypes.js`）
- 文件解析入口统一 dispatch（`services/parsers/index.js`）
- DeepSeek API 调用客户端统一封装（`services/deepseekClient.js`）
- Prompt 版本管理（`prompts/generate-v1.txt`、`selfcheck-v1.txt`）
- 试卷题型配置：各题型数量、分值可自定义
- 难度比例配置：easy/medium/hard 比例可自定义
- JSON 结构校验（`paperValidator.js`）：题型/选项/答案/分值/重复 17 项检查
- 基础质量报告：评分（0-100）、警告、建议
- 知识点提取与覆盖统计（`knowledgeExtractor.js`）
- 前端配置面板：题型数量/分值/难度比例
- 前端质量评分进度条、校验警告列表、建议区域
- 前端知识点覆盖展示、AI 知识点汇总
- Loading spinner 动画、增强错误展示

### Changed
- 前端上传区文案更新为"支持 PDF / DOCX / PPT / PPTX"
- 后端 Dockerfile 新增 libreoffice-impress 依赖
- `paperGenerator.js` 重构：拆分 Prompt 渲染、校验、知识点统计为独立模块

### Fixed
- DeepSeek API URL 统一为 `/v1/chat/completions`
- 试卷生成响应新增 `applied_config`、`prompt_version`、`knowledge_coverage` 字段

### Known Issues
- `deepseek-chat` 模型对 Vision API (`image_url`) 的支持因区域而异
- PPT 解析依赖 LibreOffice（镜像 +400MB），本地环境需手动安装
- PPTX 图片 OCR 单张限制 5MB、每文件最多 20 张
- 无自动化测试覆盖

### Dependencies
- 新增：officeparser（PPTX 解析，纯 JS）
- 新增：libreoffice-impress（系统包，PPT 转换）

## [0.1.0] - 2026-05-01

### Added
- 后端健康检查接口 `GET /health`
- DeepSeek API 测试接口 `POST /api/test-deepseek`
- 文件上传接口 `POST /api/upload`，支持 PDF/DOCX，最大20MB
- PDF 文本提取功能（pdf-parse）
- DOCX 文本提取功能（mammoth）
- 文件解析接口 `POST /api/parse-file`
- DeepSeek 试卷生成接口 `POST /api/generate-paper`
- Vue 3 前端页面：课程名输入 + 文件上传 + 一键生成试卷
- 试卷结构化 JSON 输出（6种题型、知识点标签、解析、答案）
- AI 试卷自检机制（10项自动检查 + 修复）
- 前端按题型卡片展示（难度标签、答案高亮、知识点标签）
- Docker Compose 开发环境配置

### Dependencies
- 后端：express, multer, axios, pdf-parse@1.1.1, mammoth, dotenv
- 前端：vue 3, vite 5, @vitejs/plugin-vue
