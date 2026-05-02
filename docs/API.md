# API 接口文档

Base URL：`http://localhost:3000`

统一响应格式：`{ success: boolean, data?: any, message: string, error: { code: string, details?: any } | null }`

## 支持的文件格式

| 扩展名 | MIME Type | 说明 |
|--------|-----------|------|
| `.pdf` | `application/pdf` | |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | |
| `.pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | |
| `.ppt` | `application/vnd.ms-powerpoint` | 需 LibreOffice |

文件大小限制：**20MB**

---

## 统一响应格式

**成功：**
```json
{ "success": true, "data": {}, "message": "ok", "error": null }
```

**失败：**
```json
{ "success": false, "data": null, "message": "描述", "error": { "code": "ERROR_CODE", "details": {} } }
```

---

## 错误码

| 错误码 | HTTP | 说明 |
|--------|:---:|------|
| `AUTH_REQUIRED` | 401 | 未登录或 token 无效 |
| `INVALID_CREDENTIALS` | 401 | 邮箱或密码错误 |
| `TOKEN_EXPIRED` | 401 | token 已过期 |
| `PERMISSION_DENIED` | 403 | 无权访问该资源 |
| `VALIDATION_ERROR` | 400 | 请求参数校验失败 |
| `FILE_NOT_FOUND` | 404 | 文件不存在 |
| `PAPER_NOT_FOUND` | 404 | 试卷不存在 |
| `QUOTA_EXCEEDED` | 403 | 生成次数已用完 |
| `UNSUPPORTED_FILE_TYPE` | 400 | 不支持的文件格式 |
| `PARSE_FAILED` | 500 | 文件解析失败 |
| `GENERATION_FAILED` | 500 | 试卷生成失败 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `NOT_IMPLEMENTED` | 501 | 功能未实现（V1.0 预留） |

---

## 一、System — 系统

### GET /health

健康检查。

| 属性 | 值 |
|------|-----|
| 是否登录 | 否 |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl http://localhost:3000/health
```

```json
{ "success": true, "data": { "status": "ok" }, "message": "ok", "error": null }
```

### POST /api/test-deepseek

测试 DeepSeek API 连通性。

| 属性 | 值 |
|------|-----|
| 是否登录 | 否 |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl -X POST http://localhost:3000/api/test-deepseek \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'
```

---

## 二、Auth — 认证

### POST /api/auth/register

注册新用户，自动创建 user_quota。

| 属性 | 值 |
|------|-----|
| 是否登录 | 否 |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"12345678","displayName":"张三","clientType":"web"}'
```

**成功 (201)：**
```json
{
  "success": true,
  "data": {
    "user": { "id": "uuid", "displayName": "张三", "email": "test@example.com" },
    "token": "eyJhbGciOiJIUzI1NiIs..."
  },
  "message": "注册成功",
  "error": null
}
```

**错误码：** `VALIDATION_ERROR`（邮箱格式/密码长度/已注册）

---

### POST /api/auth/login

密码登录。

| 属性 | 值 |
|------|-----|
| 是否登录 | 否 |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"12345678","clientType":"web"}'
```

**成功：**
```json
{
  "success": true,
  "data": {
    "user": { "id": "uuid", "displayName": "张三", "email": "test@example.com" },
    "token": "eyJhbGciOiJIUzI1NiIs..."
  },
  "message": "登录成功",
  "error": null
}
```

**错误码：** `INVALID_CREDENTIALS`（邮箱或密码错误—不区分原因）

---

### GET /api/auth/me

获取当前用户信息、identities、quota。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl http://localhost:3000/api/auth/me \
  -H "Authorization: Bearer <token>"
```

**成功：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "displayName": "张三",
    "identities": [{ "id": "uuid", "provider": "password", "identifier": "test@example.com" }],
    "quota": { "total": 10, "used": 3, "remaining": 7 }
  },
  "message": "ok",
  "error": null
}
```

**错误码：** `AUTH_REQUIRED`、`TOKEN_EXPIRED`

---

### POST /api/auth/logout

退出登录（JWT 无状态，后端直接返回成功）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl -X POST http://localhost:3000/api/auth/logout \
  -H "Authorization: Bearer <token>"
```

---

### POST /api/auth/wechat-mini-program-login

微信小程序登录 — **V1.0 预留，当前返回 501**。

| 属性 | 值 |
|------|-----|
| 是否登录 | 否 |
| V0.5 实现 | ❌（占位） |
| V1.0 复用 | ✅（实现） |

```bash
curl -X POST http://localhost:3000/api/auth/wechat-mini-program-login \
  -H "Content-Type: application/json" \
  -d '{"code":"wx_auth_code"}'
```

```json
{ "success": false, "message": "微信小程序登录将在 V1.0 实现", "error": { "code": "NOT_IMPLEMENTED" } }
```

---

## 三、Files — 文件

### POST /api/files/upload

上传课件文件，自动解析文本并入库。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅（小程序 wx.uploadFile 复用） |

