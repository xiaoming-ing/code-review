import pytest
from agents.reviewers import (
    correctness_reviewer,
    security_reviewer,
    performance_reviewer,
    readability_reviewer,
    maintainability_reviewer,
    standards_reviewer,
)
from agents.sfc_parser import parse_vue_sfc, extract_ast_info
from agents.synthesis import synthesis_node


@pytest.fixture
def bad_state(bad_vue_code):
    """构造一个包含问题代码的完整 state，模拟图运行时的输入。"""
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
    # error 必须排在 warning 前面
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
    # 两条相同的问题应合并为一条
    assert len(result["final_report"]["issues"]) == 1
