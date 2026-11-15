"""Test lại 15/11, tester API (P-1..P-6): lỗi kiểm tra request trả 422 tiếng Việt, không bao giờ 500.

- P-1: NaN, Infinity, 1e400 trong body từng làm handler 422 mặc định chép giá trị không ghi được ra JSON → 500.
- P-2: /api/snap so khoảng cách đã làm tròn nên báo ok ở ~150,003 m trong khi /api/route từ chối.
- P-3: thông báo "cách 150 m, quá ngưỡng 150 m".
- P-4: lat = true bị đổi thành 1.0.
- P-5: lỗi Pydantic tiếng Anh, tiền tố "Value error, ".
- P-6: blocked_edge_ids không giới hạn độ dài.
"""

from __future__ import annotations

import math

from fastapi.testclient import TestClient
import pytest

from app.api.schemas import MAX_BLOCKED
from app.graph.geo import haversine_m
from app.main import app
from app.services.routing import SNAP_MAX_M
from mini_cases import load_mini

S = {"lat": 10.77251, "lon": 106.69801}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


def _raw(client, path: str, body: str):
    return client.post(path, content=body, headers={"content-type": "application/json"})


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_non_finite_coordinate_is_422_not_500(client, bad):
    body = f'{{"source": {{"lat": {bad}, "lon": 106.69801}}, "target": {{"lat": 10.7725, "lon": 106.698}}}}'
    r = _raw(client, "/api/route", body)
    assert r.status_code == 422, r.text
    msg = r.json()["detail"][0]["msg"]
    assert msg.startswith("source.lat: ") and "hữu hạn" in msg


def test_non_finite_trace_limit_is_422(client):
    body = '{"source": {"lat": 10.77251, "lon": 106.69801}, "target": {"lat": 10.7725, "lon": 106.698}, "trace_limit": NaN}'
    r = _raw(client, "/api/route", body)
    assert r.status_code == 422, r.text
    assert r.json()["detail"][0]["msg"] == "trace_limit: phải là số hữu hạn"


def test_bool_coordinate_rejected(client):
    r = client.post("/api/route", json={"source": {"lat": True, "lon": 106.69801}, "target": S})
    assert r.status_code == 422, r.text
    assert "true/false" in r.json()["detail"][0]["msg"]


def test_messages_are_vietnamese_with_field_and_no_prefix(client):
    r = client.post("/api/route", json={"source": S})
    assert r.status_code == 422
    msgs = [d["msg"] for d in r.json()["detail"]]
    assert "target: thiếu trường bắt buộc" in msgs
    r = client.post("/api/route", json={"source": S, "target": S, "algorithms": ["bfs"]})
    msg = r.json()["detail"][0]["msg"]
    assert msg.startswith("algorithms: thuật toán không hỗ trợ") and "Value error" not in msg
    r = client.get("/api/snap", params={"lat": "abc", "lon": 106.7})
    assert r.status_code == 422 and r.json()["detail"][0]["msg"] == "lat: phải là số"
    r = client.post("/api/tour", json={"depot": S, "stops": []})
    assert r.json()["detail"][0]["msg"] == "stops: cần ít nhất 1 phần tử"


def test_blocked_list_is_capped(client):
    r = client.post("/api/route", json={"source": S, "target": S, "blocked_edge_ids": [0] * (MAX_BLOCKED + 1)})
    assert r.status_code == 422
    assert r.json()["detail"][0]["msg"] == f"blocked_edge_ids: tối đa {MAX_BLOCKED} phần tử"


def _point_just_over_threshold() -> dict[str, float]:
    """Điểm cách node gần nhất (trong SCC) hơn ngưỡng chưa tới 5 mm: rời một node theo hướng bắc, chia đôi."""
    graph, meta = load_mini()
    nodes = [i for i in range(len(graph.node_lat)) if meta.node_in_scc[i]]

    def nearest(lat: float, lon: float) -> float:
        return min(haversine_m(lat, lon, graph.node_lat[i], graph.node_lon[i]) for i in nodes)

    lat0, lon0 = graph.node_lat[nodes[0]], graph.node_lon[nodes[0]]
    lo, hi = 0.0, 0.01        # độ vĩ: lo trong ngưỡng, hi chắc chắn ngoài ngưỡng
    assert nearest(lat0 + hi, lon0) > SNAP_MAX_M
    for _ in range(80):
        mid = (lo + hi) / 2
        if nearest(lat0 + mid, lon0) > SNAP_MAX_M:
            hi = mid
        else:
            lo = mid
    d = nearest(lat0 + hi, lon0)
    assert SNAP_MAX_M < d < SNAP_MAX_M + 0.005 and round(d, 2) == SNAP_MAX_M
    return {"lat": lat0 + hi, "lon": lon0}


def test_snap_ok_matches_route_at_threshold(client):
    p = _point_just_over_threshold()
    snap = client.get("/api/snap", params=p).json()
    assert snap["ok"] is False                    # trước đây True vì so 150,00 ≤ 150
    r = client.post("/api/route", json={"source": p, "target": S})
    assert r.status_code == 422
    msg = r.json()["detail"]
    assert "hơn 150 m, quá ngưỡng 150 m" in msg and "cách mạng đường 150 m" not in msg
    assert not math.isnan(snap["snap_distance_m"])