**请求：** `multipart/form-data`，字段名 `file`

```bash
curl -X POST http://localhost:3000/api/files/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/test.pptx"
```

**成功 (201)：**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "originalName": "test.pptx",
    "mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "size": 5242880,
    "status": "parsed",
    "parsedTextLength": 5230,
    "clientType": "web",
    "createdAt": "2026-05-02T10:30:00.000Z"
  },
  "message": "上传成功",
  "error": null
}
```

**错误码：** `AUTH_REQUIRED`、`UNSUPPORTED_FILE_TYPE`、`VALIDATION_ERROR`（文件过大）

---

### GET /api/files

获取当前用户的文件列表（分页）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl "http://localhost:3000/api/files?page=1&pageSize=20" \
  -H "Authorization: Bearer <token>"
```

---

### GET /api/files/:id

获取文件详情（仅自己的文件）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

**错误码：** `FILE_NOT_FOUND`、`PERMISSION_DENIED`

---

### DELETE /api/files/:id

删除文件（物理删除记录 + 本地文件）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

**错误码：** `FILE_NOT_FOUND`、`PERMISSION_DENIED`

---

## 四、Papers — 试卷

### POST /api/papers/generate

生成试卷并入库（扣 quota）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| 是否扣 quota | ✅（成功后扣 1） |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl -X POST http://localhost:3000/api/papers/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "fileId": "uploaded_file_uuid",
    "courseName": "化工原理",
    "config": {
      "types": {
        "single_choice": { "count": 8, "score": 5 },
        "multi_choice": { "count": 2, "score": 5 },
        "fill_blank": { "count": 10, "score": 2 },
        "true_false": { "count": 10, "score": 1 },
        "calculation": { "count": 4, "score": 3 },
        "short_answer": { "count": 2, "score": 4 }
      },
      "difficulty": { "easy": 0.3, "medium": 0.5, "hard": 0.2 }
    }
  }'
```

- `fileId`：必填，来自 `POST /api/files/upload` 返回的 id
- `courseName`：必填
- `config`：可选，不传使用默认配置

**成功 (201)：**
```json
{
  "success": true,
  "data": {
    "paperId": "uuid",
    "paperTitle": "化工原理期中试卷",
    "courseName": "化工原理",
    "questionCount": 36,
    "qualityScore": 92,
    "paper": { "paper_title": "...", "questions": [...], "quality_report": {...} }
  },
  "message": "试卷生成成功",
  "error": null
}
```

**错误码：** `AUTH_REQUIRED`、`FILE_NOT_FOUND`、`PERMISSION_DENIED`、`VALIDATION_ERROR`、`QUOTA_EXCEEDED`、`GENERATION_FAILED`

---

### GET /api/papers

获取当前用户的试卷历史列表（分页，轻量字段）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl "http://localhost:3000/api/papers?page=1&pageSize=20" \
  -H "Authorization: Bearer <token>"
```

**成功：** `{ "items": [{ "id", "paperTitle", "courseName", "questionCount", "status", "qualityScore", "fileName", "createdAt" }], "total": 5, "page": 1 }`

---

### GET /api/papers/:id

获取试卷完整详情（paperJson、config、qualityReport、questions）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

**错误码：** `PAPER_NOT_FOUND`、`PERMISSION_DENIED`

---

### POST /api/papers/:id/regenerate

重新生成试卷（扣 quota，使用原 `parsed_text_snapshot` 和 `config`）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| 是否扣 quota | ✅（成功后扣 1） |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl -X POST http://localhost:3000/api/papers/{id}/regenerate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"config": { "types": {...} }}'
```

`config` 可选，不传使用原配置。

**成功 (201)：** 返回新 paper，含 `originalPaperId` 字段指向原试卷。

**错误码：** `PAPER_NOT_FOUND`、`PERMISSION_DENIED`、`QUOTA_EXCEEDED`、`GENERATION_FAILED`

---

## 五、Quota — 额度

### GET /api/quota/me

获取当前用户额度信息。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl http://localhost:3000/api/quota/me \
  -H "Authorization: Bearer <token>"
```

```json
{
  "success": true,
  "data": { "quotaTotal": 10, "quotaUsed": 3, "quotaRemaining": 7 },
  "message": "ok",
  "error": null
}
```

### GET /api/quota/usage-records

获取使用流水（分页）。

| 属性 | 值 |
|------|-----|
| 是否登录 | ✅ |
| V0.5 实现 | ✅ |
| V1.0 复用 | ✅ |

```bash
curl "http://localhost:3000/api/quota/usage-records?page=1&pageSize=20" \
  -H "Authorization: Bearer <token>"
```

---

## 六、V0.2 兼容接口（保留）

以下接口为 V0.2 兼容保留，**不需要登录**，数据不入库：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload` | 公开上传 |
| POST | `/api/parse-file` | 公开解析 |
| POST | `/api/generate-paper` | 公开生成（不入库） |

> 建议 V0.5 前端使用 `/api/files/upload` `/api/papers/generate` 鉴权版接口。
