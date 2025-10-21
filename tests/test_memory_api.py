import os

from fastapi.testclient import TestClient

from atlas.api.app import app


def client():
    return TestClient(app)


def test_memory_write_and_query():
    c = client()
    # write
    r1 = c.post(
        "/memory/write",
        json={"id": "doc1", "vector": [0.1, 0.0, 0.8, 0.0, 0.2], "meta": {"title": "hello"}},
    )
    assert r1.status_code == 200
    assert r1.json()["ok"] is True

    # query
    r2 = c.post("/memory/query", json={"vector": [0.1, 0.0, 0.7, 0.0, 0.2], "top_k": 3})
    assert r2.status_code == 200
    data = r2.json()
    assert "items" in data and len(data["items"]) >= 1
    assert data["items"][0]["id"] == "doc1"
