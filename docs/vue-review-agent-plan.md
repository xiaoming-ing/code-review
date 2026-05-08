# Vue 前端代码审查 Agent — 实现计划（Phase 1-2：Python 后端）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 Python 后端，使用 LangGraph 并行调度六个专职 Agent 对 Vue 代码进行六维度审查，通过 FastAPI SSE 端点流式返回结构化审查报告。

**Architecture:** 请求进入 FastAPI → LangGraph 图先解析 Vue SFC 结构，再并行触发六个 reviewer 节点（正确性/安全性/性能/可读性/可维护性/规范性），全部完成后 synthesis 节点汇总输出，全程通过 SSE 流式推送。

**Tech Stack:** Python 3.11, FastAPI, uvicorn, LangGraph 0.2+, anthropic SDK (claude-sonnet-4-6), pydantic, pytest, httpx

---

## 文件结构

```
vue-review-agent/
├── pyproject.toml
├── .env.example
├── main.py                         # FastAPI 入口
├── agents/
│   ├── __init__.py
│   ├── state.py                    # LangGraph ReviewState TypedDict
│   ├── graph.py                    # LangGraph 图定义（节点 + 边）
│   ├── sfc_parser.py               # parse_ast 节点：Vue SFC 解析 tool
│   ├── reviewers.py                # 六个并行 reviewer 节点
│   └── synthesis.py                # synthesis 节点：汇总 + 排序
├── models.py                       # Pydantic: ReviewRequest, Issue, ReviewResult
└── tests/
    ├── conftest.py                  # 共享 fixtures
    ├── fixtures/
    │   ├── bad_component.vue        # 含多种问题的测试 Vue 文件
    │   └── good_component.vue       # 符合规范的 Vue 文件
    ├── test_sfc_parser.py
    ├── test_reviewers.py
    └── test_api.py
```

---

## Task 1: 项目初始化

**Files:**
- Create: `vue-review-agent/pyproject.toml`
- Create: `vue-review-agent/.env.example`
- Create: `vue-review-agent/models.py`
- Create: `vue-review-agent/tests/conftest.py`
- Create: `vue-review-agent/tests/fixtures/bad_component.vue`
- Create: `vue-review-agent/tests/fixtures/good_component.vue`

- [ ] **Step 1: 创建项目目录和 pyproject.toml**

```bash
mkdir -p vue-review-agent/agents vue-review-agent/tests/fixtures
cd vue-review-agent
```

`pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "vue-review-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.40.0",
    "langgraph>=0.2.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"]
```

- [ ] **Step 2: 创建 .env.example**

`.env.example`:
```
ANTHROPIC_API_KEY=your_api_key_here
```

复制为 `.env` 并填入真实 key：
```bash
cp .env.example .env
```

- [ ] **Step 3: 安装依赖**

```bash
pip install -e ".[dev]"
```

Expected: 安装成功，无报错

- [ ] **Step 4: 创建测试 fixture — bad_component.vue**

`tests/fixtures/bad_component.vue`:
```vue
<script>
import { reactive } from 'vue'

export default {
  name: 'userCard',
  props: ['id', 'name'],
  setup() {
    const state = reactive({ count: 0, items: [] })
    const { count } = state

    const API_KEY = 'sk-prod-abc123secret'

    const data = computed(() => {
      state.count = state.count + 1
      return state.items.map(i => i * 2)
    })

    function handle(e) {
      setTimeout(() => {}, 3000)
      eval(e.data)
    }

    return { count, data, handle }
  }
}
</script>

<template>
  <div>
    <ul>
      <li v-for="item in items">{{ item }}</li>
    </ul>
    <span v-html="userInput"></span>
    <p v-if="flag">{{ flag ? val1 : show ? val2 : val3 }}</p>
  </div>
</template>

<style>
.card { color: red; }
</style>
```

- [ ] **Step 5: 创建测试 fixture — good_component.vue**

`tests/fixtures/good_component.vue`:
```vue
<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Props {
  userId: string
  userName: string
}

const props = defineProps<Props>()
const emit = defineEmits<{ update: [value: string] }>()

const DEBOUNCE_DELAY_MS = 300
const searchQuery = ref('')

const filteredName = computed(() => props.userName.trim().toLowerCase())

watch(searchQuery, (newVal) => {
  emit('update', newVal)
}, { debounce: DEBOUNCE_DELAY_MS })
</script>

<template>
  <div class="user-card">
    <p>{{ filteredName }}</p>
    <input v-model="searchQuery" placeholder="Search" />
  </div>
</template>

<style scoped>
.user-card { padding: 16px; }
</style>
```

