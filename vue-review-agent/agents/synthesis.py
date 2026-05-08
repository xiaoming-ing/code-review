from agents.state import ReviewState

# 严重程度排序权重，error 最优先展示
SEVERITY_ORDER = {"error":0,"warning":1,"suggestion":2}

def synthesis_node(state: ReviewState) -> dict:
    """
    汇总六个并行 reviewer 的结果，去重并按严重程度排序。

    不再调用LLM，纯逻辑处理：
    - 去重避免多个 reviewer 报同一问题（如 v-html 被安全和规范同时发现）
    - 排序让用户优先看到最严重的问题
    """
    raw_issues = state.get("issues",[])

    # 以 (category,title,location)为唯一键去重
    # 不用 description 做 key,因为不同 reviewer 措辞可能略有不同
    seen = set()
    unique_issues = []
    for issue in raw_issues:
        key = (issue.get("category"),issue.get("title"),issue.get("location"))
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    sorted_issues = sorted(
        unique_issues,
        key=lambda i: SEVERITY_ORDER.get(i.get("severity","suggestion"),2)
    )

    error_count = sum(1 for i in sorted_issues if i.get("severity") == "error")
    warning_count = sum(1 for i in sorted_issues if i.get("severity") == "warning")
    suggestion_count = sum(1 for i in sorted_issues if i.get("severity") == "suggestion")

    parts = []
    if error_count:
        parts.append(f"{error_count}个Error")
    if warning_count:
        parts.append(f"{warning_count} 个 Warning")
    if suggestion_count:
        parts.append(f"{suggestion_count} 个 Suggestion")
    
    summary = f"发现{', '.join(parts)}" if parts else "未发现明显问题"

    return {"final_report":{"summary":summary,"issues":sorted_issues}}

