import os
from openai import OpenAI
from agents.state import ReviewState
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)
MODEL = "deepseek-chat"

# 每个review 的审查重点配置，统一管理避免散落在各函数中
REVIEWER_CONFIGS = {
    "correctness":{
        "focus":"正确性",
        "checks":"""
        - ref vs reactive 选择错误（结构 reactive 导致响应式丢失）
        - computed 内有副作用（在 computed 中修改外部状态）
        - v-model 在子组件中未使用 definedModel 正确绑定（Vue 3.4+)
        - watch 依赖项声明不完整导致不触发
        - 异步操作未处理错误（🤔try/catch）
        - Props 未声明类型导致运行时错误
        """
    },
    "security": {
        "focus":"安全性",
        "checks":"""
        - 使用 v-html渲染未过滤的用户输入（XSS 风险）
        - API 密钥、Token 硬编码在组件内
        - eval() 或 new Function() 执行动态代码
        - 路由参数直接渲染到页面未做转义
        - localStorage 存敏感信息（密码、token 明文）
        """
    },
    "performance": {
        "focus": "性能",
        "checks":"""
        - v-for 缺少 :key 或使用 index 作为key
        - 昂贵计算未用 computed 缓存，放在 methods 或 template 表达式中
        - 未使用 defineAsyncComponent 懒加载大型子组件
        - v-if 与 v-show 场景混用（频繁切换应用 v-show）
        - watch 中做大量同步计算未加防抖
        """
    },
    "readability": {
        "focus":"可读性",
        "checks":"""
        - 变量/函数命名含糊 (data、flag、temp、handle)
        - Template 内嵌套三元表达式超过两层
        - 魔法数字未提取为具名常量 （如 setTimeout(fn,3000)）
        - 复杂条件逻辑未提取为 comouted 或命名函数
        - 单个函数超过 50 行
        """
    },
    "maintainability": {
        "focus": "可维护性",
        "checks":"""
        - 业务逻辑未抽离 composable,复用性差
        - 组件承担多个不相关职责（SRP 违反）
        - Props 定义缺少默认值或validator
        - 父组件通过 ref 直接操作对方内部状态（破坏封装）
        - 深层 props drilling (超过三层应考虑 provide/inject)
        """
    },
    "standards": {
        "focus":"规范性",
        "checks":"""
        - 组件命名不符合 PascalCase 或非 multi-word
        - 事件名未使用 kebad-case
        - <style> 未加scoped 且未使用 CSS Modules
        - Emits 未显示声明 (Vue3 要求 defineEmits)
        - 文件结构不符合约定顺序 (script -> template -> style)
        """
    }
}

# system prompt 模板
REVIEWER_SYSTEM_PROMPT = """你是一位专注于 vue3 代码{focus}审查的专家。
仅审查以下问题，不审查其他维度：
{checks}

用中文返回 JSON 数组，每个问题一个对象。如果没有发现问题，返回空数组 [].
格式（严格遵守，不要添加额外字段）：
[
    {{
        "severity": "error" | "warning" | "suggestion",
        "category": "{category}",
        "title": "简短问题标题（10字以内）",
        "location": "第N行或 template/script/style 区域",
        "description": "具体问额题说明 （20-50字）",
        "before": "有问题的代码片段（可选，单行）",
        "after": "建议修改后的代码（可选，单行）"
    }}
]

只返回 JSON，不要任何解释文字。
"""

def _call_reviewer(category:str,state: ReviewState) -> dict:
    """
    通用 reviewer 调用逻辑，六个 reviewer 共用。

    把 ast_info 和完整代码一起发给 LLM：
    - ast_info 提供确定性的结构特征（有没有 v-html、eval等），减少幻觉
    - 完整代码让 LLM 理解上下文，给出准确的行号和改进建议
    """
    config = REVIEWER_CONFIGS[category]
    system = REVIEWER_SYSTEM_PROMPT.format(
        focus=config["focus"],
        checks=config["checks"],
        category=category,
    )
    user_content = f"""文件名：{state.get('filename','未知')}

    AST 分析结果：
    {json.dumps(state['ast_info'],ensure_ascii=False,indent=2)}

    完整代码：
    {state['code']}
    """

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":user_content}
        ]
    )

    raw = response.choices[0].message.content.strip()

    # LLM 有时会把 JSON 包在 ```json ...```代码块里，需要去掉
    if raw.startswith("```"):
        raw = raw.split("\n",1)[1].rsplit("```",1)[0].strip()
    
    try:
        issues = json.loads(raw)
    except json.JSONDecodeError:
        # 解析失败时返回空列表，不影响其他 reviewer 的结果
        issues = []
    
    return {"issues":issues}

def correctness_reviewer(state:ReviewState) -> dict:
    return _call_reviewer("correctness",state)

def security_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("security",state)

def performance_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("performance",state)

def readability_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("readability",state)

def maintainability_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("maintainability",state)

def standards_reviewer(state: ReviewState) -> dict:
    return _call_reviewer("standards",state)
