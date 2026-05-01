# Changelog

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
- 版本控制规范文档、任务列表、版本路线图

### Changed
- 统一所有 API 响应格式为 `{ success, data, message }`

### Dependencies
- 后端：express, multer, axios, pdf-parse@1.1.1, mammoth, dotenv
- 前端：vue 3, vite 5, @vitejs/plugin-vue