- [ ] **Step 6: 创建 models.py**

`models.py`:
```python
from pydantic import BaseModel
from typing import Literal, Optional

Severity = Literal["error", "warning", "suggestion"]
Category = Literal["correctness", "security", "performance", "readability", "maintainability", "standards"]

class ReviewRequest(BaseModel):
    code: str
    filename: Optional[str] = None

class Issue(BaseModel):
    severity: Severity
    category: Category
    title: str
    location: str
    description: str
    before: Optional[str] = None
    after: Optional[str] = None

class ReviewResult(BaseModel):
    summary: str
    issues: list[Issue]
```

- [ ] **Step 7: 创建 tests/conftest.py**

`tests/conftest.py`:
```python
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def bad_vue_code() -> str:
    return (FIXTURES_DIR / "bad_component.vue").read_text()

@pytest.fixture
def good_vue_code() -> str:
    return (FIXTURES_DIR / "good_component.vue").read_text()
```

- [ ] **Step 8: 验证项目结构**

```bash
python -c "from models import ReviewRequest, Issue, ReviewResult; print('models ok')"
```

Expected: `models ok`

- [ ] **Step 9: Commit**

```bash
git init
git add pyproject.toml .env.example models.py tests/
git commit -m "feat: project scaffold with models and test fixtures"
```

---

## Task 2: Vue SFC 解析器

**Files:**
- Create: `vue-review-agent/agents/sfc_parser.py`
- Create: `vue-review-agent/tests/test_sfc_parser.py`

- [ ] **Step 1: 写失败测试**

`tests/test_sfc_parser.py`:
```python
from agents.sfc_parser import parse_vue_sfc, extract_ast_info

def test_parse_splits_sections(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    assert "v-for" in sfc.template
    assert "reactive" in sfc.script
    assert ".card" in sfc.style

def test_parse_detects_script_setup(good_vue_code):
    sfc = parse_vue_sfc(good_vue_code)
    assert sfc.is_script_setup is True

def test_parse_non_sfc():
    js_code = "function foo() { return 1; }"
    sfc = parse_vue_sfc(js_code)
    assert sfc.is_sfc is False

def test_extract_detects_v_html(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_v_html"] is True

def test_extract_detects_v_for_without_key(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_v_for_without_key"] is True

def test_extract_detects_eval(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_eval"] is True

def test_extract_detects_style_scoped(good_vue_code):
    sfc = parse_vue_sfc(good_vue_code)
    info = extract_ast_info(good_vue_code, sfc)
    assert info["has_style_scoped"] is True

def test_extract_detects_missing_scoped(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_style_scoped"] is False

def test_extract_detects_hardcoded_secret(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    info = extract_ast_info(bad_vue_code, sfc)
    assert info["has_hardcoded_secret"] is True
```

- [ ] **Step 2: 运行测试，确认全部失败**

```bash
pytest tests/test_sfc_parser.py -v
```

Expected: `ImportError: cannot import name 'parse_vue_sfc'`

- [ ] **Step 3: 实现 agents/sfc_parser.py**

`agents/__init__.py`: (空文件)

