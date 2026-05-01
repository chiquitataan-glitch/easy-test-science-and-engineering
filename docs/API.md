# API 接口文档

Base URL：`http://localhost:3000`

所有接口统一响应格式：`{ success: boolean, data?: any, message: string }`

## 支持的文件格式

| 扩展名 | MIME Type | 说明 |
|--------|-----------|------|
| `.pdf` | `application/pdf` | |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | |
| `.pptx` | `application/vnd.openxmlformats-officedocument.presentationml.presentation` | |
| `.ppt` | `application/vnd.ms-powerpoint` | 需 LibreOffice |

文件大小限制：**20MB**

---

## GET /health

健康检查接口。

**响应示例：**

```json
{
  "success": true,
  "data": { "status": "ok" },
  "message": "ok"
}
```

---

## POST /api/test-deepseek

测试 DeepSeek API 连通性。

**请求体：**

```json
{
  "message": "你好"
}
```

**成功响应：**

```json
{
  "success": true,
  "data": { "reply": "你好！有什么可以帮助你的吗？" },
  "message": "ok"
}
```

**错误响应：**

```json
{
  "success": false,
  "message": "message is required"
}
```

---

## POST /api/upload

上传课件文件。

**请求：** `multipart/form-data`，字段名 `file`

**成功响应：**

```json
{
  "success": true,
  "data": {
    "originalName": "课件.pdf",
    "size": 1024000,
    "type": ".pdf",
    "path": "uploads/1714567890123-课件.pdf"
  },
  "message": "ok"
}
```

**错误响应：**

| 场景 | HTTP | message |
|------|:---:|--------|
| 未上传文件 | 400 | `请上传文件` |
| 不支持格式 | 400 | `仅支持 PDF / DOCX / PPT / PPTX 文件` |
| 文件过大 | 413 | `文件大小不能超过 20MB` |

---

## POST /api/parse-file

解析已上传的文件，提取文本内容（含预览）。

**请求体：**

```json
{
  "filePath": "uploads/1714567890123-课件.pptx"
}
```

**成功响应：**

```json
{
  "success": true,
  "data": {
    "fileName": "课件.pptx",
    "fileType": ".pptx",
    "textLength": 5230,
    "preview": "第一章 流体流动..."
  },
  "message": "ok"
}
```

**错误响应：**

| 场景 | message |
|------|--------|
| 空路径 | `请提供文件路径` |
| 不支持格式 | `不支持的文件类型，仅支持 PDF / DOCX / PPT / PPTX` |
| 文件不存在 | `文件不存在` |
| 解析失败 | 具体错误信息 |

---

## POST /api/generate-paper

生成结构化试卷。自动解析文件文本，调用 DeepSeek 生成试卷，执行 AI 自检和结构校验。

**请求体：**

```json
{
  "filePath": "uploads/1714567890123-课件.pptx",
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
    "difficulty": {
      "easy": 0.3,
      "medium": 0.5,
      "hard": 0.2
    }
  }
}
```

- `filePath`：必填，上传接口返回的路径
- `courseName`：必填，课程名称
- `config`：可选，不传使用默认配置
  - `types`：部分题型可省略（未指定的用默认值），`count: 0` 表示不生成该题型
  - `difficulty`：三者比例之和必须为 1

**成功响应：**

```json
{
  "success": true,
  "data": {
    "courseName": "化工原理",
    "textLength": 5230,
    "paper": {
      "paper_title": "《化工原理》复习试卷",
      "course_name": "化工原理",
      "questions": [
        {
          "question_type": "single_choice",
          "question_no": 1,
          "content": "雷诺数判断流型的临界值是？",
          "options": [
            { "key": "A", "value": "500" },
            { "key": "B", "value": "2000" },
            { "key": "C", "value": "4000" },
            { "key": "D", "value": "10000" }
          ],
          "answer": "B",
          "analysis": "Re<2000 为层流...",
          "knowledge_points": ["雷诺数判断流型"],
          "difficulty": "easy",
          "score": 5
        }
      ],
      "knowledge_summary": {
        "points": [
          {
            "name": "雷诺数判断流型",
            "question_nos": [1, 3, 5],
            "difficulty_distribution": { "easy": 1, "medium": 1, "hard": 1 }
          }
        ],
        "total": 8,
        "description": "试卷知识点覆盖了课程标准的主要模块"
      },
      "quality_report": {
        "score": 94,
        "warnings": [],
        "suggestions": ["知识点覆盖较全面，可用于正式测验"],
        "summary": "试卷质量良好",
        "self_check": { "passed": true, "issues": [], "skip_reason": null },
        "prompt_version": "generate-v1",
        "applied_config": { "types": {...}, "difficulty": {...} },
        "knowledge_coverage": {
          "total_points": 11,
          "questions_with_knowledge": 36,
          "questions_without_knowledge": [],
          "top_points": [{ "name": "雷诺数判断流型", "count": 5 }],
          "description": "知识点覆盖广泛，分布均衡",
          "gaps": []
        }
      }
    }
  },
  "message": "ok"
}
```

**config 校验错误：**

| 场景 | message |
|------|--------|
| 未知题型 | `未知题型：xxx` |
| count 非整数或负数 | `题型 xxx 的 count 必须是非负整数` |
| score 非正数 | `题型 xxx 的 score 必须是正数` |
| 未知难度 | `未知难度：xxx` |
| 比例和 ≠ 1 | `难度比例之和必须为 1` |

**生成错误：**

| 场景 | message |
|------|--------|
| 文本太短 | `文本内容太短，无法生成试卷` |
| JSON 解析失败 | `试卷JSON解析失败，请重试` |
| 缺少 questions | `试卷格式不正确，缺少题目数据` |
| DeepSeek 超时 | `DeepSeek API 调用超时` |
