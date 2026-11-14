"""Review UI 14/11 đợt 3 (FE-9): nén gzip cho response lớn.

/api/network trên vùng demo ~283 KB JSON không nén (toạ độ 7 chữ số); nén mọi response từ 1 KB khi client nhận gzip.
Đồ thị mini quá nhỏ để /api/network vượt ngưỡng, nên test bằng /api/route có trace. Response nhỏ
(/api/health) không cần nén. Nội dung giải nén phải đúng như không nén.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


def test_large_response_is_gzipped_when_accepted(client):
    body = {"source": {"lat": 10.77251, "lon": 106.69801}, "target": {"lat": 10.77252, "lon": 106.70532},
            "algorithms": ["dijkstra", "astar", "alt", "bidijkstra"], "trace_limit": 5000}
    plain = client.post("/api/route", json=body, headers={"Accept-Encoding": "identity"})
    gz = client.post("/api/route", json=body, headers={"Accept-Encoding": "gzip"})
    assert plain.headers.get("content-encoding") is None
    assert len(plain.content) >= 1000                  # đủ lớn để vượt ngưỡng nén (trace + hình học)
    assert gz.headers.get("content-encoding") == "gzip"
    # TestClient tự giải nén; runtime_ms là số đo giờ nên khác giữa hai lần chạy, bỏ khỏi phép so.
    strip = lambda r: {**r, "results": {k: {**v, "runtime_ms": None} for k, v in r["results"].items()}}
    assert strip(gz.json()) == strip(plain.json())


def test_small_response_not_compressed(client):
    r = client.get("/api/health", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") is None