`agents/sfc_parser.py`:
```python
import re
from dataclasses import dataclass, field

@dataclass
class VueSFC:
    template: str = ""
    script: str = ""
    style: str = ""
    is_script_setup: bool = False
    is_sfc: bool = False

def parse_vue_sfc(code: str) -> VueSFC:
    sfc = VueSFC()

    template_match = re.search(r'<template[^>]*>(.*?)</template>', code, re.DOTALL)
    script_setup_match = re.search(r'<script\s+setup[^>]*>(.*?)</script>', code, re.DOTALL)
    script_match = re.search(r'<script(?!\s+setup)[^>]*>(.*?)</script>', code, re.DOTALL)
    style_match = re.search(r'<style[^>]*>(.*?)</style>', code, re.DOTALL)

    if template_match or script_setup_match or script_match:
        sfc.is_sfc = True

    if template_match:
        sfc.template = template_match.group(1).strip()

    if script_setup_match:
        sfc.script = script_setup_match.group(1).strip()
        sfc.is_script_setup = True
    elif script_match:
        sfc.script = script_match.group(1).strip()

    if style_match:
        sfc.style = style_match.group(1).strip()

    return sfc

def extract_ast_info(code: str, sfc: VueSFC) -> dict:
    script = sfc.script
    template = sfc.template
    style_attrs = re.findall(r'<style([^>]*)>', code)

    v_for_without_key = (
        bool(re.search(r'v-for=', template))
        and not bool(re.search(r':key=', template))
    )

    has_hardcoded_secret = bool(re.search(
        r'(token|secret|password|api_key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9\-_]{8,}["\']',
        script, re.IGNORECASE
    ))

    return {
        "is_sfc": sfc.is_sfc,
        "is_script_setup": sfc.is_script_setup,
        "total_lines": len(code.splitlines()),
        "script_lines": len(script.splitlines()),
        "template_lines": len(template.splitlines()),
        "has_v_html": "v-html" in template,
        "has_v_for_without_key": v_for_without_key,
        "has_eval": "eval(" in script or "new Function(" in script,
        "has_hardcoded_secret": has_hardcoded_secret,
        "has_style_scoped": any("scoped" in attrs for attrs in style_attrs),
        "uses_reactive": "reactive(" in script,
        "uses_ref": "ref(" in script,
        "defines_props": "defineProps" in script or "props:" in script,
        "defines_emits": "defineEmits" in script or "emits:" in script,
    }
```

- [ ] **Step 4: 运行测试，确认全部通过**

```bash
pytest tests/test_sfc_parser.py -v
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add agents/ tests/test_sfc_parser.py
git commit -m "feat: Vue SFC parser with AST info extraction"
```

---

## Task 3: LangGraph 状态定义 + 图骨架

**Files:**
- Create: `vue-review-agent/agents/state.py`
- Modify: `vue-review-agent/agents/graph.py`（新建）

- [ ] **Step 1: 创建 agents/state.py**

`agents/state.py`:
```python
from typing import TypedDict, Annotated, Optional
import operator

class ReviewState(TypedDict):
    code: str
    filename: str
    ast_info: dict
    # operator.add 使并行节点的结果自动合并到同一列表
    issues: Annotated[list, operator.add]
    final_report: Optional[dict]
```

- [ ] **Step 2: 创建 agents/graph.py 骨架**

`agents/graph.py`:
```python
from langgraph.graph import StateGraph, START, END
from agents.state import ReviewState

REVIEWER_NODES = [
    "correctness",
    "security",
    "performance",
    "readability",
    "maintainability",
    "standards",
]

def build_graph():
    graph = StateGraph(ReviewState)

    # 节点将在后续 Task 中注册
    # graph.add_node("parse_ast", ...)
    # graph.add_node("correctness", ...)
    # ...
    # graph.add_node("synthesis", ...)

    return graph

# 占位，Task 5 完成后替换
compiled_graph = None
```

- [ ] **Step 3: 验证导入正常**

```bash
python -c "from agents.state import ReviewState; from agents.graph import build_graph; print('state + graph ok')"
```

Expected: `state + graph ok`

- [ ] **Step 4: Commit**

```bash
git add agents/state.py agents/graph.py
git commit -m "feat: LangGraph state definition and graph skeleton"
```

---

## Task 4: 六个并行 Reviewer Agent

**Files:**
- Create: `vue-review-agent/agents/reviewers.py`
- Create: `vue-review-agent/tests/test_reviewers.py`

- [ ] **Step 1: 写失败测试**

