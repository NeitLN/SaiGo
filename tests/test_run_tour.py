"""T74 (E5): benchmark tour, ghi tour_measurements.csv (docs/tasks/T74-tour-benchmark.md)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent
for p in (ROOT / "scripts", TESTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.graph.geo import haversine_m  # noqa: E402
from app.graph.model import load_graph, node_by_name  # noqa: E402
from app.graph.scenario import baseline_snapshot, build_snapshot  # noqa: E402
import plot_results  # noqa: E402
import run_benchmarks  # noqa: E402
from run_tour import TOUR_COLUMNS, main, plan_set, sample_sets  # noqa: E402
import summarize_results  # noqa: E402

from helpers.random_graph import random_graph_dict  # noqa: E402
from mini_cases import edge_id, load_mini  # noqa: E402

METHODS = ["input", "nearest_neighbor", "nearest_neighbor_2opt", "held_karp"]


def _by_method(result):
    return {m: result["methods"][m] for m in METHODS}


def test_columns_match_what_plot_and_summarize_read():
    assert list(TOUR_COLUMNS) == list(plot_results.TOUR_COLUMNS) == list(summarize_results.TOUR_COLUMNS)


def test_plan_set_on_mini_matches_api_numbers():
    graph, meta = load_mini()
    nodes = [node_by_name(meta, n) for n in ("S", "B", "A", "T")]       # kho S; thứ tự nhập B, A, T (như test T72)
    res = plan_set(graph, baseline_snapshot(graph), nodes)
    m = _by_method(res)
    assert res["feasible"] is True
    assert m["input"]["cost_s"] == pytest.approx(280.0)
    assert m["nearest_neighbor"]["cost_s"] == pytest.approx(180.0)
    assert m["held_karp"]["cost_s"] == pytest.approx(180.0)
    assert m["held_karp"]["cost_s"] <= m["nearest_neighbor_2opt"]["cost_s"] + 1e-9 <= m["nearest_neighbor"]["cost_s"] + 2e-9
    assert sorted(m["nearest_neighbor"]["order"]) == [0, 1, 2]       # vị trí trong danh sách điểm giao
    assert res["matrix_ns"] > 0


def test_plan_set_infeasible_when_a_leg_is_unreachable():
    graph, meta = load_mini()
    snap = build_snapshot(graph, meta, _baseline(), blocked={edge_id(graph, meta, "A->T")})
    nodes = [node_by_name(meta, n) for n in ("S", "A", "T", "B")]      # A chỉ có cạnh ra A→T (như test T72)
    res = plan_set(graph, snap, nodes)
    assert res["feasible"] is False
    assert all(res["methods"][m]["cost_s"] is None for m in METHODS)


def _baseline():
    from app.graph.scenario import load_scenarios
    return load_scenarios("tests/fixtures/scenarios_mini.json")["baseline"]


@pytest.fixture
def rand_graph(tmp_path):
    path = tmp_path / "rand.json"
    path.write_text(json.dumps(random_graph_dict(seed=11, n_nodes=120, n_edges=480)), encoding="utf-8")
    return path


def test_sample_sets_are_separated_and_deterministic(rand_graph):
    graph, meta = load_graph(rand_graph)
    a = sample_sets(graph, meta, n_stops=4, count=5, seed=42, min_sep_m=150)
    b = sample_sets(graph, meta, n_stops=4, count=5, seed=42, min_sep_m=150)
    assert a == b and len(a) == 5
    for nodes in a:
        assert len(nodes) == 5 and len(set(nodes)) == 5
        for i in range(5):
            for j in range(i + 1, 5):
                assert haversine_m(graph.node_lat[nodes[i]], graph.node_lon[nodes[i]],
                                   graph.node_lat[nodes[j]], graph.node_lon[nodes[j]]) >= 150


def test_run_tour_end_to_end_and_readers(tmp_path, rand_graph):
    out = tmp_path / "results"
    assert main(["--graph", str(rand_graph), "--sizes", "4", "6", "--sets", "3", "--seed", "42",
                 "--out", str(out), "--run-id", "t74"]) == 0
    run = out / "t74"
    with (run / "tour_measurements.csv").open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert reader.fieldnames == list(TOUR_COLUMNS)
    assert len(rows) == 2 * 3 * 4
    assert {r["suite"] for r in rows} == {"tour"}
    assert {r["method"] for r in rows} == set(METHODS)
    assert len(plot_results.read_tour_measurements(run)) == len(rows)
    assert len(summarize_results.read_tour_rows(run)) == len(rows)
    for (set_id, n) in {(r["set_id"], r["n_stops"]) for r in rows}:
        group = {r["method"]: r for r in rows if r["set_id"] == set_id}
        assert len({r["matrix_ns"] for r in group.values()}) == 1      # một ma trận cho cả bộ
        if group["input"]["feasible"] == "true":
            hk, opt, nn = (float(group[m]["cost_s"]) for m in ("held_karp", "nearest_neighbor_2opt", "nearest_neighbor"))
            assert hk <= opt + 1e-6 <= nn + 2e-6
            assert len(group["input"]["order"].split(";")) == int(n)


def test_run_benchmarks_suite_tour_delegates(tmp_path, rand_graph):
    out = tmp_path / "results"
    assert run_benchmarks.main(["--suite", "tour", "--graph", str(rand_graph), "--seed", "42",
                                "--out", str(out), "--run-id", "via-rb", "--tour-sizes", "4", "--tour-sets", "2"]) == 0
    assert (out / "via-rb" / "tour_measurements.csv").exists()


def test_readers_no_longer_point_to_missing_proposal_file():
    for script in ("plot_results.py", "summarize_results.py"):
        assert "E5_proposal.md" not in (ROOT / "scripts" / script).read_text(encoding="utf-8")


@pytest.mark.realdata
def test_demo_case_kho_5_diem_matches_api():
    path = ROOT / "data" / "processed" / "hcm-benthanh-r2000-20261024.json"
    if not path.exists():
        pytest.skip("chưa có đồ thị demo trong data/processed/")
    from app.graph.snap import nearest_node
    graph, meta = load_graph(path)
    case = next(c for c in json.loads((ROOT / "data" / "demo" / "cases.json").read_text(encoding="utf-8"))["cases"]
                if c["mode"] == "tour")
    pts = [case["depot"], *case["stops"]]
    nodes = []
    for p in pts:
        s = nearest_node(graph, meta, p["lat"], p["lon"])
        nodes.append(getattr(s, "node_id", s))
    m = _by_method(plan_set(graph, baseline_snapshot(graph), nodes))
    assert [round(m[k]["cost_s"], 1) for k in METHODS] == [1066.0, 1003.3, 898.1, 627.8]
