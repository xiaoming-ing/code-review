# Vue 前端代码审查 Agent — 设计文档

**日期：** 2026-05-07  
**技术栈：** Python + LangGraph + Claude API / TypeScript + VS Code Extension API  
**目标岗位：** AI 工程师 / 大模型应用开发

---

## 1. 项目概述

一款 VS Code 插件，用户选中 Vue 代码（或整个 `.vue` 文件），触发审查后由后端多 Agent 系统并行分析，将结构化审查报告和改进方案以流式方式展示在侧边栏 WebView 中。

**核心价值：** 不是通用代码检查，而是深度理解 Vue 组件设计规范，能指出"组件职责过重""响应式变量滥用""性能陷阱"等 ESLint 发现不了的深层问题。

---

## 2. 系统架构

```
┌─────────────────────────────────────────┐
│          VS Code Extension               │
│  ┌──────────┐      ┌──────────────────┐ │
│  │ Command  │      │  WebView Panel   │ │
│  │ Palette  │      │  (审查结果展示)   │ │
│  └────┬─────┘      └────────▲─────────┘ │
│       │ 选中代码/文件路径      │ 流式结果  │
└───────┼────────────────────────┼─────────┘
        │ HTTP POST              │ SSE
        ▼                        │
┌─────────────────────────────────────────┐
│         Python Backend (FastAPI)         │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │        Orchestrator Agent         │   │
│  │  - 解析代码类型（Vue SFC / JS/TS） │   │
│  │  - 拆分审查任务，并行分发          │   │
│  └───┬──────┬──────┬───────┬──────┬──────┘   │
│      │      │      │       │      │      │
│      ▼      ▼      ▼       ▼      ▼      ▼    │
│  ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐ │
│  │正确性││安全性││性能  ││可读性││可维护││规范性│ │
│  │Agent ││Agent ││Agent ││Agent ││Agent ││Agent │ │
│  └──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘ │
│     └───────┴───────┴───────┘           │
│                   │                     │
│                   ▼                     │
│         ┌──────────────────┐            │
│         │  Synthesis Agent  │            │
│         │  汇总问题 + 生成   │            │
│         │  优先级改进方案    │            │
│         └────────┬─────────┘            │
│                  │                      │
│        ┌─────────┴──────────┐           │
│        ▼                    ▼           │
│  ┌──────────┐        ┌──────────┐       │
│  │ RAG 检索  │        │ Tool Use │       │
│  │ Vue 文档  │        │ AST 解析  │       │
│  └──────────┘        └──────────┘       │
└─────────────────────────────────────────┘
```

---

## 3. Multi-Agent 详细设计

### 3.1 Orchestrator Agent

**职责：** 接收原始代码，判断文件类型，将审查任务并行分发给六个专职 Agent，收集结果后交给 Synthesis Agent。

**输入：** 代码字符串 + 文件名（可选）  
**输出：** 六个子 Agent 的审查结果列表

**关键逻辑：**
- 使用 LangGraph 的 `parallel_node` 并发执行六个子 Agent
- 设置超时（每个子 Agent 最多 30s），超时则跳过该维度审查

### 3.2 Correctness Agent（正确性审查）

**审查点：**
- `ref` vs `reactive` 选择错误（解构 reactive 导致响应式丢失）
- `computed` 内有副作用（修改外部状态）
- `v-model` 在子组件中未使用 `defineModel` 正确绑定（Vue 3.4+）
- `watch` 依赖项声明不完整导致不触发
- 异步操作未处理错误（无 try/catch 或 onError）
- Props 未声明类型导致运行时错误

**工具调用：** AST 解析提取 `watch` 依赖项、`computed` 内赋值操作等结构化信息

### 3.3 Security Agent（安全性审查）

**审查点：**
- 使用 `v-html` 渲染未经过滤的用户输入（XSS 风险）
- 在 `<script setup>` 中拼接 SQL / 命令字符串
- API 密钥、Token 硬编码在组件内
- 路由参数直接渲染到页面未做转义
- `eval()` 或 `new Function()` 执行动态代码
- `localStorage` 存储敏感信息（密码、token 明文）

