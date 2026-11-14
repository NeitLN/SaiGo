"""Review UI 14/11 (QA-3): `blocked_edges` trong /api/route và /api/tour.

Case demo đóng sẵn cạnh bằng id; UI chỉ có id nên trước đây không vẽ được đoạn đóng, người xem không thấy
vì sao "không còn đường". Response trả lại hình học của từng cạnh đóng trong request, đúng thứ tự gửi lên,
bỏ id trùng; có cả khi không có đường và khi tour không khả thi.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.routing import edge_coords
from mini_cases import edge_id, load_mini

S = {"lat": 10.77251, "lon": 106.69801}
T = {"lat": 10.77251, "lon": 106.70532}
A = {"lat": 10.77251, "lon": 106.7016577}
B = {"lat": 10.77519, "lon": 106.7016577}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def mini():
    return load_mini()


def route(client, **kw):
    res = client.post("/api/route", json={"source": S, "target": T, "algorithms": ["dijkstra", "astar"], **kw})
    assert res.status_code == 200, res.text
    return res.json()


def tour(client, **kw):
    body = {"depot": S, "stops": [{"id": "a", **A}, {"id": "t", **T}, {"id": "b", **B}], **kw}
    res = client.post("/api/tour", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_route_without_blocked_edges_returns_empty_list(client):
    assert route(client)["blocked_edges"] == []


def test_route_echoes_blocked_edges_in_order_without_duplicates(client, mini):
    graph, meta = mini
    a_t, s_b = edge_id(graph, meta, "A->T"), edge_id(graph, meta, "S->B")
    r = route(client, blocked_edge_ids=[a_t, s_b, a_t])
    assert [b["edge_id"] for b in r["blocked_edges"]] == [a_t, s_b]
    for b in r["blocked_edges"]:
        assert b["geometry"] == edge_coords(graph, meta, b["edge_id"])
        assert len(b["geometry"]) >= 2


def test_route_geometry_of_blocked_edge_matches_route_edge_geometry(client):
    """Đoạn người dùng vừa bấm đóng phải được vẽ đúng chỗ nét tuyến cũ (cùng nguồn hình học)."""
    first = route(client)["results"]["dijkstra"]
    e, geom = first["edge_ids"][0], first["edge_geometries"][0]
    r = route(client, blocked_edge_ids=[e])
    assert r["blocked_edges"] == [{"edge_id": e, "geometry": geom}]


def test_route_no_path_still_returns_blocked_edges(client, mini):
    graph, meta = mini
    blocked = [edge_id(graph, meta, "A->T"), edge_id(graph, meta, "B->T")]   # mọi cạnh vào T
    r = route(client, blocked_edge_ids=blocked)
    assert r["results"]["dijkstra"]["status"] == "no_path"
    assert [b["edge_id"] for b in r["blocked_edges"]] == blocked


def test_tour_ok_and_infeasible_both_return_blocked_edges(client, mini):
    graph, meta = mini
    assert tour(client)["blocked_edges"] == []
    s_b = edge_id(graph, meta, "S->B")
    ok = tour(client, blocked_edge_ids=[s_b])
    assert ok["status"] == "ok"
    assert ok["blocked_edges"] == [{"edge_id": s_b, "geometry": edge_coords(graph, meta, s_b)}]
    a_t = edge_id(graph, meta, "A->T")                                       # A chỉ có cạnh ra A→T
    bad = tour(client, blocked_edge_ids=[a_t])
    assert bad["status"] == "infeasible_under_model"
    assert [b["edge_id"] for b in bad["blocked_edges"]] == [a_t]
