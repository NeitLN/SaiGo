"""O19: Dijkstra hai chiều — chi phí khớp Dijkstra, đường liên tục, bộ đếm/trace, API nhận "bidijkstra".

Đồ thị: `tests/fixtures/mini.json` (mọi cặp + 200 cặp ngẫu nhiên seed cố định, baseline + mọi
kịch bản + đóng đường), đồ thị demo `data/processed/hcm-benthanh-r2000-20261024.json` (bỏ qua khi
chưa build) và một đồ thị ngẫu nhiên có cạnh song song + node không tới được.
"""

from __future__ import annotations

import math
from pathlib import Path
import random

import pytest
from fastapi.testclient import TestClient

from app.algorithms.bidijkstra import bidijkstra
from app.algorithms.dijkstra import dijkstra
from app.graph.model import Graph, GraphMeta, load_graph, node_by_name
from app.graph.scenario import (baseline_snapshot, build_snapshot, load_scenarios, make_snapshot)
from app.main import app
from helpers.random_graph import make_random_graph
from mini_cases import edge_id, load_mini

ROOT = Path(__file__).resolve().parent.parent
SCENARIO_FILE = ROOT / "data" / "config" / "scenarios.json"
DEMO_FILE = ROOT / "data" / "processed" / "hcm-benthanh-r2000-20261024.json"
MINI_SCENARIO_FILE = ROOT / "tests" / "fixtures" / "scenarios_mini.json"

SEED = 20261113
N_PAIRS = 200          # số cặp ngẫu nhiên mỗi kịch bản (card O19: ≥ 200)
TOL = 1e-9

NEAR_S = {"lat": 10.77251, "lon": 106.69801}
NEAR_T = {"lat": 10.77252, "lon": 106.70532}


# --- Fixture ---

@pytest.fixture(scope="module")
def mini() -> tuple[Graph, GraphMeta]:
    return load_mini()


@pytest.fixture(scope="module")
def demo() -> tuple[Graph, GraphMeta]:
    if not DEMO_FILE.exists():
        pytest.skip("chưa có data/processed/hcm-benthanh-r2000-20261024.json")
    return load_graph(DEMO_FILE)


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


# --- Helper ---

def mini_pairs(graph: Graph) -> list[tuple[int, int]]:
    """Mọi cặp có thứ tự trên mini (6 node) + 200 cặp ngẫu nhiên seed cố định."""
    n = len(graph.node_lat)
    rng = random.Random(SEED)
    pairs = [(s, t) for s in range(n) for t in range(n)]
    pairs += [(rng.randrange(n), rng.randrange(n)) for _ in range(N_PAIRS)]
    return pairs


def snapshots_mini(graph: Graph, meta: GraphMeta) -> list:
    """Baseline, mọi kịch bản trong scenarios_mini.json, và một tổ hợp đóng đường."""
    scenarios = load_scenarios(MINI_SCENARIO_FILE)
    snaps = [build_snapshot(graph, meta, scenario) for scenario in scenarios.values()]
    closed = frozenset({edge_id(graph, meta, "A->T"), edge_id(graph, meta, "B->T")})
    snaps.append(make_snapshot(graph, graph.edge_base_time_s, closed, scenario_id="closed"))
    return snaps


def assert_route_is_continuous(graph: Graph, snap, source: int, target: int, res) -> None:
    """Tuyến phải nối đuôi nhau từ source tới target và tổng trọng số đúng bằng `cost_s`."""
    assert res.status == "ok"
    assert res.node_ids[0] == source and res.node_ids[-1] == target
    assert len(res.node_ids) == len(res.edge_ids) + 1
    total = 0.0
    for i, e in enumerate(res.edge_ids):
        assert graph.edge_u[e] == res.node_ids[i], (i, e)
        assert graph.edge_v[e] == res.node_ids[i + 1], (i, e)
        assert snap.weights[e] < math.inf, e
        total += snap.weights[e]
    assert total == pytest.approx(res.cost_s, rel=TOL, abs=TOL)
    assert res.distance_m == pytest.approx(sum(graph.edge_length_m[e] for e in res.edge_ids))


def assert_same_as_dijkstra(graph: Graph, snap, pairs, *, check_route: bool = True) -> None:
    for source, target in pairs:
        want = dijkstra(graph, snap, source, target)
        got = bidijkstra(graph, snap, source, target)
        assert got.status == want.status, (snap.scenario_id, source, target)
        if want.cost_s is None:
            assert got.cost_s is None, (snap.scenario_id, source, target)
            assert got.edge_ids == [] and got.node_ids == []
        else:
            assert got.cost_s == pytest.approx(want.cost_s, rel=TOL, abs=TOL), \
                (snap.scenario_id, source, target)
            if check_route:
                assert_route_is_continuous(graph, snap, source, target, got)


# --- Chi phí khớp Dijkstra ---

def test_matches_dijkstra_every_pair_on_mini(mini):
    graph, _ = mini
    pairs = mini_pairs(graph)
    assert len(pairs) > N_PAIRS
    assert_same_as_dijkstra(graph, baseline_snapshot(graph), pairs)


def test_matches_dijkstra_on_every_mini_scenario_and_closure(mini):
    graph, meta = mini
    pairs = mini_pairs(graph)
    for snap in snapshots_mini(graph, meta):
        assert_same_as_dijkstra(graph, snap, pairs)


