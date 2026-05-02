# 任务列表

## V0.1 本地验证版 (已完成)

- [x] 项目初始化
- [x] Docker 环境搭建
- [x] 文件上传接口（PDF/DOCX）
- [x] 文本解析功能
- [x] DeepSeek API 集成
- [x] 试卷生成逻辑
- [x] 前端试卷展示
- [x] AI 自检机制

## V0.2 生成质量优化版 (已完成)

- [x] PPTX 上传与解析
- [x] PPT 上传与解析（LibreOffice）
- [x] PPTX 图片 OCR（Vision + 降级）
- [x] 文件类型统一配置
- [x] 解析器统一 dispatch
- [x] DeepSeek Client 封装
- [x] Prompt 版本管理
- [x] 题型/题量/难度配置
- [x] JSON 结构校验
- [x] 质量报告
- [x] 知识点提取与覆盖
- [x] 前端结构化展示

## V0.5 MVP 可用版 (已完成)

### Task 1: PostgreSQL + Prisma + 统一响应/错误码
- [x] docker-compose.yml 新增 postgres 容器
- [x] prisma/schema.prisma（10 张表 + 5 个枚举）
- [x] prisma/seed.js（prompt_versions 初始化）
- [x] utils/response.js 统一响应
- [x] utils/errors.js（13 个错误码 + AppError）
- [x] middleware/errorHandler.js 全局错误处理
- [x] config/env.js 环境变量校验

### Task 2: 用户注册登录 + JWT
- [x] POST /api/auth/register（bcrypt + 自动创建 quota）
- [x] POST /api/auth/login（identifier/password 匹配）
- [x] GET /api/auth/me（当前用户 + identities + quota）
- [x] POST /api/auth/logout（无状态 JWT）
- [x] POST /api/auth/wechat-mini-program-login（V1.0 占位 501）
- [x] middleware/auth.js（requireAuth / optionalAuth）
- [x] JWT payload: sub/userId/clientType/identityProvider

### Task 3: 文件记录持久化
- [x] POST /api/files/upload（鉴权 + Multer + 入库 + 自动解析）
- [x] GET /api/files（分页列表，用户隔离）
- [x] GET /api/files/:id（详情，归属校验）
- [x] DELETE /api/files/:id（物理删除 + 清理本地文件）
- [x] crypto.randomUUID() 安全文件名

### Task 4: 试卷生成历史
- [x] POST /api/papers/generate（鉴权 + generatePaper + 入库 + 拆题）
- [x] GET /api/papers（分页，含文件名 + 质量评分）
- [x] GET /api/papers/:id（完整 paperJson + questions + file 关联）
- [x] POST /api/papers/:id/regenerate（parsed_text_snapshot 复用 + 关联）
- [x] generation_logs 记录每次生成

### Task 5: quota 额度控制
- [x] GET /api/quota/me（quotaTotal/quotaUsed/quotaRemaining）
- [x] GET /api/quota/usage-records（分页流水）
- [x] generateAndSave / regeneratePaper 注入 checkQuota + deductQuota
- [x] AI 失败不扣减
- [x] Prisma 事务 + 二次校验防并发超扣

### Task 6: 前端登录态
- [x] /login 页面（LoginView）
- [x] /register 页面（RegisterView）
- [x] vue-router + beforeEach 导航守卫
- [x] authStore（reactive + localStorage 恢复）
- [x] NavBar（登录态/用户名/quota/退出）
- [x] apiClient（自动 Authorization + 401 跳转）
- [x] HomeView 从 App.vue 迁移（零逻辑改动）

### Task 7: 前端历史/详情/个人中心
- [x] HomeView 改用 V0.5 API（apiClient + fileId + 跳转）
- [x] /papers 历史列表（PaperListView）
- [x] /papers/:id 详情（PaperDetailView + PaperContent）
- [x] 重新生成按钮
- [x] /profile 个人中心（用户信息 + quota 进度条）
- [x] refreshUser() 生成后实时更新 quota
- [x] 全部 loading/error/empty 三态

### Task 8: 文档收尾
- [x] API.md 完整重写（17 个接口，5 模块）
- [x] README.md 更新至 V0.5
- [x] CHANGELOG.md 新增 [0.5.0]
- [x] ROADMAP.md V0.5 标记完成
- [x] TASKS.md 全部标记完成
- [x] DEV_ENV.md 更新 PostgreSQL/Prisma/JWT

## V1.0 正式商业版

- [ ] 微信小程序前端
- [ ] 微信登录（POST /api/auth/wechat-mini-program-login 实现）
- [ ] 支付购买额度（plans 表 + 支付回调）
- [ ] 对象存储（storage_provider/storage_key 切换）
- [ ] PDF 导出
- [ ] API 限流
- [ ] 管理后台
- [ ] 成本统计
- [ ] 生产部署
- [ ] 自动化测试

## V1.0 小程序预留说明

| 预留点 | 文件/表 | 说明 |
|--------|---------|------|
| `user_identities.openid / unionid` | schema.prisma | 微信登录直接写入 |
| `ClientType.wechat_mini_program` | schema.prisma + error.js | 枚举已定义 |
| `POST /api/auth/wechat-mini-program-login` | routes/auth.js | 占位接口返回 501 |
| `storage_provider / storage_key` | uploaded_files 表 | 预留对象存储切换 |
| `client_type` 字段 | 所有资源表 | 区分 web/wechat 用量 |
| `plans` 表 | schema.prisma | 支付套餐 |
| `UsageAction.quota_grant` | schema.prisma | 购买额度充值 |
| multipart/form-data 上传 | routes/files.js | 小程序 wx.uploadFile 直接复用 |
| Bearer token 机制 | 全部 | 小程序 wx.request 直接复用 |

## Known Issues

- DeepSeek Vision API 兼容性不稳定
- PPT 依赖 LibreOffice（+400MB）
- 无自动化测试
- Token 存 localStorage（XSS 风险）
- V0.5 不做 refresh token，过期需重新登录
