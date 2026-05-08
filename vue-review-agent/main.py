
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from models import ReviewRequest
from agents.graph import compiled_graph
import json

load_dotenv()

app = FastAPI(title="Vue 审核Agent")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/review")
async def review_code(request:ReviewRequest):
    if not request.code.strip():
        raise HTTPException(status_code=422, detail="code cannot be empty")

    initial_state = {
        "code":request.code,
        "filename":request.filename or "unknown.vue",
        "ast_info":{},
        "issues":[],
        "final_report":None
    }

    async def event_stream():
        """
        用SSE 格式流式推送审查结果。
        LangGraph astream 每个节点完成时产出一个事件，
        我们只关心 synthesis 节点的输出（最终报告）。
        """
        async for event in compiled_graph.astream(initial_state,stream_mode="updates"):
            if "synthesis" in event:
                report = event["synthesis"]["final_report"]
                yield f"data: {json.dumps(report,ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(),media_type="text/event-stream")