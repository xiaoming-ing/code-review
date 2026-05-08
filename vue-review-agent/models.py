from typing import Literal,Optional
from pydantic import BaseModel

Severity = Literal["error","warning","suggestion"] # Literal 字面量类型
Category = Literal["correctness","security","performance","readability","maintainability","standars"]

class ReviewRequest(BaseModel):
    code: str
    filename: Optional[str] =  None

class Issue(BaseModel):
    severity: Severity
    category: Category
    title: str
    location:str
    description:str
    before: Optional[str] = None
    after: Optional[str] = None

class ReviewResult(BaseModel):
    summary: str
    issues: list[Issue]