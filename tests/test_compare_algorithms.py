"""O20: so sánh 4 thuật toán trên `tests/fixtures/mini.json` — đủ dòng/cột, chi phí khớp, CLI.

Chạy trên mini với `--pairs` nhỏ (3 tầng có thể không đủ trên 6 node nên dùng `fallback_used` của
`generate_queries`); mọi số trong test là dữ liệu THỬ, không phải số đo chính thức.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from compare_algorithms import (  # noqa: E402
    ALGOS,
    COMPARE_MEASUREMENT_COLUMNS,
    SUMMARY_COLUMNS,
    _check_cost,
    run_compare,
)
from app.graph.scenario import load_scenarios  # noqa: E402
from mini_cases import MINI  # noqa: E402

MINI_SCENARIOS = REPO_ROOT / "tests" / "fixtures" / "scenarios_mini.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PAIRS = 12
ALT_K = 2

needs_matplotlib = pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None,
    reason="cần matplotlib (extra 'bench') để vẽ hình",
)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def run_mini(tmp_path: Path, **overrides) -> tuple[dict, Path]:
    scenarios = load_scenarios(MINI_SCENARIOS)
    out_dir = tmp_path / "run"
    kwargs = dict(
        run_id="test-compare",
        scenario_ids=("baseline", "un-tac-tam-a"),
        n_pairs=PAIRS,
        seed=7,
        repeats=2,
        warmup=2,
        warmup_seconds=0.0,     # test không chờ ngân sách chạy nóng
        alt_k=ALT_K,
        command="pytest",
        make_figure=False,
    )
    kwargs.update(overrides)
    result = run_compare([MINI], scenarios, out_dir, **kwargs)
    return result, out_dir


def test_measurements_rows_columns_and_costs(tmp_path: Path) -> None:
    """Đúng số dòng (cặp × kịch bản × 4 thuật toán), đủ cột, 4 chi phí khớp Dijkstra."""
    result, out_dir = run_mini(tmp_path)
    assert result["n_queries"] == PAIRS
    assert result["n_rows"] == PAIRS * 2 * len(ALGOS)

    rows = read_csv(out_dir / "measurements.csv")
    assert rows and list(rows[0]) == COMPARE_MEASUREMENT_COLUMNS
    assert len(rows) == result["n_rows"]

    sha = hashlib.sha256(MINI.read_bytes()).hexdigest()
    by_query: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        assert row["algo"] in ALGOS
        assert row["dataset_id"] == "mini"
        assert int(row["n_nodes"]) == 6 and int(row["n_edges"]) == 8
        assert row["graph_sha256"] == sha
        assert row["suite"] == "compare" and row["workload"] == "demo"
        assert int(row["repeats"]) == 2
        assert int(row["runtime_ns_median"]) > 0
        assert int(row["runtime_ns_min"]) <= int(row["runtime_ns_median"])
        if row["algo"] == "alt":
            assert int(row["k"]) == ALT_K
        else:
            assert row["k"] == ""
        by_query.setdefault((row["scenario_id"], row["query_id"]), []).append(row)

    assert len(by_query) == PAIRS * 2
    for group in by_query.values():
        assert len(group) == len(ALGOS)
        assert len({(r["source"], r["target"]) for r in group}) == 1
        reference = next(r for r in group if r["algo"] == "dijkstra")
        for row in group:
            assert row["status"] == reference["status"]
            if reference["status"] == "ok":
                assert float(row["cost_s"]) == pytest.approx(float(reference["cost_s"]),
                                                             rel=1e-6, abs=1e-6)
                assert float(row["cost_s"]) > 0.0
            else:
                assert row["cost_s"] == row["distance_m"] == ""
            assert int(row["expanded"]) > 0


def test_summary_groups_and_metadata(tmp_path: Path) -> None:
    result, out_dir = run_mini(tmp_path)
    rows = read_csv(out_dir / "measurements.csv")
    summary = read_csv(out_dir / "summary.csv")
    assert list(summary[0]) == SUMMARY_COLUMNS

    expected_groups = {(r["scenario_id"], r["stratum"], r["algo"]) for r in rows}
    assert len(summary) == len(expected_groups)

    for row in summary:
        assert float(row["expanded_q1"]) <= float(row["expanded_median"]) <= float(
            row["expanded_q3"])
        assert int(row["runtime_ns_q1"]) <= int(row["runtime_ns_median"]) <= int(
            row["runtime_ns_q3"])
        assert int(row["n_queries"]) > 0
        if row["algo"] == "alt":
            assert int(row["k"]) == ALT_K
            assert float(row["preprocess_ms"]) >= 0.0
            assert int(row["memory_bytes"]) == 16 * 6 * ALT_K
        else:
            assert row["k"] == row["preprocess_ms"] == row["memory_bytes"] == ""

    config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
    assert config["run_id"] == "test-compare"
    assert config["suite"] == "compare"
    assert config["algorithms"] == list(ALGOS)
    assert config["scenarios"] == ["baseline", "un-tac-tam-a"]
    assert config["n_pairs"] == PAIRS and config["seed"] == 7
    assert config["repeats"] == 2 and config["warmup"] == 2
    assert config["warmup_seconds"] == 0.0
    assert config["alt_k_requested"] == ALT_K
    assert config["alt_index"][0]["k"] == ALT_K
    assert config["alt_index"][0]["memory_bytes"] == 16 * 6 * ALT_K
    assert config["strata_thresholds"]["delta_ngan_lt"] == 0.2
    assert config["strata_thresholds"]["delta_trung_binh_lt"] == 0.5
    assert config["command"] == "pytest"
    assert config["cli_args"] == {}
    drift = config["drift_check"]
    assert drift["ok_range"] == [0.83, 1.20]
    assert len(drift["runs"]) == 1
    assert drift["runs"][0]["dataset_id"] == "mini"
    assert drift["runs"][0]["n_queries"] > 0
    assert drift["runs"][0]["status"] in ("ok", "canh_bao")
    graph = config["graphs"][0]
    assert graph["dataset_id"] == "mini"
    assert graph["sha256"] == hashlib.sha256(MINI.read_bytes()).hexdigest()
    assert graph["L_m"] > 0 and graph["L_source"] in ("manifest", "bbox", "side_m")
    assert graph["sampling"]["L_m"] == graph["L_m"]
    assert not (out_dir / "fig_compare.png").exists()

    env = json.loads((out_dir / "env.json").read_text(encoding="utf-8"))
    assert env["python_executable"] == sys.executable
    assert env["dataset_sha256"] == ""      # hai đồ thị: sha256 nằm ở config.graphs
    assert "git_commit" in env


def test_check_cost_stops_on_mismatch() -> None:
    reference = SimpleNamespace(status="ok", cost_s=80.0)
    _check_cost(reference, SimpleNamespace(status="ok", cost_s=80.0), "ok")
    with pytest.raises(RuntimeError, match="trạng thái lệch"):
        _check_cost(reference, SimpleNamespace(status="no_path", cost_s=None), "status")
    with pytest.raises(RuntimeError, match="chi phí lệch"):
        _check_cost(reference, SimpleNamespace(status="ok", cost_s=100.0), "cost")
    _check_cost(SimpleNamespace(status="no_path", cost_s=None),
                SimpleNamespace(status="no_path", cost_s=None), "no_path")


def test_run_compare_rejects_bad_scenario_and_params(tmp_path: Path) -> None:
    scenarios = load_scenarios(MINI_SCENARIOS)
    with pytest.raises(ValueError, match="kịch bản không có"):
        run_compare([MINI], scenarios, tmp_path / "a", run_id="x",
                    scenario_ids=("khong-co",), n_pairs=2, make_figure=False)
    with pytest.raises(ValueError, match="pairs/repeats"):
        run_compare([MINI], scenarios, tmp_path / "b", run_id="x",
                    scenario_ids=("baseline",), n_pairs=0, make_figure=False)
    with pytest.raises(ValueError, match="không tìm thấy file đồ thị"):
        run_compare([tmp_path / "khong-co.json"], scenarios, tmp_path / "c", run_id="x",
                    scenario_ids=("baseline",), n_pairs=2, make_figure=False)
    with pytest.raises(ValueError, match="warmup_seconds"):
        run_compare([MINI], scenarios, tmp_path / "d", run_id="x",
                    scenario_ids=("baseline",), n_pairs=2, warmup_seconds=-1,
                    make_figure=False)


def test_warm_up_budget_and_disable() -> None:
    """`_warm_up` chạy đúng `warmup` cặp khi ngân sách = 0, lặp tới đủ ngân sách, và tắt hẳn khi cả hai = 0."""
    import time as _time

    from compare_algorithms import _warm_up, load_case
    from app.graph.scenario import build_snapshot

    scenarios = load_scenarios(MINI_SCENARIOS)
    case = load_case(MINI, n_pairs=4, seed=5, alt_k=ALT_K)
    snap = build_snapshot(case.graph, case.meta, scenarios["baseline"])

    assert _warm_up(case.graph, snap, case.queries, case.index, 0, 0.0) == 0

    one_pass = _warm_up(case.graph, snap, case.queries, case.index, 2, 0.0)
    assert one_pass == 2 * len(ALGOS)

    t0 = _time.perf_counter()
    calls = _warm_up(case.graph, snap, case.queries, case.index, 2, 0.05)
    elapsed = _time.perf_counter() - t0
    assert calls >= 2 * len(ALGOS)
    assert calls % (2 * len(ALGOS)) == 0        # luôn kết thúc ở cuối một lượt
    assert elapsed >= 0.045


@needs_matplotlib
def test_main_writes_all_outputs_and_figure(tmp_path: Path) -> None:
    from compare_algorithms import main

    ret = main([
        "--graphs", str(MINI),
        "--scenario-file", str(MINI_SCENARIOS),
        "--scenarios", "baseline",
        "--pairs", "6",
        "--seed", "3",
        "--repeats", "2",
        "--warmup", "1",
        "--alt-k", "2",
        "--run-id", "test-compare-main",
        "--out", str(tmp_path),
    ])
    assert ret == 0
    out_dir = tmp_path / "test-compare-main"
    for name in ("measurements.csv", "summary.csv", "env.json", "config.json",
                 "fig_compare.png"):
        assert (out_dir / name).is_file(), name
    assert (out_dir / "fig_compare.png").read_bytes()[:8] == PNG_MAGIC

    rows = read_csv(out_dir / "measurements.csv")
    assert len(rows) == 6 * len(ALGOS)      # 6 cặp × 1 kịch bản × 4 thuật toán
    config = json.loads((out_dir / "config.json").read_text(encoding="utf-8"))
    assert "compare_algorithms.py" in config["command"]
    assert "--pairs 6" in config["command"]
    assert config["cli_args"]["pairs"] == 6
    assert config["cli_args"]["graphs"] == [str(MINI)]
