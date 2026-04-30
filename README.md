# Easy Test - AI试卷生成系统

基于DeepSeek AI的智能试卷生成H5应用。

## 版本信息

- 当前版本：V0.1 本地验证版

## 快速开始

### 前置要求

- Docker
- Docker Compose

### 启动项目

```bash
docker compose up --build
```

### 访问地址

- 前端：http://localhost:5173
- 后端：http://localhost:3000

### 常用Docker命令

```bash
# 后台启动
docker compose up -d

# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 停止服务
docker compose down

# 重新构建
docker compose up --build
```

## 项目结构

```
easy-test/
├── backend/          # 后端服务
│   ├── src/
│   ├── uploads/
│   ├── package.json
│   └── Dockerfile
├── frontend/         # 前端应用
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docs/             # 文档
├── docker-compose.yml
└── README.md
```

## 版本路线

- **V0.1** 本地验证版：验证核心闭环
- **V0.2** 生成质量优化版：优化试卷生成质量
- **V0.5** MVP可用版：用户登录、MySQL、Redis、历史记录、PDF导出
- **V1.0** 正式商业版：完整后台、成本统计、部署上线
