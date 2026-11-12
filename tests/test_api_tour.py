"""T72: ma trận chi phí từ đồ thị và /api/tour (docs/TOPIC.md mục 10, 15.3–15.4, 17.3).

Đáp án trên mini.json (10 m/s): S→A 40 s, A→T 40 s, T→B 50 s, B→S 50 s, S→B 50 s; C và D không
có cạnh ra nên không quay về kho được. Tour S→A→T→B→S = 180 s là tối ưu trong cả 6 hoán vị;
thứ tự nhập B, A, T cho 50 + 90 + 40 + 100 = 280 s.
"""

from __future__ import annotations

import math

from fastapi.testclient import TestClient
import pytest

from app.algorithms.dijkstra import dijkstra, dijkstra_many
from app.algorithms.tour import HELD_KARP_MAX_POINTS
from app.graph.scenario import baseline_snapshot, build_snapshot, load_scenarios
from app.main import app
from mini_cases import MINI, edge_id, load_mini

LON_A = 106.7016577
P = {
    "S": {"lat": 10.77251, "lon": 106.69801},
    "A": {"lat": 10.77251, "lon": LON_A},
    "T": {"lat": 10.77251, "lon": 106.70532},
    "B": {"lat": 10.77519, "lon": LON_A},
    "C": {"lat": 10.77251, "lon": 106.69526},
}


def stop(name):
    return {"id": name.lower(), **P[name]}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def mini():
    return load_mini()


def tour(client, names, **kw):
    body = {"depot": P["S"], "stops": [stop(n) for n in names]}
    body.update(kw)
    return client.post("/api/tour", json=body)


# --- R1: Dijkstra một nguồn tới nhiều đích ---

def test_dijkstra_many_matches_single_target(mini):
    graph, _ = mini
    snap = baseline_snapshot(graph)
    n = len(graph.node_lat)
    for s in range(n):
        dist, _ = dijkstra_many(graph, snap, s, list(range(n)))
        for t in range(n):
            want = dijkstra(graph, snap, s, t).cost_s
            assert dist[t] == (pytest.approx(want) if want is not None else math.inf), (s, t)


# --- R3, R4: ba phương án, chi phí = tổng các cạnh đã dựng ---

def check_closed_route(graph, weights, cand, depot):
    edges = cand["edge_ids"]
    assert graph.edge_u[edges[0]] == depot and graph.edge_v[edges[-1]] == depot
    for e1, e2 in zip(edges, edges[1:]):
        assert graph.edge_v[e1] == graph.edge_u[e2]      # nối tiếp, đúng chiều
    assert cand["cost_s"] == pytest.approx(sum(weights[e] for e in edges))
    assert cand["distance_m"] == pytest.approx(sum(graph.edge_length_m[e] for e in edges))


def test_tour_returns_three_candidates_with_exact_costs(client, mini):
    graph, _ = mini
    r = tour(client, ["B", "A", "T"]).json()
    assert r["status"] == "ok"
    c = r["candidates"]
    assert set(c) == {"input", "nearest_neighbor", "nearest_neighbor_2opt"}
    assert c["input"]["stop_order"] == ["b", "a", "t"]
    assert c["input"]["cost_s"] == pytest.approx(280.0)
    assert c["nearest_neighbor"]["stop_order"] == ["a", "t", "b"]
    assert c["nearest_neighbor"]["cost_s"] == pytest.approx(180.0)
    assert c["nearest_neighbor"]["improvement_pct"] == pytest.approx(100 * 100 / 280)
    assert r["chosen"] == "nearest_neighbor"
    weights = baseline_snapshot(graph).weights
    for cand in c.values():
        check_closed_route(graph, weights, cand, depot=0)
    assert r["candidates"]["input"]["geometry"]["coordinates"][0] == [graph.node_lon[0], graph.node_lat[0]]


def test_input_order_kept_when_already_best(client):
    r = tour(client, ["A", "T", "B"]).json()
    assert r["chosen"] == "input" and r["candidates"]["input"]["improvement_pct"] == 0


def test_include_optimal_reports_gap(client):
    r = tour(client, ["B", "A", "T"], include_optimal=True).json()
    assert r["optimal"]["cost_s"] == pytest.approx(180.0)
    assert r["optimal"]["gap_pct"] == pytest.approx(0.0)    # gap của phương án được chọn