### 3.4 Performance Agent（性能审查）

**审查点：**
- `v-for` 缺少 `:key` 或使用 `index` 作为 key（影响 diff 算法）
- 大列表未使用虚拟滚动（`vue-virtual-scroller`）
- 昂贵计算未用 `computed` 缓存，放在 `methods` 或 template 表达式中
- 未使用 `defineAsyncComponent` 懒加载大型子组件
- `v-if` 与 `v-show` 场景混用（频繁切换应用 v-show）
- 在 `watch` 中做大量同步计算未加 `{ flush: 'post' }` 或防抖

### 3.5 Readability Agent（可读性审查）

**审查点：**
- 组件超过 300 行未拆分，单个函数超过 50 行
- 变量 / 函数命名含糊（`data`、`flag`、`temp`、`handle`）
- Template 内嵌套三元表达式超过两层
- 魔法数字未提取为具名常量（如 `setTimeout(fn, 3000)`）
- 复杂条件逻辑未提取为 `computed` 或命名函数
- 注释与代码不一致或说明"是什么"而非"为什么"

### 3.6 Maintainability Agent（可维护性审查）

**审查点：**
- 业务逻辑未抽离 composable，复用性差
- 组件承担多个不相关职责（SRP 违反）
- Props 定义缺少默认值或 validator
- 硬编码的字符串 / 配置值散落在组件中（应集中到常量文件）
- 父子组件通过 `ref` 直接操作对方内部状态（破坏封装）
- 深层 props drilling（超过三层应考虑 provide/inject 或状态管理）

### 3.7 Standards Agent（规范性审查）

**审查点：**
- 组件命名不符合 PascalCase 或非 multi-word（与 HTML 内置元素冲突风险）
- 事件名未使用 kebab-case
- `<style>` 未加 `scoped` 且未使用 CSS Modules（全局样式污染风险）
- `<script>` 与 `<script setup>` 混用
- Emits 未显式声明（Vue 3 最佳实践要求 `defineEmits`）
- 文件结构不符合约定顺序（`<script>` → `<template>` → `<style>`）

### 3.8 Synthesis Agent

**职责：** 接收六个子 Agent 的原始发现，去重合并，按严重程度（Error / Warning / Suggestion）排序，为每个问题生成具体的代码改进示例。

**输出格式：**
```json
{
  "summary": "发现 3 个 Error，5 个 Warning，2 个 Suggestion",
  "issues": [
    {
      "severity": "error",
      "category": "correctness",
      "title": "解构 reactive 对象导致响应式丢失",
      "location": "第 12 行",
      "description": "直接解构 reactive 对象会丢失响应式追踪，修改后视图不会更新。",
      "before": "const { count } = state",
      "after": "const count = computed(() => state.count)"
    }
  ]
}
```

---

## 4. RAG 设计

**知识库内容：**
| 来源 | 内容 | 更新频率 |
|------|------|---------|
| Vue 3 官方文档 | 响应式、组件、composable 最佳实践 | 版本发布时 |
| Vue Style Guide | 优先级 A/B/C/D 规则 | 版本发布时 |
| VueUse 文档 | 常用 composable 模式 | 季度 |

**检索策略：**
- 每个子 Agent 审查前，根据"发现的问题类型"检索相关文档片段
- 检索结果作为 system prompt 的一部分注入，支撑改进建议的准确性
- 使用 `text-embedding-3-small` 做向量化，ChromaDB 本地存储

**为什么不只靠 LLM 记忆：** Vue 3.4+ 的 `defineModel`、`useTemplateRef` 等新 API 在模型训练数据中覆盖不足，RAG 能补充最新知识。

---

## 5. Tool Use 设计

### AST 解析工具

```python
@tool
def parse_vue_ast(code: str) -> dict:
    """
    解析 Vue SFC，返回结构化信息：
    - template 节点数量和最大嵌套深度
    - script 中的函数列表、ref/reactive 使用情况
    - style 是否有 scoped
    """
```

