# Vue Review Agent

基于 LangGraph + DeepSeek 的 Vue 3 代码多维度审查系统。输入一段 Vue 代码，六个并行 Agent 分别从正确性、安全性、性能、可读性、可维护性、规范性六个维度分析，最终通过 SSE 流式返回结构化审查报告。

## 系统架构

```
POST /review
     │
     ▼
parse_ast（解析 Vue SFC 结构）
     │
     ├─ correctness_reviewer
     ├─ security_reviewer
     ├─ performance_reviewer    （六个 Agent 并行执行）
     ├─ readability_reviewer
     ├─ maintainability_reviewer
     └─ standards_reviewer
              │
              ▼
        synthesis（去重 + 排序）
              │
              ▼
         SSE 流式输出
```

## 快速开始

**1. 安装依赖**

```bash
pip install -e ".[dev]"
```

**2. 配置 API Key**

```bash
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

**3. 启动服务**

```bash
uvicorn main:app --reload --port 8000
```

**4. 发起审查请求**

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"code": "<your vue code>", "filename": "MyComponent.vue"}' \
  --no-buffer
```

## 接口说明

### `POST /review`

**请求体**

```json
{
  "code": "Vue 组件代码字符串",
  "filename": "MyComponent.vue"
}
```

**响应**（SSE 格式）

```
data: {
  "summary": "发现 3 个 Error，2 个 Warning",
  "issues": [
    {
      "severity": "error",
      "category": "security",
      "title": "v-html XSS 风险",
      "location": "第 8 行",
      "description": "v-html 渲染了未过滤的用户输入，存在 XSS 风险。",
      "before": "<span v-html=\"userInput\">",
      "after": "<span>{{ sanitize(userInput) }}</span>"
    }
  ]
}

data: [DONE]
```

### `GET /health`

返回 `{"status": "ok"}`，用于健康检查。

## 审查维度

| 维度 | 典型问题 |
|------|---------|
| 正确性 | 解构 reactive 丢失响应式、computed 有副作用 |
| 安全性 | v-html XSS、eval() 注入、硬编码密钥 |
| 性能 | v-for 缺少 key、昂贵计算未用 computed 缓存 |
| 可读性 | 命名含糊、嵌套三元表达式、魔法数字 |
| 可维护性 | 业务逻辑未抽离 composable、props drilling |
| 规范性 | 组件非 PascalCase、style 缺少 scoped |

## 项目结构

```
vue-review-agent/
├── main.py                  # FastAPI 入口，SSE 端点
├── models.py                # Pydantic 数据模型
├── agents/
│   ├── state.py             # LangGraph 全局状态定义
│   ├── graph.py             # 图结构：节点注册 + 边连接
│   ├── sfc_parser.py        # Vue SFC 正则解析 + 特征提取
│   ├── reviewers.py         # 六个并行 reviewer Agent
│   └── synthesis.py         # 汇总去重 + 按严重程度排序
└── tests/
    ├── fixtures/            # 测试用 Vue 文件（好/坏各一份）
    ├── test_sfc_parser.py
    ├── test_reviewers.py
    └── test_api.py
```

## 运行测试

```bash
# 不调用 API 的单元测试（快）
pytest tests/ -v --ignore=tests/test_reviewers.py --ignore=tests/test_api.py

# 完整测试（需要有效的 DEEPSEEK_API_KEY，约 1-2 分钟）
pytest tests/ -v
```

## 技术栈

- **LangGraph 1.x** — 多 Agent 状态机编排，并行节点 + fan-in 汇总
- **DeepSeek Chat** — 通过 OpenAI 兼容接口调用
- **FastAPI + SSE** — 流式推送审查结果
- **Pydantic v2** — 请求/响应数据校验

## 后续计划

| 阶段 | 内容 |
|------|------|
| Phase 3 | 接入 RAG，索引 Vue 官方文档提升建议质量 |
| Phase 4 | VS Code 插件，WebView 侧边栏展示结果 |
| Phase 5 | Prompt Caching，降低约 60% token 成本 |
