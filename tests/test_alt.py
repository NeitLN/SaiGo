"""O16: ALT (A* + landmark) — chi phí khớp Dijkstra, heuristic admissible/consistent, API nhận "alt".

Đồ thị: `tests/fixtures/mini.json` (mọi cặp + 200 cặp ngẫu nhiên seed cố định), đồ thị demo
`data/processed/hcm-benthanh-r2000-20261024.json` (bỏ qua khi chưa build) và một đồ thị ngẫu nhiên
có cạnh song song + node không tới được. NetworkX chỉ dùng ở đây để đối chứng khoảng cách thật.
"""

from __future__ import annotations

import math
from pathlib import Path
import random

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from app.algorithms.alt import (DEFAULT_LANDMARKS, LANDMARK_SEED, alt, build_alt_index,
                                choose_landmarks, ensure_alt_compatible, get_alt_index,
                                make_alt_heuristic)
from app.algorithms.dijkstra import dijkstra
from app.graph.model import Graph, GraphMeta, load_graph, node_by_name
from app.graph.scenario import (baseline_snapshot, build_snapshot, load_scenarios,
                                make_snapshot)
from app.main import app
from helpers.random_graph import make_random_graph, to_networkx
from mini_cases import edge_id, load_mini

ROOT = Path(__file__).resolve().parent.parent
SCENARIO_FILE = ROOT / "data" / "config" / "scenarios.json"
DEMO_FILE = ROOT / "data" / "processed" / "hcm-benthanh-r2000-20261024.json"
MINI_SCENARIO_FILE = ROOT / "tests" / "fixtures" / "scenarios_mini.json"

SEED = 20261113
N_PAIRS = 200          # số cặp ngẫu nhiên mỗi kịch bản (card O16: ≥ 200)
TOL = 1e-6

NEAR_S = {"lat": 10.77251, "lon": 106.69801}
NEAR_T = {"lat": 10.77252, "lon": 106.70532}


# --- Fixture ---

@pytest.fixture(scope="module")
def mini() -> tuple[Graph, GraphMeta]:
    return load_mini()


@pytest.fixture(scope="module")
def mini_index(mini) -> object:
    graph, meta = mini
    return build_alt_index(graph, meta)


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

def mini_pairs(graph: Graph, meta: GraphMeta) -> list[tuple[int, int]]:
    """Mọi cặp có thứ tự trên mini (6 node) + 200 cặp ngẫu nhiên seed cố định."""
    n = len(graph.node_lat)
    rng = random.Random(SEED)
    pairs = [(s, t) for s in range(n) for t in range(n)]
    pairs += [(rng.randrange(n), rng.randrange(n)) for _ in range(N_PAIRS)]
    return pairs


def assert_same_as_dijkstra(graph, snap, index, pairs) -> None:
    for s, t in pairs:
        want = dijkstra(graph, snap, s, t)
        got = alt(graph, snap, s, t, index)
        assert got.status == want.status, (s, t, got.status, want.status)
        if want.cost_s is None:
            assert got.cost_s is None, (s, t)
            assert got.edge_ids == [] and got.node_ids == []
        else:
            assert got.cost_s == pytest.approx(want.cost_s, rel=TOL, abs=TOL), (s, t)
            # heuristic admissible + consistent thì không bao giờ mở rộng nhiều hơn Dijkstra
            assert got.expanded <= want.expanded, (s, t)


def snapshots_mini(graph: Graph, meta: GraphMeta) -> list:
    """Baseline, mọi kịch bản trong scenarios_mini.json, và một tổ hợp đóng đường."""
    scenarios = load_scenarios(MINI_SCENARIO_FILE)
    snaps = [build_snapshot(graph, meta, scenario) for scenario in scenarios.values()]
    closed = frozenset({edge_id(graph, meta, "A->T"), edge_id(graph, meta, "B->T")})
    snaps.append(make_snapshot(graph, graph.edge_base_time_s, closed, scenario_id="closed"))
    return snaps


# --- Chi phí khớp Dijkstra ---

def test_alt_matches_dijkstra_every_pair_on_mini(mini, mini_index):
    graph, meta = mini
    pairs = mini_pairs(graph, meta)
    assert len(pairs) > N_PAIRS
    assert_same_as_dijkstra(graph, baseline_snapshot(graph), mini_index, pairs)


def test_alt_matches_dijkstra_on_every_mini_scenario_and_closure(mini, mini_index):
    graph, meta = mini
    pairs = mini_pairs(graph, meta)
    for snap in snapshots_mini(graph, meta):
        assert_same_as_dijkstra(graph, snap, mini_index, pairs)