`tests/test_reviewers.py`:
```python
import pytest
import json
from agents.reviewers import (
    correctness_reviewer,
    security_reviewer,
    performance_reviewer,
    readability_reviewer,
    maintainability_reviewer,
    standards_reviewer,
)
from agents.sfc_parser import parse_vue_sfc, extract_ast_info

@pytest.fixture
def bad_state(bad_vue_code):
    sfc = parse_vue_sfc(bad_vue_code)
    return {
        "code": bad_vue_code,
        "filename": "bad_component.vue",
        "ast_info": extract_ast_info(bad_vue_code, sfc),
        "issues": [],
        "final_report": None,
    }

def test_security_catches_v_html(bad_state):
    result = security_reviewer(bad_state)
    issues = result["issues"]
    assert any(i["category"] == "security" for i in issues)
    assert any("v-html" in i["title"].lower() or "xss" in i["title"].lower() for i in issues)

def test_security_catches_eval(bad_state):
    result = security_reviewer(bad_state)
    issues = result["issues"]
    assert any("eval" in i["title"].lower() for i in issues)

def test_performance_catches_v_for_key(bad_state):
    result = performance_reviewer(bad_state)
    issues = result["issues"]
    assert any("key" in i["title"].lower() or "v-for" in i["title"].lower() for i in issues)

def test_standards_catches_missing_scoped(bad_state):
    result = standards_reviewer(bad_state)
    issues = result["issues"]
    assert any("scoped" in i["title"].lower() or "style" in i["title"].lower() for i in issues)

def test_reviewer_returns_list_of_issues(bad_state):
    result = correctness_reviewer(bad_state)
    assert "issues" in result
    assert isinstance(result["issues"], list)
    for issue in result["issues"]:
        assert "severity" in issue
        assert "category" in issue
        assert "title" in issue
        assert issue["severity"] in ("error", "warning", "suggestion")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/test_reviewers.py -v
```

Expected: `ImportError: cannot import name 'correctness_reviewer'`

- [ ] **Step 3: 实现 agents/reviewers.py**

`agents/reviewers.py`:
```python
import json
import os
from anthropic import Anthropic
from agents.state import ReviewState

client = Anthropic()
MODEL = "claude-sonnet-4-6"

REVIEWER_CONFIGS = {
    "correctness": {
        "focus": "正确性",
        "checks": """
- ref vs reactive 选择错误（解构 reactive 导致响应式丢失）
- computed 内有副作用（在 computed 中修改外部状态）
- v-model 在子组件中未使用 defineModel 正确绑定（Vue 3.4+）
- watch 依赖项声明不完整导致不触发
- 异步操作未处理错误（无 try/catch）
- Props 未声明类型导致运行时错误
""",
    },
    "security": {
        "focus": "安全性",
        "checks": """
- 使用 v-html 渲染未过滤的用户输入（XSS 风险）
- API 密钥、Token 硬编码在组件内
- eval() 或 new Function() 执行动态代码
- 路由参数直接渲染到页面未做转义
- localStorage 存储敏感信息（密码、token 明文）
""",
    },
    "performance": {
        "focus": "性能",
        "checks": """
- v-for 缺少 :key 或使用 index 作为 key
- 昂贵计算未用 computed 缓存，放在 methods 或 template 表达式中
- 未使用 defineAsyncComponent 懒加载大型子组件
- v-if 与 v-show 场景混用（频繁切换应用 v-show）
- watch 中做大量同步计算未加防抖
""",
    },
    "readability": {
        "focus": "可读性",
        "checks": """
- 变量/函数命名含糊（data、flag、temp、handle）
- Template 内嵌套三元表达式超过两层
- 魔法数字未提取为具名常量（如 setTimeout(fn, 3000)）
- 复杂条件逻辑未提取为 computed 或命名函数
- 单个函数超过 50 行
""",
    },
    "maintainability": {
        "focus": "可维护性",
        "checks": """
- 业务逻辑未抽离 composable，复用性差
- 组件承担多个不相关职责（SRP 违反）
- Props 定义缺少默认值或 validator
- 父子组件通过 ref 直接操作对方内部状态（破坏封装）
- 深层 props drilling（超过三层应考虑 provide/inject）
""",
    },
    "standards": {
        "focus": "规范性",
        "checks": """
- 组件命名不符合 PascalCase 或非 multi-word
- 事件名未使用 kebab-case
- <style> 未加 scoped 且未使用 CSS Modules
- Emits 未显式声明（Vue 3 要求 defineEmits）
- 文件结构不符合约定顺序（script → template → style）
""",
    },
}

REVIEWER_SYSTEM_PROMPT = """你是一位专注于 Vue 3 代码{focus}审查的专家。
仅审查以下问题，不审查其他维度：
{checks}

用中文返回 JSON 数组，每个问题一个对象。如果没有发现问题，返回空数组 []。
格式（严格遵守，不要添加额外字段）：
[
  {{
    "severity": "error" | "warning" | "suggestion",
    "category": "{category}",
    "title": "简短问题标题（10字以内）",
    "location": "第 N 行 或 template/script/style 区域",
    "description": "具体问题说明（20-50字）",
    "before": "有问题的代码片段（可选，单行）",
    "after": "建议修改后的代码（可选，单行）"
  }}
]

只返回 JSON，不要任何解释文字。"""

def _call_reviewer(category: str, state: ReviewState) -> dict:
    config = REVIEWER_CONFIGS[category]
    system = REVIEWER_SYSTEM_PROMPT.format(
        focus=config["focus"],
        checks=config["checks"],
        category=category,
    )
    user_content = f"""文件名: {state.get('filename', '未知')}

AST 分析结果:
{json.dumps(state['ast_info'], ensure_ascii=False, indent=2)}

完整代码:
{state['code']}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text.strip()
    # 清理可能的 markdown 代码块
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        issues = json.loads(raw)
    except json.JSONDecodeError:
        issues = []

    return {"issues": issues}


def correctness_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("correctness", state)

def security_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("security", state)

def performance_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("performance", state)

def readability_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("readability", state)

def maintainability_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("maintainability", state)

def standards_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("standards", state)
```

