from langgraph.graph import StateGraph,START,END
from agents.state import ReviewState
from agents.sfc_parser import parse_vue_sfc,extract_ast_info
from agents.reviewers import (
    correctness_reviewer,
    security_reviewer,
    performance_reviewer,
    readability_reviewer,
    maintainability_reviewer,
    standards_reviewer,
)
from agents.synthesis import synthesis_node

# 六个并行 reviewer 节点的名称，后续Task 会逐一注册
REVIEWER_FNS = {
    "correctness":correctness_reviewer,
    "security":security_reviewer,
    "performance": performance_reviewer,
    "readability": readability_reviewer,
    "maintainability": maintainability_reviewer,
    "standards": standards_reviewer
}

def parse_ast_node(state: ReviewState) -> dict:
    """解析SFC 结构，结果存入 state 供所有 reviewer 共享。"""
    sfc = parse_vue_sfc(state["code"])
    return {"ast_info":extract_ast_info(state["code"],sfc)}

def build_graph():
    """
    构建LangGraph 审查图
    
    最终图的拓扑：
    START -> parse_ast -> [六个 review 并行] -> synthesis -> END
    """
    graph = StateGraph(ReviewState)

    # 注册所有节点
    graph.add_node("parse_ast",parse_ast_node)
    for name,fn in REVIEWER_FNS.items():
        graph.add_node(name,fn)
    graph.add_node("synthesis",synthesis_node)

    # 连接边：parse_ast 完成后并行触发所有 reviewer
    graph.add_edge(START, "parse_ast")
    for name in REVIEWER_FNS:
        graph.add_edge("parse_ast",name)
        graph.add_edge(name,"synthesis")
    graph.add_edge("synthesis",END)

    return graph.compile()


compiled_graph = build_graph()