**意义：** 让 Agent 基于结构化数据而不是纯文本推断，减少幻觉，提高定位准确性（能指出具体行号）。

### 规则校验工具（可选扩展）

```python
@tool  
def run_eslint_vue(code: str, rules: list[str]) -> list[dict]:
    """运行指定的 eslint-plugin-vue 规则，返回违规列表"""
```

AI Agent 负责深层语义分析，ESLint 工具负责确定性规则检查，两者互补。

---

## 6. VS Code 插件设计

### 交互流程

1. 用户在编辑器中选中代码（或不选则取整个文件）
2. 右键菜单 / `Cmd+Shift+P` 触发 `Vue Review: Analyze`
3. 侧边栏打开 WebView，显示"分析中..."
4. 后端 SSE 流式返回，WebView 实时渲染结果
5. 每条问题支持点击跳转到对应行

### WebView 展示结构

```
┌─────────────────────────────┐
│ Vue Code Review              │
│ ─────────────────────────── │
│ ● 3 Errors  ▲ 5 Warnings    │
│ ─────────────────────────── │
│ [响应式] ERROR               │
│ 解构 reactive 导致响应式丢失  │
│ 第 12 行 · 点击查看           │
│                              │
│ Before:                      │
│ const { count } = state      │
│                              │
│ After:                       │
│ const count = computed(...)  │
│ ─────────────────────────── │
│ [性能] WARNING               │
│ v-for 使用 index 作为 key    │
└─────────────────────────────┘
```

---

## 7. 数据流

```
用户触发审查
    │
    ▼
Extension 提取代码 + 文件名
    │ POST /review
    ▼
FastAPI 接收请求，启动 LangGraph 工作流
    │
    ▼
Orchestrator 调用 parse_vue_ast 工具获取结构信息
    │
    ├─────────────────────────────────┐
    ▼                                 ▼
并行执行四个子 Agent（各自 RAG 检索 + LLM 分析）
    │                                 │
    └──────────────┬──────────────────┘
                   ▼
           Synthesis Agent 汇总
                   │
                   ▼
           SSE 流式推送结果
                   │
                   ▼
         WebView 实时渲染
```

---

## 8. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 子 Agent 超时 | 跳过该维度，在报告中标注"分析超时" |
| 代码不是合法 Vue SFC | Orchestrator 降级为通用 JS/TS 审查 |
| LLM API 限流 | 指数退避重试，最多 3 次 |
| AST 解析失败 | 降级为纯文本分析，不影响主流程 |
| 代码过长（>5000 行） | 提示用户选择具体代码片段 |

---

## 9. 技术亮点（简历/面试用）

1. **LangGraph 状态机编排**：用有向图管理 agent 生命周期，支持并行、条件分支、错误恢复，而不是简单的链式调用
2. **RAG 补盲点**：针对 Vue 新版本 API 训练数据不足的问题，用 RAG 注入最新文档，可量化对比有无 RAG 时的准确率
3. **Tool Use 提升精度**：AST 解析提供结构化上下文，将幻觉率（错误行号、不存在的问题）从纯 LLM 的 ~30% 降至 <5%
4. **Prompt Caching**：Vue 文档知识库作为 cached system prompt，降低每次审查的 token 成本约 60%
5. **流式输出**：SSE 实时推送，用户不需要等全部分析完才看到结果

---

## 10. 开发阶段规划

| 阶段 | 内容 | 产出 |
|------|------|------|
| Phase 1 | 单 Agent + 基础审查，CLI 调用 | 能跑通的最小版本 |
| Phase 2 | 拆分为 Multi-Agent，加 LangGraph | 架构完整 |
| Phase 3 | 接入 RAG（Vue 文档向量化） | 审查质量提升 |
| Phase 4 | VS Code 插件 + WebView UI | 可演示版本 |
| Phase 5 | AST Tool Use + Prompt Caching | 技术亮点完整 |