- [ ] **Step 4: 运行测试（需要真实 API Key）**

```bash
pytest tests/test_reviewers.py -v -s
```

Expected: `5 passed`（会调用真实 API，耗时约 30s）

- [ ] **Step 5: Commit**

```bash
git add agents/reviewers.py tests/test_reviewers.py
git commit -m "feat: six parallel reviewer agents with structured JSON output"
```

---

## Task 5: Synthesis Agent + 完整 LangGraph 图

**Files:**
- Create: `vue-review-agent/agents/synthesis.py`
- Modify: `vue-review-agent/agents/graph.py`（完成图定义）

- [ ] **Step 1: 写失败测试**

在 `tests/test_reviewers.py` 末尾追加：
```python
from agents.synthesis import synthesis_node

def test_synthesis_produces_report():
    state = {
        "code": "...",
        "filename": "test.vue",
        "ast_info": {},
        "issues": [
            {"severity": "error", "category": "security", "title": "XSS 风险",
             "location": "第 5 行", "description": "v-html 渲染未过滤内容",
             "before": None, "after": None},
            {"severity": "warning", "category": "performance", "title": "v-for 缺少 key",
             "location": "第 12 行", "description": "应添加 :key 属性",
             "before": None, "after": None},
        ],
        "final_report": None,
    }
    result = synthesis_node(state)
    report = result["final_report"]
    assert "summary" in report
    assert "issues" in report
    assert len(report["issues"]) == 2
    # errors 排在 warnings 前面
    assert report["issues"][0]["severity"] == "error"

def test_synthesis_deduplicates_identical_issues():
    duplicate_issue = {
        "severity": "error", "category": "security", "title": "XSS 风险",
        "location": "第 5 行", "description": "v-html 渲染未过滤内容",
        "before": None, "after": None
    }
    state = {
        "code": "", "filename": "", "ast_info": {},
        "issues": [duplicate_issue, duplicate_issue],
        "final_report": None,
    }
    result = synthesis_node(state)
    assert len(result["final_report"]["issues"]) == 1
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/test_reviewers.py::test_synthesis_produces_report -v
```

Expected: `ImportError: cannot import name 'synthesis_node'`

- [ ] **Step 3: 实现 agents/synthesis.py**

`agents/synthesis.py`:
```python
from agents.state import ReviewState

SEVERITY_ORDER = {"error": 0, "warning": 1, "suggestion": 2}

def synthesis_node(state: ReviewState) -> dict:
    raw_issues = state.get("issues", [])

    # 去重：以 (category, title, location) 为唯一键
    seen = set()
    unique_issues = []
    for issue in raw_issues:
        key = (issue.get("category"), issue.get("title"), issue.get("location"))
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    # 按严重程度排序
    sorted_issues = sorted(
        unique_issues,
        key=lambda i: SEVERITY_ORDER.get(i.get("severity", "suggestion"), 2)
    )

    error_count = sum(1 for i in sorted_issues if i.get("severity") == "error")
    warning_count = sum(1 for i in sorted_issues if i.get("severity") == "warning")
    suggestion_count = sum(1 for i in sorted_issues if i.get("severity") == "suggestion")

    parts = []
    if error_count:
        parts.append(f"{error_count} 个 Error")
    if warning_count:
        parts.append(f"{warning_count} 个 Warning")
    if suggestion_count:
        parts.append(f"{suggestion_count} 个 Suggestion")

    summary = f"发现 {', '.join(parts)}" if parts else "未发现明显问题"

    return {"final_report": {"summary": summary, "issues": sorted_issues}}
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/test_reviewers.py::test_synthesis_produces_report tests/test_reviewers.py::test_synthesis_deduplicates_identical_issues -v
```

