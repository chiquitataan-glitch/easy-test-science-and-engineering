# 版本控制规范

## Git Flow分支策略

### 分支类型

| 分支 | 用途 | 命名规范 |
|------|------|----------|
| main | 生产环境 | main |
| develop | 开发集成 | develop |
| feature | 功能开发 | feature/功能名称 |
| hotfix | 紧急修复 | hotfix/问题描述 |

### 工作流程

1. 从develop创建feature分支
2. 开发完成后合并回develop
3. release分支从develop创建
4. 最终合并到main和develop

## 提交规范

### Commit Message格式

```
<type>: <subject>

<body>
```

### Type类型

- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试
- chore: 构建/工具

### 示例

```
feat: 添加用户登录功能

- 实现登录表单
- 添加JWT验证
```

## 版本号规范

格式：主版本.次版本.修订号

- 主版本：重大架构变更
- 次版本：新功能
- 修订号：bug修复
