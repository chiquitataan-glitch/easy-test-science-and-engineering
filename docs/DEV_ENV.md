# 开发环境说明

## Docker网络说明

- 前端容器通过Vite代理访问后端容器，代理配置在 `frontend/vite.config.js`
- 前端容器内访问后端使用 `http://backend:3000`
- 浏览器访问前端使用 `http://localhost:5173`

## 环境变量

### 后端环境变量

- `DEEPSEEK_API_KEY`：DeepSeek API密钥（必须配置）
- `PORT`：后端服务端口（默认3000）

配置文件位置：`backend/.env`（不提交Git）
示例文件：`backend/.env.example`（提交Git）

## Volumes

- `./backend:/app`：挂载后端代码，支持热重载
- `./backend/uploads:/app/uploads`：挂载上传文件目录
- `./frontend:/app`：挂载前端代码，支持热重载

## 端口映射

- 前端：宿主5173 -> 容器5173
- 后端：宿主3000 -> 容器3000

## 系统依赖说明

### LibreOffice（解析 .ppt 文件）

后端 Docker 镜像包含 LibreOffice Impress，用于将老格式 `.ppt` 文件转换为 `.pptx` 后再提取文本。

- Docker 环境：已内置在 Dockerfile 中，`docker compose up --build` 自动安装
- 本地环境：需要手动安装 LibreOffice
  - Windows：从 https://www.libreoffice.org/download/ 下载安装
  - macOS：`brew install --cask libreoffice`
  - Linux：`sudo apt-get install libreoffice-impress`

> 如果本地未安装 LibreOffice，上传 `.ppt` 文件时会返回错误提示，请使用 `.pptx` 格式代替。

## 文件上传说明

- `pdf`：纯 JS 解析，无需系统依赖
- `docx`：纯 JS 解析，无需系统依赖
- `pptx`：纯 JS 解析，无需系统依赖
- `ppt`：依赖 LibreOffice 转换为 `.pptx` 后解析

## 调试技巧

### 进入后端容器
```bash
docker compose exec backend sh
```

### 进入前端容器
```bash
docker compose exec frontend sh
```

### 查看实时日志
```bash
docker compose logs -f
```
