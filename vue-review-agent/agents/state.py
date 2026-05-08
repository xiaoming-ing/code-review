from typing import TypedDict,Annotated,Optional
import operator

class ReviewState(TypedDict):
    """
    LangGraph 图的全局状态，贯穿整个审查流程。

    LangGraph 每个节点接收当前state,返回要更新的字段。
    issues 字段用Annotated[list,operator.add]声明，
    这样六个并行reviewer 各自返回的 issues 列表会自动合并（append),
    而不是互相覆盖--这是并行节点能正确汇总结果的关键。
    """
    code: str   # 待审查的原始代码
    filename:str  # 文件名，辅助 Agent 判断组件命名规范
    ast_info:dict  # sfc_parser 提取结构化特征
    issues: Annotated[list,operator.add] # 各 reviewer 发现的问题，自动合并
    final_report: Optional[dict] # synthesis 节点生成的最终报告
    