def test_alt_matches_dijkstra_on_demo_every_scenario_and_closure(demo):
    """Đồ thị demo: baseline + mọi kịch bản trong data/config/scenarios.json + đóng đường."""
    graph, meta = demo
    index = get_alt_index(graph, meta)
    scenarios = load_scenarios(SCENARIO_FILE)

    nodes = [v for v in range(len(graph.node_lat)) if meta.node_in_scc[v]]
    rng = random.Random(SEED)
    pairs = [(rng.choice(nodes), rng.choice(nodes)) for _ in range(N_PAIRS)]

    blocked = frozenset(random.Random(SEED + 1).sample(range(len(graph.edge_u)), 5))
    snaps = [build_snapshot(graph, meta, scenario) for scenario in scenarios.values()]
    snaps.append(build_snapshot(graph, meta, scenarios["peak-center"], blocked))

    for snap in snaps:
        for s, t in pairs:
            want = dijkstra(graph, snap, s, t)
            got = alt(graph, snap, s, t, index)
            assert got.status == want.status, (snap.scenario_id, s, t)
            if want.cost_s is None:
                assert got.cost_s is None
            else:
                assert got.cost_s == pytest.approx(want.cost_s, rel=TOL, abs=TOL), \
                    (snap.scenario_id, s, t)
                assert got.expanded <= want.expanded, (snap.scenario_id, s, t)


def test_alt_matches_dijkstra_on_random_graph_with_parallel_edges():
    graph, meta = make_random_graph(seed=7, n_nodes=50, n_edges=150)
    index = build_alt_index(graph, meta)
    base = baseline_snapshot(graph)
    rng = random.Random(SEED)
    pairs = [(rng.randrange(50), rng.randrange(50)) for _ in range(N_PAIRS)]
    assert_same_as_dijkstra(graph, base, index, pairs)


def test_no_path_is_reported_like_dijkstra(mini, mini_index):
    graph, meta = mini
    blocked = frozenset({edge_id(graph, meta, "A->T"), edge_id(graph, meta, "B->T")})
    snap = make_snapshot(graph, graph.edge_base_time_s, blocked)
    s, t = node_by_name(meta, "S"), node_by_name(meta, "T")
    d = dijkstra(graph, snap, s, t)
    r = alt(graph, snap, s, t, mini_index)
    assert d.status == r.status == "no_path"
    assert r.cost_s is None and r.edge_ids == [] and r.node_ids == []
    assert r.expanded <= d.expanded


def test_source_equals_target(mini, mini_index):
    graph, meta = mini
    s = node_by_name(meta, "A")
    r = alt(graph, baseline_snapshot(graph), s, s, mini_index)
    assert r.status == "ok" and r.cost_s == 0.0 and r.expanded == 0 and r.node_ids == [s]


# --- Heuristic: admissible + consistent, đối chứng NetworkX ---

def test_alt_heuristic_never_exceeds_true_distance_on_mini(mini, mini_index):
    graph, meta = mini
    n = len(graph.node_lat)
    for snap in snapshots_mini(graph, meta):
        net = to_networkx(graph, snap)
        for t in range(n):
            h = make_alt_heuristic(mini_index, t)
            assert h(t) == 0.0
            for v in range(n):
                try:
                    true = nx.dijkstra_path_length(net, v, t, weight="weight")
                except nx.NetworkXNoPath:
                    continue
                assert h(v) <= true + 1e-9, (snap.scenario_id, v, t, h(v), true)


def test_alt_heuristic_is_consistent_on_every_snapshot_edge(mini, mini_index):
    graph, meta = mini
    n = len(graph.node_lat)
    for snap in snapshots_mini(graph, meta):
        for t in range(n):
            h = make_alt_heuristic(mini_index, t)
            for e, w in enumerate(snap.weights):
                if w == math.inf:
                    continue
                assert h(graph.edge_u[e]) <= w + h(graph.edge_v[e]) + 1e-9, (e, t)


