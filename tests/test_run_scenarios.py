"""T63 (E4): ùn tắc, đóng đoạn, không còn đường (docs/tasks/T63-congestion-closure.md)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
TESTS_DIR = Path(__file__).resolve().parent
for p in (SCRIPTS_DIR, TESTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import plot_results  # noqa: E402
from run_benchmarks import MEASUREMENT_COLUMNS, route_sig  # noqa: E402
from run_scenarios import check_invariants, closure_edges, main, nopath_edges  # noqa: E402
import summarize_results  # noqa: E402

from helpers.random_graph import random_graph_dict  # noqa: E402

OLD_27 = [
    "run_id", "suite", "dataset_id", "size_label", "n_nodes", "n_edges", "query_id", "workload", "stratum",
    "source", "target", "hav_m", "algo", "scenario_id", "blocked_count", "status", "cost_s", "distance_m",
    "expanded", "unique_expanded", "reopened", "relaxations", "pushes", "max_frontier", "runtime_ns_median",
    "runtime_ns_min", "repeats",
]


def test_columns_keep_old_27_then_append_two():
    assert list(MEASUREMENT_COLUMNS[:27]) == OLD_27
    assert list(MEASUREMENT_COLUMNS[27:]) == ["route_sig", "snapshot_ns"]


def test_route_sig_identifies_route():
    assert route_sig("ok", [3, 1, 4]) == route_sig("ok", [3, 1, 4])
    assert route_sig("ok", [3, 1, 4]) != route_sig("ok", [3, 4, 1])     # thứ tự cạnh là một phần của tuyến
    assert len(route_sig("ok", [3, 1, 4])) == 12
    assert route_sig("no_path", []) == ""


def test_closure_edges_mid_edge_and_twin():
    twins = {10: 11, 11: 10, 20: None, 30: 31, 31: 30, 40: None}
    assert closure_edges([10, 20, 30, 40], twins) == [30, 31]          # ⌊4/2⌋ = 2 → cạnh 30 và cạnh đối 31
    assert closure_edges([10, 20, 40], twins) == [20]                  # ⌊3/2⌋ = 1 → cạnh 20, một chiều


def test_nopath_edges_are_all_edges_into_target():
    class G:
        edge_v = [2, 5, 2, 7, 2]
    assert nopath_edges(G, 2) == [0, 2, 4]


def test_old_and_new_measurement_files_both_readable(tmp_path):
    row = {c: "" for c in MEASUREMENT_COLUMNS}
    row.update({"run_id": "r", "suite": "scenario", "dataset_id": "d", "size_label": "d", "n_nodes": "3",
                "n_edges": "4", "query_id": "0", "workload": "demo", "stratum": "ngan", "source": "0", "target": "1",
                "hav_m": "100", "algo": "dijkstra", "scenario_id": "baseline", "blocked_count": "0", "status": "ok",
                "cost_s": "10", "distance_m": "100", "expanded": "3", "unique_expanded": "3", "reopened": "0",
                "relaxations": "4", "pushes": "4", "max_frontier": "2", "runtime_ns_median": "1000",
                "runtime_ns_min": "900", "repeats": "1", "route_sig": "abc", "snapshot_ns": "0"})
    for name, cols in (("old", OLD_27), ("new", list(MEASUREMENT_COLUMNS))):
        d = tmp_path / name
        d.mkdir()
        with (d / "measurements.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerow(row)
            w.writerow({**row, "algo": "astar", "expanded": "2"})
        assert len(plot_results.read_measurements(d)) == 2
        assert len(summarize_results.read_rows(d)) == 2


def test_check_invariants_flags_congestion_making_route_cheaper():
    rows = [
        {"suite": "scenario", "query_id": "0", "algo": "dijkstra", "scenario_id": "baseline", "status": "ok", "cost_s": "100"},
        {"suite": "scenario", "query_id": "0", "algo": "dijkstra", "scenario_id": "peak", "status": "ok", "cost_s": "90"},
    ]
    bad = check_invariants(rows, closure_routes={}, nopath_ids=set())
    assert len(bad) == 1 and bad[0]["query_id"] == "0"


@pytest.fixture
def graph_file(tmp_path):
    g = random_graph_dict(seed=7, n_nodes=80, n_edges=320)
    path = tmp_path / "rand.json"
    path.write_text(json.dumps(g), encoding="utf-8")
    return path


def test_run_scenarios_end_to_end(tmp_path, graph_file):
    out = tmp_path / "results"
    code = main(["--graph", str(graph_file), "--scenario-file", "tests/fixtures/scenarios_mini.json",
                 "--pairs", "30", "--closure", "8", "--nopath", "5", "--seed", "42", "--repeats", "1", "--warmup", "0",
                 "--out", str(out), "--run-id", "t63"])
    assert code == 0
    run = out / "t63"
    with (run / "measurements.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with (run / "queries.csv").open(encoding="utf-8") as f:
        queries = list(csv.DictReader(f))
    suites = {r["suite"] for r in rows}
    assert suites == {"scenario", "closure", "nopath"}
    n_scen = len([q for q in queries if q["suite"] == "scenario"])
    assert len([r for r in rows if r["suite"] == "scenario"]) == n_scen * 2 * 2      # 2 kịch bản × 2 thuật toán
    closure = [r for r in rows if r["suite"] == "closure"]
    assert 0 < len(closure) <= 8 * 2
    assert all(int(r["snapshot_ns"]) > 0 and int(r["blocked_count"]) >= 1 for r in closure)
    nopath = [r for r in rows if r["suite"] == "nopath"]
    assert len(nopath) == 5 * 2 and all(r["status"] == "no_path" for r in nopath)
    assert all(q["blocked_edges"] for q in queries if q["suite"] in ("closure", "nopath"))
    assert all(r["route_sig"] for r in rows if r["status"] == "ok")
    assert not (run / "violations.csv").exists()
