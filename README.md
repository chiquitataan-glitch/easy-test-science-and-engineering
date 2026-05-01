# Easy Test - AI试卷生成系统

基于 DeepSeek AI 的智能试卷生成 Web 应用。上传课件资料（PDF/DOCX/PPT/PPTX），自动提取文本内容，调用 DeepSeek 大语言模型生成结构化复习试卷。

**v0.2.0** — 生成质量优化版

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | Vue 3 (Composition API) + Vite 5 |
| 后端 | Node.js + Express |
| AI | DeepSeek API (`deepseek-chat`) |
| 文件解析 | pdf-parse, mammoth, officeparser, JSZip |
| PPT 转换 | LibreOffice Impress (headless) |
| 容器化 | Docker + Docker Compose |

## 支持文件格式

| 格式 | 文本解析 | 图片 OCR | 依赖 |
|------|:---:|:---:|------|
| PDF | ✅ | - | pdf-parse（纯 JS） |
| DOCX | ✅ | - | mammoth（纯 JS） |
| PPTX | ✅ | ⚠️ 需 Vision API | officeparser + JSZip |
| PPT | ✅（转为 PPTX） | ⚠️ 需 Vision API | LibreOffice |

## 快速开始

### 前置要求

- Docker Desktop
- DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）

### 1. 配置环境变量

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的 DEEPSEEK_API_KEY
```

### 2. Docker Compose 启动

```bash
docker compose up --build
```

构建过程约 5-8 分钟（首次需下载 LibreOffice）。

### 3. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端界面 |
| http://localhost:3000/health | 后端健康检查 |

### 本地启动（无需 Docker）

```bash
# 终端1：后端
cd backend && npm install && npm start

# 终端2：前端
cd frontend && npm install && npx vite --host
```

> 本地启动时，PPT 格式需要自行安装 LibreOffice。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|:---:|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | - | DeepSeek API 密钥 |
| `PORT` | ❌ | 3000 | 后端端口 |
| `DEEPSEEK_API_URL` | ❌ | `https://api.deepseek.com/v1/chat/completions` | API 地址 |

## 接口概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/test-deepseek` | DeepSeek 连通性测试 |
| POST | `/api/upload` | 上传课件文件 |
| POST | `/api/parse-file` | 解析文件提取文本 |
| POST | `/api/generate-paper` | 生成结构化试卷 |

详细文档见 [docs/API.md](docs/API.md)。

## V0.2 核心功能

- **多格式支持**：PDF / DOCX / PPT / PPTX 四种课件格式
- **PPT 解析**：通过 LibreOffice headless 转换 + officeparser 提取文本
- **图片 OCR**（可选）：PPTX 内嵌图片通过 DeepSeek Vision API 识别文字
- **结构化试卷**：36 题标准试卷（单选/多选/填空/判断/计算/简答）
- **题型配置**：可自定义各题型数量、分值和难度比例
- **Prompt 版本管理**：Prompt 模板文件化，支持迭代和 A/B 测试
- **AI 自检**：自动检查试卷结构并修复问题
- **质量报告**：评分（0-100）、校验警告、改进建议
- **知识点覆盖**：自动统计知识点分布和覆盖盲区
- **前端展示**：按题型分组卡片、难度标签、答案高亮、质量评分进度条

## 常见问题

### Q: PPT 上传报错"未安装 LibreOffice"？

本地开发需手动安装 LibreOffice：
- Windows：从 [libreoffice.org](https://www.libreoffice.org/download/) 下载
- macOS：`brew install --cask libreoffice`
- Linux：`sudo apt-get install libreoffice-impress`

Docker 环境已内置，无需额外配置。

### Q: 生成试卷很慢？

正常，DeepSeek 生成 36 道题约 1-2 分钟，自检再额外 30-90 秒。

### Q: 图片 OCR 不工作？

`deepseek-chat` 模型对 Vision 的支持因区域而异。不支持时会自动降级——跳过图片 OCR，不影响文本解析。

### Q: 如何调整题目数量？

前端页面的"出题配置"面板可自定义各题型数量和分值。不展开面板则使用默认配置。

## 项目结构

```
easy-test/
├── backend/
│   ├── src/
│   │   ├── config/fileTypes.js, paperConfig.js
│   │   ├── prompts/generate-v1.txt, selfcheck-v1.txt
│   │   ├── routes/deepseek.js, upload.js, parseFile.js, generatePaper.js
│   │   └── services/ (deepseekClient, promptManager, paperGenerator,
│   │        paperValidator, knowledgeExtractor, imageToText, parsers/)
│   ├── uploads/ (不提交 Git)
│   ├── .env.example
│   └── Dockerfile
├── frontend/src/ (App.vue, style.css)
├── docs/ (API.md, DEV_ENV.md, TASKS.md, ROADMAP.md)
├── docker-compose.yml
└── README.md
```

## 版本路线

| 版本 | 目标 |
|------|------|
| **v0.1.0** ✅ | 核心闭环：上传→解析→生成→展示 |
| **v0.2.0** ✅ | 多格式支持 + 生成质量优化 |
| v0.5.0 | 用户登录、数据库、历史记录 |
| v1.0.0 | 完整后台、成本统计、生产部署
