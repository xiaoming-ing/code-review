import pytest
import json
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_health(client):
    """验证服务正常启动。"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_review_returns_sse(client, bad_vue_code):
    response = client.post(
        "/review",
        json={"code": bad_vue_code, "filename": "test.vue"},
    )
    print("\n--- response.text ---")
    print(repr(response.text[:500]))  # 打印前500字符
    print("--- end ---")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # 直接从响应文本里找 data: 行
    lines = response.text.splitlines()
    events = []
    for line in lines:
        if line.startswith("data: ") and line != "data: [DONE]":
            import json
            events.append(json.loads(line[6:]))

    assert len(events) > 0
    assert "summary" in events[0]
    assert "issues" in events[0]


def test_review_rejects_empty_code(client):
    """空代码应被拒绝，返回 422。"""
    response = client.post("/review", json={"code": ""})
    assert response.status_code == 422
