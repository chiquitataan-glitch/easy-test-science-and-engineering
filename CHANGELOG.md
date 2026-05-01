# Changelog

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
- `deepseek-chat` 模型对 Vision API (`image_url`) 的支持因区域而异，中国/海外 API 行为不一致
- PPT 解析依赖 LibreOffice（镜像 +400MB），本地环境需手动安装
- PPTX 图片 OCR 单张限制 5MB、每文件最多 20 张
- 无测试覆盖

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
