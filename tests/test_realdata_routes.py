"""Kiểm tra điều kiện heuristic và đối chứng Dijkstra/A* trên đồ thị thật với NetworkX (T33, issue #15).

Tiêu chuẩn: docs/TASKS.md mục T33 và docs/DATA_MODEL.md mục 5.1, 8.4:
- Tự động skip nếu chưa có data/processed/manifest.json hoặc file đồ thị;
- heuristic_report: c >= 0.999, n_violations == 0, v_max khớp manifest;
- 200 cặp ngẫu nhiên có seed (seed 42) trong thành phần liên thông mạnh SCC:
  + Luôn có đường (trong cùng SCC);
  + Chi phí Dijkstra và A* (make_geo_heuristic) khớp nx.dijkstra_path_length trên MultiDiGraph;
  + Sai số <= 1e-9 * max(1, cost);
  + Tuyến hợp lệ: nối tiếp liên tục, đúng chiều, tổng trọng số và quãng đường khớp;
  + reopened == 0 cho mọi truy vấn A*;
- Thử nghiệm kịch bản peak-center (50 cặp) nếu scenarios.json đã có kịch bản đó (chờ PR #88).
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import networkx as nx
import pytest

from app.algorithms.astar import astar
from app.algorithms.dijkstra import dijkstra
from app.algorithms.heuristics import heuristic_report, make_geo_heuristic
from app.algorithms.result import SearchResult
from app.graph.model import Graph, GraphMeta, load_graph
from app.graph.scenario import Snapshot, baseline_snapshot, build_snapshot, load_scenarios

from helpers.random_graph import to_networkx

pytestmark = pytest.mark.realdata

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "processed" / "manifest.json"
SCENARIOS_PATH = ROOT / "data" / "config" / "scenarios.json"


@pytest.fixture(scope="module")
def real_demo_graph() -> tuple[Graph, GraphMeta, dict]:
    """Nạp đồ thị thật vùng demo từ manifest.json; tự động skip nếu chưa có dữ liệu."""
    if not MANIFEST_PATH.exists():
        pytest.skip("chưa có data/processed/manifest.json (T31)")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    path = ROOT / manifest["file"]
    if not path.exists():
        pytest.skip(f"chưa có {manifest['file']}; cần dựng dữ liệu trước")
    graph, meta = load_graph(path)
    return graph, meta, manifest


def _verify_route(graph: Graph, snap: Snapshot, res: SearchResult, source: int, target: int) -> None:
    """Kiểm tra tính hợp lệ của tuyến: liên tục, đúng chiều, tổng trọng số và độ dài."""
    assert res.status == "ok"
    assert res.cost_s is not None
    assert res.distance_m is not None

    if source == target:
        assert res.cost_s == 0.0
        assert res.edge_ids == []
        assert res.node_ids == [source]
        assert res.distance_m == 0.0
        return

    assert len(res.edge_ids) >= 1
    assert len(res.node_ids) == len(res.edge_ids) + 1
    assert res.node_ids[0] == source
    assert res.node_ids[-1] == target
    assert graph.edge_u[res.edge_ids[0]] == source
    assert graph.edge_v[res.edge_ids[-1]] == target

    # Kiểm tra tính nối tiếp liên tục và đúng chiều
    for k in range(len(res.edge_ids) - 1):
        assert graph.edge_v[res.edge_ids[k]] == graph.edge_u[res.edge_ids[k + 1]]

    for k, e in enumerate(res.edge_ids):
        assert e not in snap.blocked
        assert not math.isinf(snap.weights[e])
        assert graph.edge_u[e] == res.node_ids[k]
        assert graph.edge_v[e] == res.node_ids[k + 1]

    # Kiểm tra tổng trọng số và quãng đường
    tol_cost = 1e-9 * max(1.0, res.cost_s)
    w_sum = sum(snap.weights[e] for e in res.edge_ids)
    assert abs(w_sum - res.cost_s) <= tol_cost

    tol_dist = 1e-9 * max(1.0, res.distance_m)
    d_sum = sum(graph.edge_length_m[e] for e in res.edge_ids)
    assert abs(d_sum - res.distance_m) <= tol_dist


def test_heuristic_report_real_data(real_demo_graph: tuple[Graph, GraphMeta, dict]) -> None:
    """Kiểm tra điều kiện heuristic trên đồ thị thật: c >= 0.999, không có vi phạm."""
    graph, meta, manifest = real_demo_graph
    rep = heuristic_report(graph)

    # Hệ số co giãn c >= 0.999 (DATA_MODEL mục 5.1)
    assert rep.c >= 0.999
    assert rep.c == pytest.approx(manifest["heuristic_c"])

    # Không có cạnh nào vi phạm điều kiện length < haversine - 1mm
    assert rep.n_violations == 0

    # Tốc độ lớn nhất v_max_mps khớp với v_max_kmh trong manifest
    expected_v_max_mps = manifest["v_max_kmh"] / 3.6
    assert rep.v_max_mps == pytest.approx(expected_v_max_mps)


def test_routes_200_pairs_oracle_networkx(real_demo_graph: tuple[Graph, GraphMeta, dict]) -> None:
    """Đối chứng 200 cặp truy vấn ngẫu nhiên trong SCC với NetworkX trên đồ thị thật."""
    graph, meta, _ = real_demo_graph
    snap = baseline_snapshot(graph)
    nx_g = to_networkx(graph, snap)

    scc_nodes = [i for i in range(len(graph.node_lat)) if meta.node_in_scc[i]]
    assert len(scc_nodes) >= 200, f"SCC cần có đủ node để sinh cặp, nhận {len(scc_nodes)}"

    rng = random.Random(42)
    pairs: list[tuple[int, int]] = []
    while len(pairs) < 200:
        s = rng.choice(scc_nodes)
        t = rng.choice(scc_nodes)
        if s != t:
            pairs.append((s, t))

    for s, t in pairs:
        res_d = dijkstra(graph, snap, s, t)
        h = make_geo_heuristic(graph, t)
        res_a = astar(graph, snap, s, t, h)
        nx_cost = nx.dijkstra_path_length(nx_g, s, t, weight="weight")

        # Trong SCC luôn luôn tìm thấy đường
        assert res_d.status == "ok"
        assert res_a.status == "ok"
        assert res_a.reopened == 0, f"A* bị mở lại node tại truy vấn ({s} -> {t}): reopened={res_a.reopened}"

        # Kiểm tra chi phí khớp tuyệt đối với NetworkX
        tol = 1e-9 * max(1.0, nx_cost)
        assert abs(res_d.cost_s - nx_cost) <= tol
        assert abs(res_a.cost_s - nx_cost) <= tol
        assert abs(res_a.cost_s - res_d.cost_s) <= tol

        # Kiểm tra tính hợp lệ hình học của tuyến
        _verify_route(graph, snap, res_d, s, t)
        _verify_route(graph, snap, res_a, s, t)


def test_routes_peak_center_scenario_if_available(real_demo_graph: tuple[Graph, GraphMeta, dict]) -> None:
    """Chạy đối chứng 50 cặp dưới kịch bản peak-center nếu đã có trong scenarios.json."""
    if not SCENARIOS_PATH.exists():
        pytest.skip("chưa có data/config/scenarios.json")

    scenarios = load_scenarios(SCENARIOS_PATH)
    if "peak-center" not in scenarios:
        pytest.skip("kịch bản 'peak-center' chưa có trong data/config/scenarios.json (chờ PR #88)")

    graph, meta, _ = real_demo_graph
    scenario = scenarios["peak-center"]
    snap = build_snapshot(graph, meta, scenario)
    nx_g = to_networkx(graph, snap)

    scc_nodes = [i for i in range(len(graph.node_lat)) if meta.node_in_scc[i]]
    rng = random.Random(42)
    pairs: list[tuple[int, int]] = []
    while len(pairs) < 50:
        s = rng.choice(scc_nodes)
        t = rng.choice(scc_nodes)
        if s != t:
            pairs.append((s, t))

    for s, t in pairs:
        res_d = dijkstra(graph, snap, s, t)
        h = make_geo_heuristic(graph, t)
        res_a = astar(graph, snap, s, t, h)
        nx_cost = nx.dijkstra_path_length(nx_g, s, t, weight="weight")

        assert res_d.status == "ok"
        assert res_a.status == "ok"
        assert res_a.reopened == 0

        tol = 1e-9 * max(1.0, nx_cost)
        assert abs(res_d.cost_s - nx_cost) <= tol
        assert abs(res_a.cost_s - nx_cost) <= tol
        assert abs(res_a.cost_s - res_d.cost_s) <= tol

        _verify_route(graph, snap, res_d, s, t)
        _verify_route(graph, snap, res_a, s, t)

