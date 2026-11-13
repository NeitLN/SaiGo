"""O18: thí nghiệm số landmark k của ALT (`scripts/alt_landmark_sweep.py`).

Chạy trên `tests/fixtures/mini.json` với k nhỏ: đúng số dòng (cặp × k × kịch bản), đủ cột,
chi phí khớp Dijkstra, cùng bộ cặp cho mọi k, summary có median/IQR + tiền xử lý, và CLI ghi đủ
`env.json`/`config.json`/`fig_altk.png`.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from alt_landmark_sweep import (  # noqa: E402
    MEASUREMENT_COLUMNS,
    SUMMARY_COLUMNS,
    run_sweep,
    sample_pairs,
)
from app.graph.model import load_graph
from app.graph.scenario import load_scenarios
from helpers.random_graph import make_random_graph
from mini_cases import MINI

MINI_SCENARIOS = REPO_ROOT / "tests" / "fixtures" / "scenarios_mini.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

needs_matplotlib = pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None,
    reason="cần matplotlib (extra 'bench') để vẽ hình",
)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def run_mini(tmp_path: Path, **overrides) -> tuple[dict, Path]:
    graph, meta = load_graph(MINI)
    scenarios = load_scenarios(MINI_SCENARIOS)
    out_dir = tmp_path / "run"
    kwargs = dict(
        run_id="test-altk",
        scenario_ids=("baseline", "un-tac-tam-a"),
        k_values=(1, 2),
        n_pairs=10,
        seed=7,
        repeats=3,
        warmup=2,
        dataset_path=MINI,
        command="pytest",
        make_figure=False,
    )
    kwargs.update(overrides)
    result = run_sweep(graph, meta, scenarios, out_dir, **kwargs)
    return result, out_dir


def test_run_sweep_mini_rows_columns_and_cost(tmp_path: Path) -> None:
    """Đúng số dòng, đủ cột, mọi dòng ALT/A* khớp chi phí Dijkstra, cùng cặp cho mọi k."""
    result, out_dir = run_mini(tmp_path)
    assert result["n_rows"] == 10 * 2 * 2

    rows = read_csv(out_dir / "measurements.csv")
    assert rows and list(rows[0]) == MEASUREMENT_COLUMNS
    assert len(rows) == result["n_rows"]

    for row in rows:
        assert row["algo"] == "alt"
        assert int(row["k"]) in (1, 2)
        assert int(row["n_nodes"]) == 6 and int(row["n_edges"]) == 8
        assert row["status"] == row["ref_dijkstra_status"]
        if row["status"] == "ok":
            assert float(row["cost_s"]) == pytest.approx(float(row["ref_dijkstra_cost_s"]),
                                                         rel=1e-6, abs=1e-6)
            assert float(row["ref_astar_cost_s"]) == pytest.approx(
                float(row["ref_dijkstra_cost_s"]), rel=1e-6, abs=1e-6)
        assert int(row["runtime_ns_median"]) > 0
        assert int(row["runtime_ns_min"]) <= int(row["runtime_ns_median"])
        assert int(row["repeats"]) == 3

    # Cùng bộ cặp cho mọi k: mỗi (kịch bản, query_id) có đúng 2 dòng (2 k), cùng source/target.
    by_query: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        by_query.setdefault((row["scenario_id"], row["query_id"]), []).append(row)
    assert len(by_query) == 10 * 2
    for group in by_query.values():
        assert len({(r["source"], r["target"]) for r in group}) == 1


def test_run_sweep_mini_summary_and_metadata(tmp_path: Path) -> None:
    result, out_dir = run_mini(tmp_path)

    summary = read_csv(out_dir / "summary.csv")
    assert list(summary[0]) == SUMMARY_COLUMNS
    assert len(summary) == 2 * (2 + 2)          # 2 kịch bản × (Dijkstra + A* + 2 k)

    alt_rows = [r for r in summary if r["algo"] == "alt"]
    assert len(alt_rows) == 2 * 2
    for row in alt_rows:
        assert int(row["n_queries"]) == 10
        assert float(row["expanded_q1"]) <= float(row["expanded_median"]) <= float(row["expanded_q3"])
        assert int(row["runtime_ns_q1"]) <= int(row["runtime_ns_median"]) <= int(row["runtime_ns_q3"])
        assert float(row["preprocess_ms"]) >= 0.0
        assert int(row["memory_bytes"]) == 16 * 6 * int(row["k"])   # 6 node × 2 chiều × 8 byte

    refs = [r for r in summary if r["algo"] in ("dijkstra", "astar")]
    assert len(refs) == 2 * 2
    assert all(r["preprocess_ms"] == "" and r["memory_bytes"] == "" for r in refs)

    queries = read_csv(out_dir / "queries.csv")
    assert len(queries) == 10
    assert result["n_pairs"] == 10

    config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
    assert config["k_values"] == [1, 2]
    assert config["scenarios"] == ["baseline", "un-tac-tam-a"]
    assert config["command"] == "pytest"
    env = json.loads((out_dir / "env.json").read_text(encoding="utf-8"))
    assert env["python_executable"] == sys.executable
    assert env["dataset_sha256"]
    assert not (out_dir / "fig_altk.png").exists()      # make_figure=False


def test_sample_pairs_are_scc_unique_and_seeded() -> None:
    graph, meta = make_random_graph(seed=5, n_nodes=30, n_edges=80)
    pairs = sample_pairs(graph, meta, 60, seed=123)
    assert len(pairs) == 60
    keys = [(p["source"], p["target"]) for p in pairs]
    assert len(set(keys)) == 60
    assert all(s != t for s, t in keys)
    assert all(meta.node_in_scc[s] and meta.node_in_scc[t] for s, t in keys)
    assert pairs == sample_pairs(graph, meta, 60, seed=123)      # cùng seed → cùng bộ cặp

    # mini không đủ cặp khác nhau trong SCC: vẫn trả đúng số cặp, không lặp vô hạn.
    mini_graph, mini_meta = load_graph(MINI)
    many = sample_pairs(mini_graph, mini_meta, 40, seed=1)
    assert len(many) == 40 and all(p["source"] != p["target"] for p in many)


def test_run_sweep_rejects_bad_scenario_and_k(tmp_path: Path) -> None:
    graph, meta = load_graph(MINI)
    scenarios = load_scenarios(MINI_SCENARIOS)
    with pytest.raises(ValueError, match="kịch bản không có"):
        run_sweep(graph, meta, scenarios, tmp_path / "a", run_id="x",
                  scenario_ids=("khong-co",), k_values=(1,), n_pairs=2, make_figure=False)
    with pytest.raises(ValueError, match="k phải là số nguyên dương"):
        run_sweep(graph, meta, scenarios, tmp_path / "b", run_id="x",
                  scenario_ids=("baseline",), k_values=(0,), n_pairs=2, make_figure=False)


@needs_matplotlib
def test_main_writes_all_outputs_and_figure(tmp_path: Path) -> None:
    ret = run_main([
        "--graph", str(MINI),
        "--scenario-file", str(MINI_SCENARIOS),
        "--scenarios", "baseline",
        "--k", "1", "2",
        "--pairs", "6",
        "--seed", "3",
        "--repeats", "2",
        "--warmup", "1",
        "--run-id", "test-altk-main",
        "--out", str(tmp_path),
    ])
    assert ret == 0
    out_dir = tmp_path / "test-altk-main"
    for name in ("queries.csv", "measurements.csv", "summary.csv", "env.json", "config.json",
                 "fig_altk.png"):
        assert (out_dir / name).is_file(), name
    assert (out_dir / "fig_altk.png").read_bytes()[:8] == PNG_MAGIC

    rows = read_csv(out_dir / "measurements.csv")
    assert len(rows) == 6 * 2                  # 6 cặp × 2 k × 1 kịch bản
    config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
    assert "alt_landmark_sweep.py" in config["command"]
    assert "--k 1 2" in config["command"]
    assert config["cli_args"]["pairs"] == 6
    assert config["cli_args"]["run_id"] == "test-altk-main"


def run_main(argv: list[str]) -> int:
    """Gọi `main` của script mà không để lẫn `sys.argv` của pytest."""
    from alt_landmark_sweep import main

    return main(argv)