def test_matches_dijkstra_on_demo_every_scenario_and_closure(demo):
    """Đồ thị demo: baseline + mọi kịch bản trong data/config/scenarios.json + đóng đường."""
    graph, meta = demo
    scenarios = load_scenarios(SCENARIO_FILE)

    nodes = [v for v in range(len(graph.node_lat)) if meta.node_in_scc[v]]
    rng = random.Random(SEED)
    pairs = [(rng.choice(nodes), rng.choice(nodes)) for _ in range(N_PAIRS)]

    blocked = frozenset(random.Random(SEED + 1).sample(range(len(graph.edge_u)), 5))
    snaps = [build_snapshot(graph, meta, scenario) for scenario in scenarios.values()]
    snaps.append(build_snapshot(graph, meta, scenarios["peak-center"], blocked))

    for snap in snaps:
        assert_same_as_dijkstra(graph, snap, pairs)


def test_matches_dijkstra_on_random_graph_with_parallel_edges():
    graph, _ = make_random_graph(seed=7, n_nodes=50, n_edges=150)
    base = baseline_snapshot(graph)
    rng = random.Random(SEED)
    pairs = [(rng.randrange(50), rng.randrange(50)) for _ in range(N_PAIRS)]
    assert_same_as_dijkstra(graph, base, pairs)


def test_source_equals_target(mini):
    graph, meta = mini
    s = node_by_name(meta, "A")
    res = bidijkstra(graph, baseline_snapshot(graph), s, s)
    assert res.status == "ok"
    assert res.cost_s == 0.0 and res.distance_m == 0.0
    assert res.edge_ids == [] and res.node_ids == [s]
    assert res.expanded == res.unique_expanded == res.reopened == 0
    assert res.relaxations == res.pushes == res.max_frontier == 0
    assert res.trace == [] and res.trace_truncated is False


def test_no_path_is_reported_like_dijkstra(mini):
    graph, meta = mini
    blocked = frozenset({edge_id(graph, meta, "A->T"), edge_id(graph, meta, "B->T")})
    snap = make_snapshot(graph, graph.edge_base_time_s, blocked)
    s, t = node_by_name(meta, "S"), node_by_name(meta, "T")
    want = dijkstra(graph, snap, s, t)
    got = bidijkstra(graph, snap, s, t)
    assert want.status == got.status == "no_path"
    assert got.cost_s is None and got.distance_m is None
    assert got.edge_ids == [] and got.node_ids == []
    assert got.expanded > 0 and got.unique_expanded <= got.expanded
    assert got.reopened == 0


# --- Bộ đếm và trace ---

def test_trace_is_interleaved_in_expansion_order_and_honours_limit(mini):
    graph, meta = mini
    snap = baseline_snapshot(graph)
    s, t = node_by_name(meta, "S"), node_by_name(meta, "T")

    off = bidijkstra(graph, snap, s, t)              # trace_limit = 0: tắt trace
    assert off.trace == [] and off.trace_truncated is False

    full = bidijkstra(graph, snap, s, t, trace_limit=1000)
    assert len(full.trace) == full.expanded          # mọi lần mở rộng đều được ghi
    assert full.trace_truncated is False
    assert all(0 <= v < len(graph.node_lat) for v in full.trace)
    assert full.expanded > 0 and full.unique_expanded <= full.expanded
    assert full.reopened == 0
    assert full.pushes >= 2 and full.max_frontier >= 2 and full.relaxations >= 0

    short = bidijkstra(graph, snap, s, t, trace_limit=3)
    assert short.trace == full.trace[:3]
    assert short.trace_truncated is True


def test_counters_are_consistent_with_route(mini):
    """Tuyến trả về đúng chi phí; expanded/unique/reopened cùng nghĩa với Dijkstra một chiều."""
    graph, meta = mini
    snap = baseline_snapshot(graph)
    s, t = node_by_name(meta, "S"), node_by_name(meta, "T")
    res = bidijkstra(graph, snap, s, t)
    assert res.status == "ok"
    assert res.expanded > 0
    assert res.unique_expanded <= res.expanded
    assert res.reopened == 0
    assert res.pushes > res.expanded              # mỗi node mở rộng push ít nhất một lần + 2 entry đầu
    assert res.max_frontier >= 2


# --- API ---

def test_api_accepts_dijkstra_astar_alt_bidijkstra(client: TestClient):
    res = client.post("/api/route", json={
        "source": NEAR_S, "target": NEAR_T,
        "algorithms": ["dijkstra", "astar", "alt", "bidijkstra"],
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert set(data["results"]) == {"dijkstra", "astar", "alt", "bidijkstra"}
    assert data["costs_match"] is True
    assert data["warnings"] == []
    for algo in ("dijkstra", "astar", "alt", "bidijkstra"):
        result = data["results"][algo]
        assert result["status"] == "ok"
        assert result["cost_s"] == pytest.approx(80.0)
        assert result["runtime_ms"] >= 0.0
        assert result["expanded"] > 0
        assert result["edge_ids"] == [0, 4]


def test_api_bidijkstra_matches_dijkstra_under_scenario_and_closure(client: TestClient):
    res = client.post("/api/route", json={
        "source": NEAR_S, "target": NEAR_T,
        "algorithms": ["dijkstra", "bidijkstra"],
        "scenario_id": "peak-ben-thanh",
        "blocked_edge_ids": [4],
    })
    assert res.status_code == 200, res.text
    data = res.json()
    d, b = data["results"]["dijkstra"], data["results"]["bidijkstra"]
    assert d["status"] == b["status"]
    assert b["cost_s"] == pytest.approx(d["cost_s"])
    assert b["edge_ids"] == d["edge_ids"]
    assert data["warnings"] == []
    # costs_match vẫn chỉ là phép so Dijkstra–A*: thiếu A* thì để null như cũ
    assert data["costs_match"] is None


def test_api_rejects_unknown_algorithm_still(client: TestClient):
    res = client.post("/api/route", json={
        "source": NEAR_S, "target": NEAR_T, "algorithms": ["bidijkstra", "floyd_warshall"],
    })
    assert res.status_code == 422
    assert "floyd_warshall" in res.text
