"""E2c: biến thể A* chỉ dùng để đo (scripts/measure_heuristic_cost.py).

A* với h tính sẵn thành mảng phải cho **cùng** kết quả với A* gốc (chi phí, tuyến, số node mở rộng,
số lần push), vì giá trị h trùng từng bit; bộ đếm số lần gọi h phải bằng `pushes`. Số trong test
là dữ liệu THỬ trên `mini.json` và đồ thị ngẫu nhiên, không phải số đo chính thức.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import pytest

from app.algorithms.astar import astar
from app.algorithms.heuristics import make_geo_heuristic
from app.graph.scenario import baseline_snapshot, make_snapshot
from helpers.random_graph import make_random_graph
from mini_cases import MINI, load_mini

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import measure_heuristic_cost as hcost  # noqa: E402


def _same_as_astar(graph, snap, source, target):
    h = make_geo_heuristic(graph, target)
    ref = astar(graph, snap, source, target, h, trace_limit=5)
    got = hcost.astar_precomputed(graph, snap, source, target, hcost.precompute_h(graph, target),
                                  trace_limit=5)
    assert got.status == ref.status
    assert got.cost_s == ref.cost_s                      # cùng phép cộng, cùng thứ tự → bằng hẳn
    assert got.edge_ids == ref.edge_ids
    assert (got.expanded, got.reopened, got.relaxations, got.pushes, got.max_frontier) == \
        (ref.expanded, ref.reopened, ref.relaxations, ref.pushes, ref.max_frontier)
    assert got.trace == ref.trace
    return ref


def test_precompute_h_equals_geo_heuristic_bit_for_bit():
    graph, _ = load_mini()
    for target in range(len(graph.node_lat)):
        h = make_geo_heuristic(graph, target)
        assert hcost.precompute_h(graph, target) == [h(n) for n in range(len(graph.node_lat))]


def test_precomputed_astar_matches_astar_on_mini_all_pairs():
    graph, _ = load_mini()
    snap = baseline_snapshot(graph)
    n = len(graph.node_lat)
    for source in range(n):
        for target in range(n):
            _same_as_astar(graph, snap, source, target)


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_precomputed_astar_matches_astar_on_random_graphs_with_closures(seed):
    graph, _ = make_random_graph(seed=seed, n_nodes=40, n_edges=120)
    base = baseline_snapshot(graph)
    closed = make_snapshot(graph, list(base.weights), blocked=frozenset(range(0, 120, 7)))
    statuses = set()
    for snap in (base, closed):
        for source in range(0, 40, 3):
            for target in range(40):
                statuses.add(_same_as_astar(graph, snap, source, target).status)
    assert statuses == {"ok", "no_path"}                 # có cả node không tới được (helper)


def test_counting_heuristic_counts_one_call_per_push():
    graph, _ = make_random_graph(seed=3, n_nodes=40, n_edges=120)
    snap = baseline_snapshot(graph)
    for target in (5, 17, 39):
        counting = hcost.CountingHeuristic(make_geo_heuristic(graph, target))
        res = astar(graph, snap, 0, target, counting)
        assert counting.calls == res.pushes
        assert counting(target) == 0.0                   # h(đích) = 0, vẫn đếm
        assert counting.calls == res.pushes + 1


def test_pair_metrics_hand_computed():
    row = {"t_d_ns": 1000, "t_a_ns": 800, "t_search_ns": 500, "t_pre_ns": 1500, "h_calls": 2,
           "expanded_d": 10, "expanded_a": 4}
    m = hcost.pair_metrics(row, h_call_ns=100.0)
    assert m["s"] == pytest.approx(1.25)
    assert m["s_search"] == pytest.approx(2.0)
    assert m["s_with_pre"] == pytest.approx(0.5)
    assert m["share_a"] == pytest.approx(37.5)           # (800 − 500) / 800
    assert m["share_b"] == pytest.approx(25.0)           # 2 · 100 / 800
    assert (m["ns_per_node_d"], m["ns_per_node_a"], m["ns_per_node_search"]) == (100, 200, 125)


def test_run_on_mini_writes_all_files(tmp_path):
    graph, _ = load_mini()
    queries = tmp_path / "queries.csv"
    pairs = [(0, 5), (5, 0), (1, 4), (2, 3)]
    with queries.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["query_id", "workload", "stratum", "source", "target", "hav_m", "delta"])
        for i, (s, t) in enumerate(pairs):
            writer.writerow([i, "thu", ("ngan", "dai")[i % 2], s, t, 1.0, 0.1])
    out = tmp_path / "out" / "run-thu"
    result = hcost.run(MINI, queries, out, "run-thu", repeats=2, warmup=2, limit=None,
                       micro_targets=2, micro_calls=200, micro_rounds=2, seed=1,
                       scenario_file=REPO_ROOT / "data" / "config" / "scenarios.json",
                       cli_args={"thu": True})
    for name in ("queries.csv", "hcost_measurements.csv", "microbench.csv", "summary.csv",
                 "env.json", "config.json"):
        assert (out / name).is_file(), name
    with (out / "hcost_measurements.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(pairs)
    assert list(rows[0]) == hcost.MEASUREMENT_COLUMNS
    for row in rows:
        assert row["h_calls"] == row["pushes_a"]
        assert int(row["t_search_ns"]) > 0 and int(row["t_pre_ns"]) > 0
    with (out / "summary.csv").open(encoding="utf-8") as fh:
        summary = list(csv.DictReader(fh))
    assert [r["stratum"] for r in summary] == ["ngan", "dai", "tat_ca"]
    assert list(summary[0]) == hcost.SUMMARY_COLUMNS
    config = json.loads((out / "config.json").read_text(encoding="utf-8"))
    assert config["run_id"] == "run-thu" and config["n_queries"] == len(pairs)
    text = hcost.render(result["summary"], result["micro"], "run-thu")
    assert "| tất cả | 4 |" in text
    assert not math.isnan(result["summary"][-1]["share_a"])
