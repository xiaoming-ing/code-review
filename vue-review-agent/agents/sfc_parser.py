from dataclasses import dataclass
import re

@dataclass
class VueSFC:
    """Vue 单文件组件解析结果，存储是哪个块的原始文本和元信息。"""
    template: str = ""
    script: str = ""
    style: str = ""
    is_script_setup: bool = False # 是否使用了 <script setup>语法（Vue 3推荐写法）
    is_sfc: bool = False # 是否是合法的 Vue SFC 

def parse_vue_sfc(code: str) -> VueSFC:
    """
    用正则把Vue SFC 拆成 template / script / style 三块。


    没有用 vue-parser 等专业库，原因：
    1. 避免引入 Node.js 依赖（纯 Python 环境）
    2. 我们只需要块级文本，不需要完整 AST（抽象语法树）
    正则对嵌套标签有局限，但 SFC 顶层块不会嵌套，这里够用。
    """
    sfc = VueSFC()

    template_match = re.search(r'<template[^>]*>(.*?)</template>',code,re.DOTALL)

    # script setup和普通script 用不同正则区分：
    # (?!\s+setup)是负向前瞻，匹配没有 setup 属性的 <script>
    script_setup_match = re.search(r'<script\s+setup[^>]*>(.*?)</script>',code,re.DOTALL)
    script_match = re.search(r'<script(?!\s+setup)[^>]*>(.*?)</script>',code,re.DOTALL)

    style_match = re.search(r'<style[^>]*>(.*)</style>',code,re.DOTALL)

    # 有任意一个块就认定为SFC，否则当作普通JS/TS 降级处理
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

def extract_ast_info(code:str,sfc:VueSFC) -> dict:
    """
    从解析结果中提取结构化特征，供各个reviewer Agent使用。

    返回的dict 作为AST 分析结果注入 LLM prompt,
    让 Agent 基于确定性数据做判断，而不是让LLM自己从文本猜结构，
    可以显著减少幻觉（错误行号、不存在问题）。
    """
    script = sfc.script
    template = sfc.template

    # 提取所有<style> 标签的属性部分，用于判断是否有scoped
    style_attrs = re.findall(r'<style([^>]*)>', code)

    # v-for 存在但整个template 里没有 :key= 就判定为缺少 key
    # 粗粒度监测，无法区分多个 v-for 各自是否有key,但对review 够用
    v_for_without_key = (
        bool(re.search(r'v-for=',template))
        and not bool(re.search(r':key=',template))
    )

    # 用关键词正则匹配硬编码密钥，覆盖常见变量名模式
    # 要求值长度 >= 8，避免短字符串误报
    has_hardcoded_secret = bool(re.search(
        r'(token|secret|password|api_key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9\-_]{8,}["\']',
        script, re.IGNORECASE
    ))

    return {
        "is_sfc":sfc.is_sfc,
        "is_script_setup":sfc.is_script_setup,
        "total_lines":len(code.splitlines()),
        "script_lines": len(script.splitlines()),
        "template_lines":len(template.splitlines()),
        "has_v_html":"v-html" in template,
        "has_v_for_without_key":v_for_without_key,
        # eval() 和 new Function() 都能执行动态代码，是高危安全问题
        "has_eval":"eval(" in script or "new Function(" in script,
        "has_hardcoded_secret":has_hardcoded_secret,
        "has_style_scoped":any("scoped" in attrs for attrs in style_attrs),
        "uses_reactive":"reactive(" in script,
        "uses_ref":"ref(" in script,
        "defines_props":"defineProps" in script or "props:" in script,
        "defines_emits":"defineemits" in script or "emits:" in script,
    }