def test_single_stop(client):
    r = tour(client, ["A"]).json()
    assert r["candidates"]["input"]["stop_order"] == ["a"]
    assert r["candidates"]["input"]["cost_s"] == pytest.approx(40 + 40 + 100)   # S→A→T→B→S


# --- R2: chặng không hữu hạn ---

def test_unreachable_stop_gives_infeasible(client):
    r = tour(client, ["A", "C"]).json()
    assert r["status"] == "infeasible_under_model"
    assert r["candidates"] == {} and r["chosen"] is None
    assert {"from_id": "c", "to_id": "depot"} in r["unreachable"]


# --- R5: kịch bản, đóng đường, snap ---

def test_scenario_and_blocked_edges_use_new_snapshot(client, mini):
    graph, meta = mini
    scen = load_scenarios("tests/fixtures/scenarios_mini.json")["un-tac-tam-a"]
    r = tour(client, ["B", "A", "T"], scenario_id="un-tac-tam-a").json()
    weights = build_snapshot(graph, meta, scen).weights
    for cand in r["candidates"].values():
        check_closed_route(graph, weights, cand, depot=0)
    assert r["candidates"]["nearest_neighbor"]["cost_s"] > 180.0
    blocked = tour(client, ["A", "T", "B"], blocked_edge_ids=[edge_id(graph, meta, "A->T")]).json()
    assert blocked["status"] == "infeasible_under_model"      # A chỉ có cạnh ra A→T


def test_duplicate_points_rejected(client):
    res = client.post("/api/tour", json={"depot": P["S"], "stops": [stop("A"), {"id": "a2", **P["A"]}]})
    assert res.status_code == 422
    assert "trùng" in res.json()["detail"]


def test_far_stop_names_the_stop(client):
    res = client.post("/api/tour", json={"depot": P["S"], "stops": [{"id": "xa", "lat": 10.79, "lon": 106.698}]})
    assert res.status_code == 422
    assert "xa" in res.json()["detail"] and "150" in res.json()["detail"]


def test_stop_count_limits(client):
    assert client.post("/api/tour", json={"depot": P["S"], "stops": []}).status_code == 422
    too_many = client.post("/api/tour", json={"depot": P["S"], "stops": [{"id": f"s{i}", **P["A"]} for i in range(15)]})
    assert too_many.status_code == 422 and too_many.json()["detail"][0]["type"] == "too_long"
    # 14 điểm qua được giới hạn số lượng; ở mini.json chúng trùng node nên mới bị 422 vì trùng.
    fourteen = client.post("/api/tour", json={"depot": P["S"], "stops": [{"id": f"s{i}", **P["A"]} for i in range(14)]})
    assert fourteen.status_code == 422 and "trùng" in fourteen.json()["detail"]


def test_optimal_limited_by_held_karp_size(client):
    over = [{"id": f"s{i}", **P["A"]} for i in range(HELD_KARP_MAX_POINTS)]      # + kho = vượt 1 điểm
    res = client.post("/api/tour", json={"depot": P["S"], "stops": over, "include_optimal": True})
    assert res.status_code == 422 and "Held–Karp" in res.json()["detail"]
    at_limit = over[:HELD_KARP_MAX_POINTS - 1]                                   # vừa đúng giới hạn
    res = client.post("/api/tour", json={"depot": P["S"], "stops": at_limit, "include_optimal": True})
    assert res.status_code == 422 and "trùng" in res.json()["detail"]           # qua giới hạn Held–Karp


def test_open_tour_not_supported(client):
    res = tour(client, ["A"], return_to_depot=False)
    assert res.status_code == 422


@pytest.mark.parametrize("path", ["/api/route", "/api/tour"])
def test_boolean_is_not_an_edge_id(client, path):
    body = ({"source": P["S"], "target": P["T"]} if path == "/api/route"
            else {"depot": P["S"], "stops": [stop("A")]})
    assert client.post(path, json={**body, "blocked_edge_ids": [False]}).status_code == 422


@pytest.mark.parametrize("path", ["/api/route", "/api/tour"])
def test_empty_scenario_id_rejected(client, path):
    body = ({"source": P["S"], "target": P["T"]} if path == "/api/route"
            else {"depot": P["S"], "stops": [stop("A")]})
    res = client.post(path, json={**body, "scenario_id": ""})
    assert res.status_code == 422
