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

## 开发调试

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