def test_alt_heuristic_does_not_exceed_networkx_on_demo_sample(demo):
    graph, meta = demo
    index = get_alt_index(graph, meta)
    scenarios = load_scenarios(SCENARIO_FILE)
    nodes = [v for v in range(len(graph.node_lat)) if meta.node_in_scc[v]]
    rng = random.Random(SEED)
    for scenario_id in ("baseline", "peak-center"):
        snap = build_snapshot(graph, meta, scenarios[scenario_id])
        net = to_networkx(graph, snap)
        for _ in range(25):
            s, t = rng.choice(nodes), rng.choice(nodes)
            h = make_alt_heuristic(index, t)
            assert h(s) <= nx.dijkstra_path_length(net, s, t, weight="weight") + 1e-9


# --- Index: chọn landmark, cache, bộ nhớ, hợp lệ với snapshot ---

def test_choose_landmarks_honours_k_scc_and_seed(demo, mini):
    graph, meta = demo
    chosen = choose_landmarks(graph, meta, DEFAULT_LANDMARKS, LANDMARK_SEED, graph.edge_base_time_s)
    assert len(chosen) == DEFAULT_LANDMARKS
    assert len(set(chosen)) == DEFAULT_LANDMARKS
    assert all(meta.node_in_scc[v] for v in chosen)
    assert chosen == choose_landmarks(graph, meta, DEFAULT_LANDMARKS, LANDMARK_SEED,
                                      graph.edge_base_time_s)

    small, small_meta = mini
    # mini chỉ có 4 node có cạnh ra (C, D là node cụt) nên không thể chọn nhiều hơn 4 landmark
    assert len(choose_landmarks(small, small_meta, 99, LANDMARK_SEED, small.edge_base_time_s)) == 4


def test_index_cache_memory_and_preprocess_stats(mini):
    graph, meta = mini
    first = get_alt_index(graph, meta)
    assert get_alt_index(graph, meta) is first
    assert first.preprocess_ms >= 0.0
    assert first.k == len(first.landmarks) == len(set(first.landmarks))
    assert 0 < first.k <= min(DEFAULT_LANDMARKS, len(graph.node_lat))
    assert first.memory_bytes == 16 * len(graph.node_lat) * first.k


def test_rejects_snapshot_with_cheaper_edges(mini, mini_index):
    graph, _ = mini
    cheaper = [w * 0.5 for w in graph.edge_base_time_s]
    bad = make_snapshot(graph, cheaper, scenario_id="cheaper")
    with pytest.raises(ValueError, match="rẻ hơn chi phí cơ sở"):
        ensure_alt_compatible(graph, bad)
    with pytest.raises(ValueError, match="rẻ hơn chi phí cơ sở"):
        alt(graph, bad, 0, 2, mini_index)


def test_increased_cost_snapshot_is_accepted(mini, mini_index):
    graph, meta = mini
    scenario = load_scenarios(MINI_SCENARIO_FILE)["un-tac-tam-a"]
    snap = build_snapshot(graph, meta, scenario)
    ensure_alt_compatible(graph, snap)
    assert alt(graph, snap, node_by_name(meta, "S"), node_by_name(meta, "T"),
               mini_index).status == "ok"


# --- API ---

def test_api_accepts_dijkstra_astar_alt(client: TestClient):
    res = client.post("/api/route", json={
        "source": NEAR_S, "target": NEAR_T,
        "algorithms": ["dijkstra", "astar", "alt"],
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert set(data["results"]) == {"dijkstra", "astar", "alt"}
    assert data["costs_match"] is True
    assert data["warnings"] == []
    for algo in ("dijkstra", "astar", "alt"):
        assert data["results"][algo]["status"] == "ok"
        assert data["results"][algo]["cost_s"] == pytest.approx(80.0)
        assert data["results"][algo]["runtime_ms"] >= 0.0


def test_api_alt_matches_dijkstra_under_scenario_and_closure(client: TestClient):
    res = client.post("/api/route", json={
        "source": NEAR_S, "target": NEAR_T,
        "algorithms": ["dijkstra", "alt"],
        "scenario_id": "peak-ben-thanh",
    })
    assert res.status_code == 200, res.text
    data = res.json()
    d, a = data["results"]["dijkstra"], data["results"]["alt"]
    assert d["status"] == a["status"]
    assert a["cost_s"] == pytest.approx(d["cost_s"])
    assert data["warnings"] == []
    # costs_match vẫn chỉ là phép so Dijkstra–A*: thiếu A* thì để null như cũ
    assert data["costs_match"] is None


def test_api_rejects_unknown_algorithm(client: TestClient):
    res = client.post("/api/route", json={
        "source": NEAR_S, "target": NEAR_T, "algorithms": ["alt", "floyd_warshall"],
    })
    assert res.status_code == 422
    assert "floyd_warshall" in res.text