Expected: `2 passed`

- [ ] **Step 5: 完成 agents/graph.py**

`agents/graph.py`（完整替换）:
```python
from langgraph.graph import StateGraph, START, END
from agents.state import ReviewState
from agents.sfc_parser import parse_vue_sfc, extract_ast_info
from agents.reviewers import (
    correctness_reviewer, security_reviewer, performance_reviewer,
    readability_reviewer, maintainability_reviewer, standards_reviewer,
)
from agents.synthesis import synthesis_node

REVIEWER_NODES = [
    "correctness", "security", "performance",
    "readability", "maintainability", "standards",
]

REVIEWER_FNS = {
    "correctness": correctness_reviewer,
    "security": security_reviewer,
    "performance": performance_reviewer,
    "readability": readability_reviewer,
    "maintainability": maintainability_reviewer,
    "standards": standards_reviewer,
}

def parse_ast_node(state: ReviewState) -> dict:
    sfc = parse_vue_sfc(state["code"])
    return {"ast_info": extract_ast_info(state["code"], sfc)}

def build_graph():
    graph = StateGraph(ReviewState)

    graph.add_node("parse_ast", parse_ast_node)
    for name, fn in REVIEWER_FNS.items():
        graph.add_node(name, fn)
    graph.add_node("synthesis", synthesis_node)

    graph.add_edge(START, "parse_ast")
    for name in REVIEWER_NODES:
        graph.add_edge("parse_ast", name)
        graph.add_edge(name, "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()

compiled_graph = build_graph()
```

- [ ] **Step 6: 验证图可以编译**

```bash
python -c "from agents.graph import compiled_graph; print('graph compiled ok')"
```

Expected: `graph compiled ok`

- [ ] **Step 7: Commit**

```bash
git add agents/synthesis.py agents/graph.py tests/test_reviewers.py
git commit -m "feat: synthesis node and complete LangGraph parallel graph"
```

---

## Task 6: FastAPI 服务 + SSE 端点

**Files:**
- Create: `vue-review-agent/main.py`
- Create: `vue-review-agent/tests/test_api.py`

- [ ] **Step 1: 写失败测试**

`tests/test_api.py`:
```python
import pytest
import json
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    from main import app
    return TestClient(app)

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_review_returns_sse(client, bad_vue_code):
    with client.stream("POST", "/review", json={"code": bad_vue_code, "filename": "test.vue"}) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                events.append(payload)
                break  # 收到第一个事件即可
        
        assert len(events) > 0
        assert "summary" in events[0]
        assert "issues" in events[0]

def test_review_rejects_empty_code(client):
    response = client.post("/review", json={"code": ""})
    assert response.status_code == 422
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/test_api.py::test_health -v
```

Expected: `ImportError: cannot import name 'app'`

- [ ] **Step 3: 实现 main.py**

`main.py`:
```python
import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import field_validator
from dotenv import load_dotenv
from models import ReviewRequest
from agents.graph import compiled_graph

load_dotenv()

app = FastAPI(title="Vue Review Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/review")
async def review_code(request: ReviewRequest):
    if not request.code.strip():
        raise HTTPException(status_code=422, detail="code cannot be empty")

    initial_state = {
        "code": request.code,
        "filename": request.filename or "unknown.vue",
        "ast_info": {},
        "issues": [],
        "final_report": None,
    }

    async def event_stream():
        async for event in compiled_graph.astream(initial_state):
            if "synthesis" in event:
                report = event["synthesis"]["final_report"]
                yield f"data: {json.dumps(report, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 4: 运行所有 API 测试**

```bash
pytest tests/test_api.py -v
```

Expected: `3 passed`（test_review_returns_sse 会调用真实 API，约 60s）

- [ ] **Step 5: 手动启动服务器，做冒烟测试**

```bash
uvicorn main:app --reload --port 8000
```

新建终端，发送测试请求：
```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"code": "<script>\nconst key = \"sk-secret\"\n</script><template><span v-html=\"x\"></span></template><style>.a{}</style>", "filename": "test.vue"}' \
  --no-buffer
