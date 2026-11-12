"""T51: /api/route đầy đủ (kịch bản, đóng đường, snap 150 m, cạnh đối) và /api/dataset.

Đáp án trên mini.json lấy từ bảng tính tay của Bảo (tests/fixtures/mini_expected.json, T03).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.algorithms import heuristics
from app.main import app
from mini_cases import edge_id, load_mini

NEAR_S = {"lat": 10.77251, "lon": 106.69801}
NEAR_T = {"lat": 10.77252, "lon": 106.70532}
FAR = {"lat": 10.78250, "lon": 106.69801}   # cách S khoảng 1,1 km về phía bắc


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def mini():
    return load_mini()


def post(client, **kw):
    body = {"source": NEAR_S, "target": NEAR_T, "algorithms": ["dijkstra", "astar"]}
    body.update(kw)
    return client.post("/api/route", json=body)


# --- R5: /api/dataset ---

def test_dataset_lists_scenarios(client):
    res = client.get("/api/dataset")
    assert res.status_code == 200
    d = res.json()
    assert d["dataset_id"] == "mini"
    assert (d["node_count"], d["edge_count"]) == (6, 8)
    assert [s["id"] for s in d["scenarios"]] == ["baseline", "un-tac-tam-a"]
    rule = d["scenarios"][1]["rules"][0]
    assert rule["zone"] == {"type": "circle", "lat": 10.7725, "lon": 106.7016577, "radius_m": 220.0}
    assert rule["alpha"] == 2.0 and rule["highway"] is None


# --- R2: kịch bản ùn tắc ---

def test_scenario_changes_route(client, mini):
    graph, meta = mini
    res = post(client, scenario_id="un-tac-tam-a")
    assert res.status_code == 200
    r = res.json()
    for algo, expanded in (("dijkstra", 5), ("astar", 2)):
        assert r["results"][algo]["cost_s"] == pytest.approx(100.0)
        assert r["results"][algo]["edge_ids"] == [edge_id(graph, meta, "S->B"), edge_id(graph, meta, "B->T")]
        assert r["results"][algo]["expanded"] == expanded
    assert r["costs_match"] is True
    assert r["snapshot_id"] != post(client).json()["snapshot_id"]


def test_unknown_scenario_returns_422(client):
    res = post(client, scenario_id="khong-co")
    assert res.status_code == 422
    assert "kịch bản" in res.json()["detail"]


def test_null_scenario_means_baseline(client):
    assert post(client, scenario_id=None).json()["results"]["dijkstra"]["cost_s"] == pytest.approx(80.0)


# --- R3: đóng đường ---

def test_blocked_edge_reroutes(client, mini):
    graph, meta = mini
    a_t = edge_id(graph, meta, "A->T")
    r = post(client, blocked_edge_ids=[a_t]).json()
    for algo in ("dijkstra", "astar"):
        assert r["results"][algo]["cost_s"] == pytest.approx(100.0)
        assert a_t not in r["results"][algo]["edge_ids"]


def test_blocking_every_entry_gives_no_path(client, mini):
    graph, meta = mini
    r = post(client, blocked_edge_ids=[edge_id(graph, meta, "A->T"), edge_id(graph, meta, "B->T")]).json()
    for algo in ("dijkstra", "astar"):
        res = r["results"][algo]
        assert res["status"] == "no_path" and res["cost_s"] is None
        assert res["geometry"]["coordinates"] == []      # không vẽ đường thẳng
    assert r["costs_match"] is True


def test_invalid_blocked_edge_returns_422(client):
    res = post(client, blocked_edge_ids=[99])
    assert res.status_code == 422
    assert "cạnh" in res.json()["detail"]


# --- R1: snap có ngưỡng 150 m ---

def test_point_too_far_returns_422(client):
    res = post(client, source=FAR)
    assert res.status_code == 422
    assert "150" in res.json()["detail"] and "Điểm đi" in res.json()["detail"]


def test_target_too_far_names_target(client):
    res = post(client, target=FAR)
    assert res.status_code == 422
    assert "Điểm đến" in res.json()["detail"]


# --- R4: cạnh đối của từng cạnh trên tuyến ---

def test_edge_twin_ids_align_with_route(client, mini):
    graph, meta = mini
    back = client.post("/api/route", json={"source": NEAR_T, "target": NEAR_S}).json()["results"]["dijkstra"]
    assert back["edge_ids"] == [edge_id(graph, meta, "T->B"), edge_id(graph, meta, "B->S")]
    assert back["edge_twin_ids"] == [edge_id(graph, meta, "B->T"), edge_id(graph, meta, "S->B")]
    forward = post(client).json()["results"]["dijkstra"]
    assert forward["edge_twin_ids"] == [None, None]    # S→A, A→T là đường một chiều


# --- R6: tính sẵn lúc khởi động ---

def test_startup_precomputes_geo_scale_and_twins(client):
    graph = client.app.state.graph
    assert heuristics._scale_cache[id(graph)][0] is graph
    assert len(client.app.state.twins) == len(graph.edge_u)


def test_heuristic_setup_counts_toward_astar_time(client, monkeypatch):
    # EXPERIMENT_PLAN 3.1 bước 5: thời gian tính heuristic được tính vào A* (cùng định nghĩa với benchmark).
    import time
    real = heuristics.make_geo_heuristic

    def slow(*a, **k):
        time.sleep(0.05)
        return real(*a, **k)

    monkeypatch.setattr("app.services.routing.make_geo_heuristic", slow)
    r = post(client, algorithms=["astar"]).json()
    assert r["results"]["astar"]["runtime_ms"] >= 50


def test_geo_scale_cached_before_first_request(client, monkeypatch):
    # geo_scale duyệt mọi cạnh; phải được tính lúc khởi động, không rơi vào request (review #67, #73).
    seen = []
    real = heuristics.geo_scale

    def spy(graph):
        seen.append(id(graph) in heuristics._scale_cache)
        return real(graph)

    monkeypatch.setattr(heuristics, "geo_scale", spy)
    post(client, algorithms=["astar"])
    assert seen == [True]


def test_empty_scenario_id_rejected(client):
    assert post(client, scenario_id="").status_code == 422      # chỉ null mới là baseline


def test_boolean_is_not_an_edge_id(client):
    assert post(client, blocked_edge_ids=[False]).status_code == 422   # không bị ép thành cạnh 0
