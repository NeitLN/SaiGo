"""Kiểm tra đóng đường và nhóm cạnh đối trên đồ thị thật (T41, issue #17).

Tiêu chuẩn: docs/DATA_MODEL.md mục 4.2 và thẻ A9 trong PLAN.md:
- Tự động skip nếu chưa có data/processed/manifest.json hoặc file đồ thị;
- reverse_twins(graph, meta):
  + Đếm số cạnh có / không có cạnh đối;
  + Tính đối xứng: twins[twins[e]] == e với mọi cạnh có cạnh đối;
  + Cạnh đối luôn là v -> u cùng tập way_ids và hình học đảo ngược;
  + Cạnh một chiều (oneway = True) không có cạnh đối;
- 50 cặp ngẫu nhiên trong SCC (seed 42):
  + Tìm tuyến cơ sở bằng Dijkstra;
  + Đóng một cạnh giữa tuyến bằng close_both_ways (cạnh và cạnh đối nếu có);
  + Dựng snapshot bằng build_snapshot với kịch bản baseline từ scenarios.json;
  + Dijkstra và A* khớp chi phí, tuyến mới không chứa cạnh đóng nào, chi phí mới >= chi phí cũ;
  + A* có reopened == 0;
  + Nếu no_path thì cả hai cùng trả về no_path;
  + Đếm số ca còn đường và no_path.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from app.algorithms.astar import astar
from app.algorithms.dijkstra import dijkstra
from app.algorithms.heuristics import make_geo_heuristic
from app.algorithms.result import SearchResult
from app.graph.closures import _is_reversed, close_both_ways, reverse_twins
from app.graph.model import Graph, GraphMeta, load_graph
from app.graph.scenario import Snapshot, baseline_snapshot, build_snapshot, load_scenarios

pytestmark = pytest.mark.realdata

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "processed" / "manifest.json"
SCENARIOS_PATH = ROOT / "data" / "config" / "scenarios.json"


@pytest.fixture(scope="module")
def real_graph() -> tuple[Graph, GraphMeta, dict]:
    """Nạp đồ thị thật vùng demo từ manifest.json; tự động skip nếu chưa có dữ liệu."""
    if not MANIFEST_PATH.exists():
        pytest.skip("chưa có data/processed/manifest.json")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    graph_file = ROOT / manifest["file"]
    if not graph_file.exists():
        pytest.skip(f"chưa có {manifest['file']}; chạy prepare_data.py build trước")
    graph, meta = load_graph(graph_file)
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


def test_realdata_reverse_twins(real_graph: tuple[Graph, GraphMeta, dict]) -> None:
    """Kiểm tra reverse_twins trên đồ thị thật: đếm cạnh, tính đối xứng, way_ids, hình học, oneway."""
    graph, meta, manifest = real_graph
    m = len(graph.edge_u)
    assert m == manifest["edge_count"]

    twins = reverse_twins(graph, meta)
    assert len(twins) == m

    has_twin_count = 0
    no_twin_count = 0

    for e in range(m):
        t = twins[e]
        if t is not None:
            has_twin_count += 1
            # Đối xứng
            assert twins[t] == e
            assert t != e, f"Cạnh {e} không thể là cạnh đối của chính mình"
            # Đầu và cuối ngược nhau: v -> u
            assert graph.edge_u[t] == graph.edge_v[e]
            assert graph.edge_v[t] == graph.edge_u[e]
            # Cùng tập way_ids
            assert frozenset(meta.edge_way_ids[t]) == frozenset(meta.edge_way_ids[e])
            # Hình học đảo ngược đúng
            assert _is_reversed(meta.edge_geometry[e], meta.edge_geometry[t])
            # Cạnh có cạnh đối thì không thể là oneway
            assert not meta.edge_oneway[e], f"Cạnh một chiều {e} không được có cạnh đối"
        else:
            no_twin_count += 1

    assert has_twin_count + no_twin_count == m
    # Số cạnh có cạnh đối phải là số chẵn (theo từng cặp đối xứng)
    assert has_twin_count % 2 == 0
    # Cạnh oneway trên đồ thị thật không có cạnh đối
    assert no_twin_count == manifest["oneway_edge_count"]


def test_realdata_closures_50_pairs(real_graph: tuple[Graph, GraphMeta, dict]) -> None:
    """50 cặp trong SCC: đóng một cạnh giữa tuyến bằng close_both_ways, so sánh Dijkstra và A*."""
    graph, meta, _ = real_graph

    if not SCENARIOS_PATH.exists():
        pytest.skip(f"chưa có file kịch bản tại {SCENARIOS_PATH}")
    scenarios = load_scenarios(SCENARIOS_PATH)
    assert "baseline" in scenarios
    baseline_scenario = scenarios["baseline"]

    base_snap = baseline_snapshot(graph)
    twins = reverse_twins(graph, meta)

    scc_nodes = [i for i in range(len(graph.node_lat)) if meta.node_in_scc[i]]
    assert len(scc_nodes) >= 50

    rng = random.Random(42)
    pairs: list[tuple[int, int]] = []
    while len(pairs) < 50:
        s = rng.choice(scc_nodes)
        t = rng.choice(scc_nodes)
        if s != t:
            pairs.append((s, t))

    n_has_path = 0
    n_no_path = 0

    for s, t in pairs:
        # 1. Tìm tuyến cơ sở
        res_base = dijkstra(graph, base_snap, s, t)
        assert res_base.status == "ok"
        assert res_base.cost_s is not None
        edge_ids = res_base.edge_ids
        assert len(edge_ids) >= 1

        # 2. Đóng một cạnh giữa tuyến bằng close_both_ways
        mid_edge = edge_ids[len(edge_ids) // 2]
        blocked = close_both_ways(graph, meta, mid_edge)
        assert mid_edge in blocked
        twin_mid = twins[mid_edge]
        if twin_mid is not None:
            assert twin_mid in blocked
            assert len(blocked) == 2
        else:
            assert len(blocked) == 1

        # 3. Dựng snapshot bằng build_snapshot kịch bản baseline kèm blocked
        snap = build_snapshot(graph, meta, baseline_scenario, blocked=blocked)
        assert snap.blocked == blocked

        # 4. Chạy lại Dijkstra và A*
        res_d = dijkstra(graph, snap, s, t)
        h = make_geo_heuristic(graph, t)
        res_a = astar(graph, snap, s, t, h)

        assert res_d.status == res_a.status

        if res_d.status == "ok":
            n_has_path += 1
            assert res_d.cost_s is not None
            assert res_a.cost_s is not None

            # Khớp chi phí giữa Dijkstra và A*
            tol = 1e-6 * max(1.0, res_d.cost_s)
            assert abs(res_d.cost_s - res_a.cost_s) <= tol

            # Chi phí mới >= chi phí cũ
            assert res_d.cost_s >= res_base.cost_s - 1e-6

            # Tuyến mới không chứa cạnh đóng nào
            for e in res_d.edge_ids:
                assert e not in blocked, f"Tuyến Dijkstra chứa cạnh đóng {e}"
            for e in res_a.edge_ids:
                assert e not in blocked, f"Tuyến A* chứa cạnh đóng {e}"

            # A* không mở lại node
            assert res_a.reopened == 0

            # Kiểm tra hình học tuyến
            _verify_route(graph, snap, res_d, s, t)
            _verify_route(graph, snap, res_a, s, t)
        else:
            n_no_path += 1

    assert n_has_path + n_no_path == 50
    # Ghi nhận kết quả
    assert n_has_path > 0