```

Expected: SSE 事件流，包含 `security` 类别的 issue（XSS 风险 + 硬编码密钥）

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_api.py
git commit -m "feat: FastAPI server with SSE streaming endpoint"
```

---

## Task 7: 端到端集成测试

**Files:**
- Create: `vue-review-agent/tests/test_integration.py`

- [ ] **Step 1: 写集成测试**

`tests/test_integration.py`:
```python
import pytest
from agents.graph import compiled_graph
from agents.sfc_parser import parse_vue_sfc, extract_ast_info

@pytest.mark.asyncio
async def test_full_pipeline_bad_component(bad_vue_code):
    initial_state = {
        "code": bad_vue_code,
        "filename": "bad_component.vue",
        "ast_info": {},
        "issues": [],
        "final_report": None,
    }

    final_state = await compiled_graph.ainvoke(initial_state)

    report = final_state["final_report"]
    assert report is not None
    assert len(report["issues"]) > 0

    categories = {i["category"] for i in report["issues"]}
    # bad_component 应覆盖安全、性能、规范三个维度
    assert "security" in categories
    assert "performance" in categories
    assert "standards" in categories

    # errors 必须排在 warnings 前
    severities = [i["severity"] for i in report["issues"]]
    error_positions = [i for i, s in enumerate(severities) if s == "error"]
    warning_positions = [i for i, s in enumerate(severities) if s == "warning"]
    if error_positions and warning_positions:
        assert max(error_positions) < min(warning_positions)

@pytest.mark.asyncio
async def test_full_pipeline_good_component_fewer_errors(good_vue_code, bad_vue_code):
    async def run(code, filename):
        state = {"code": code, "filename": filename, "ast_info": {}, "issues": [], "final_report": None}
        result = await compiled_graph.ainvoke(state)
        return result["final_report"]["issues"]

    bad_issues = await run(bad_vue_code, "bad.vue")
    good_issues = await run(good_vue_code, "good.vue")

    bad_errors = [i for i in bad_issues if i["severity"] == "error"]
    good_errors = [i for i in good_issues if i["severity"] == "error"]
    assert len(bad_errors) > len(good_errors)
```

- [ ] **Step 2: 安装 pytest-asyncio**

```bash
pip install pytest-asyncio
```

在 `pyproject.toml` 的 `[project.optional-dependencies]` dev 列表中添加 `"pytest-asyncio>=0.23.0"`

在项目根目录创建 `pytest.ini`：
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 3: 运行集成测试**

```bash
pytest tests/test_integration.py -v -s
```

Expected: `2 passed`（约 2-3 分钟，并行调用 6 个 Agent）

- [ ] **Step 4: 运行全部测试套件**

```bash
pytest tests/ -v --ignore=tests/test_integration.py  # 快速测试
pytest tests/ -v                                       # 含集成测试（需 API Key）
```

Expected: 全部 pass

- [ ] **Step 5: 最终 Commit**

```bash
git add tests/test_integration.py pytest.ini pyproject.toml
git commit -m "test: end-to-end integration tests for full review pipeline"
```

---

## 完成后的验证清单

- [ ] `pytest tests/ -v --ignore=tests/test_integration.py` 全部 pass（无 API Key 也能运行）
- [ ] `uvicorn main:app --reload` 启动无报错
- [ ] curl 调用 `/review` 返回包含 security issue 的 SSE 事件
- [ ] 对 `bad_component.vue` 审查结果覆盖 security + performance + standards 三个维度

---

## 下一步计划

| 计划 | 内容 |
|------|------|
| Phase 3 | 接入 RAG：ChromaDB 索引 Vue 官方文档，注入检索结果提升建议质量 |
| Phase 4 | VS Code 插件：TypeScript + WebView 消费 SSE，侧边栏展示结果 |
| Phase 5 | Prompt Caching：Vue 文档作为 cached system prompt，降低 ~60% token 成本 |
