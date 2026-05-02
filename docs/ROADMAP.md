# 版本路线图

## V0.1 本地验证版 (已完成)

目标：验证核心闭环

- [x] 项目初始化
- [x] Docker 环境搭建
- [x] PDF/DOCX 上传与解析
- [x] DeepSeek API 集成
- [x] 试卷生成（固定 36 题）
- [x] 前端展示

## V0.2 生成质量优化版 (已完成)

目标：多格式课件 + AI 生成质量优化

- [x] PPT/PPTX 上传与解析
- [x] PPTX 图片 OCR（Vision + 降级）
- [x] 架构重构（config/parser/client）
- [x] Prompt 版本管理
- [x] 题型/题量/难度可配置
- [x] JSON 校验 + 质量报告
- [x] 知识点提取与覆盖统计
- [x] 前端结构化展示优化

## V0.5 MVP 可用版 (已完成)

目标：用户系统 + 数据持久化 + 产品雏形

- [x] 用户注册/登录（JWT + bcrypt）
- [x] PostgreSQL + Prisma ORM（10 表 + 5 枚举）
- [x] 用户身份分离模型（users + user_identities）
- [x] 文件记录持久化 + 用户资源隔离
- [x] 试卷生成历史 + 详情查看
- [x] 试卷重新生成（original_paper_id 关联）
- [x] 题目拆分入库（paper_questions）
- [x] quota 额度控制（Prisma 事务防并发）
- [x] 使用流水记录（usage_records）
- [x] 生成日志（generation_logs）
- [x] 前端路由 + 登录态 + 6 页面
- [x] Docker Compose 新增 postgres 容器
- [x] Migration / Seed 自动化

## V1.0 正式商业版

目标：微信小程序 + 支付 + 生产部署

- [ ] 微信小程序前端（uni-app 或原生）
- [ ] 微信登录（openid/unionid → user_identities）
- [ ] 多端 token 复用（web / wechat_mini_program / admin）
- [ ] 支付购买额度（plans 表已预留）
- [ ] 对象存储（storage_provider/storage_key 已预留）
- [ ] API 限流（express-rate-limit）
- [ ] PDF 导出
- [ ] 管理后台
- [ ] 成本统计
- [ ] 生产部署（HTTPS / 域名 / 监控）
- [ ] 自动化测试
