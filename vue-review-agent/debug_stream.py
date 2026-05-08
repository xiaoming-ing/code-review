import asyncio
import json
from dotenv import load_dotenv
from agents.graph import compiled_graph

load_dotenv()

async def main():
    state = {
        "code": "<script>\nconst k = 'sk-secret123'\n</script><template><span v-html='x'></span></template><style>.a{}</style>",
        "filename": "test.vue",
        "ast_info": {},
        "issues": [],
        "final_report": None,
    }
    async for event in compiled_graph.astream(state, stream_mode="updates"):
        print("EVENT KEYS:", list(event.keys()))
        print("EVENT:", json.dumps(event, ensure_ascii=False, default=str)[:200])
        print("---")

asyncio.run(main())
