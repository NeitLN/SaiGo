"""Kiểm tra bộ chạy benchmark offline (T60, issue #25).

Tiêu chuẩn: docs/EXPERIMENT_PLAN.md mục 2, 3 và docs/TASKS.md mục T60.
- Sinh cặp có seed và phân tầng (ngắn, trung bình, dài);
- Ghi queries.csv trước khi đo;
- Warm-up;
- Lặp R lần, đổi thứ tự thuật toán giữa cặp chẵn và lẻ;
- measurements.csv có đủ 27 cột theo EXPERIMENT_PLAN mục 3.3;
- env.json và config.json ghi nhận đầy đủ môi trường đo;
- 100% cặp khớp chi phí Dijkstra và A*.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import sys

import pytest

# Thêm đường dẫn để import script và helpers
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from helpers.random_graph import make_random_graph, random_graph_dict
from run_benchmarks import (
    MEASUREMENT_COLUMNS,
    QUERY_COLUMNS,
    collect_env,
    generate_queries,
    main,
    read_queries_csv,
    run_benchmark,
    write_queries_csv,
)

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
MINI_GRAPH_PATH = FIXTURES_DIR / "mini.json"
MINI_SCENARIOS_PATH = FIXTURES_DIR / "scenarios_mini.json"


def test_run_benchmarks_cli_mini(tmp_path: Path) -> None:
    """Tiêu chí chấp nhận chính: chạy bộ demo trên mini.json, đủ 27 cột, 100% khớp chi phí."""
    cmd_args = [
        "--suite", "demo",
        "--graph", str(MINI_GRAPH_PATH),
        "--pairs", "20",
        "--seed", "42",
        "--repeats", "3",
        "--warmup", "5",
        "--run-id", "run_mini",
        "--out", str(tmp_path),
    ]

    ret = main(cmd_args)
    assert ret == 0, "main() phải trả về 0 (thành công)"

    out_dir = tmp_path / "run_mini"

    # 1. Kiểm tra queries.csv
    queries_file = out_dir / "queries.csv"
    assert queries_file.is_file(), "queries.csv phải được tạo"
    queries = read_queries_csv(queries_file)
    assert len(queries) == 20, "phải có đúng 20 cặp truy vấn"

    with queries_file.open("r", encoding="utf-8") as f:
        header = f.readline().strip().split(",")
        assert header == QUERY_COLUMNS, f"header queries.csv phải là {QUERY_COLUMNS}"

    # 2. Kiểm tra measurements.csv
    meas_file = out_dir / "measurements.csv"
    assert meas_file.is_file(), "measurements.csv phải được tạo"

    with meas_file.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == MEASUREMENT_COLUMNS, "measurements.csv phải đủ 27 cột chuẩn"
        rows = list(reader)

    # 20 query × 2 thuật toán (dijkstra, astar) = 40 dòng
    assert len(rows) == 40

    # Đối chiếu từng cặp: 100% khớp chi phí và status
    dijkstra_rows = {int(r["query_id"]): r for r in rows if r["algo"] == "dijkstra"}
    astar_rows = {int(r["query_id"]): r for r in rows if r["algo"] == "astar"}
    assert len(dijkstra_rows) == 20
    assert len(astar_rows) == 20

    for q_id in range(20):
        d_row = dijkstra_rows[q_id]
        a_row = astar_rows[q_id]
        assert d_row["status"] == a_row["status"]
        if d_row["status"] == "ok":
            d_cost = float(d_row["cost_s"])
            a_cost = float(a_row["cost_s"])
            assert abs(d_cost - a_cost) <= 1e-6 * max(1.0, d_cost)
            # A* với heuristic địa lý consistent có reopened == 0
            assert int(a_row["reopened"]) == 0

        # Kiểm tra thời gian đo hợp lệ (ns > 0, median >= min)
        assert int(d_row["runtime_ns_median"]) >= int(d_row["runtime_ns_min"]) > 0
        assert int(a_row["runtime_ns_median"]) >= int(a_row["runtime_ns_min"]) > 0
        assert int(d_row["repeats"]) == 3

    # 3. Kiểm tra env.json
    env_file = out_dir / "env.json"
    assert env_file.is_file(), "env.json phải được tạo"
    env_data = json.loads(env_file.read_text(encoding="utf-8"))
    assert "platform" in env_data
    assert "python_version" in env_data
    assert "git_commit" in env_data
    assert "git_dirty" in env_data
    assert isinstance(env_data["git_dirty"], bool)
    assert "dataset_sha256" in env_data
    assert env_data["dataset_sha256"] != ""

    # 4. Kiểm tra config.json
    config_file = out_dir / "config.json"
    assert config_file.is_file(), "config.json phải được tạo"
    cfg_data = json.loads(config_file.read_text(encoding="utf-8"))
    assert cfg_data["n_queries"] == 20
    assert cfg_data["repeats"] == 3
    assert cfg_data["suite"] == "demo"
    assert "sampling" in cfg_data

    sampling = cfg_data["sampling"]
    assert "L_m" in sampling
    assert sampling["L_source"] == "bbox"
    assert "target_per_stratum" in sampling
    assert "actual_per_stratum" in sampling
    assert "rejected" in sampling
    assert "fallback_used" in sampling
    assert sampling["fallback_used"] is True  # mini.json không có cặp delta < 0.2
    assert "strata_stats" in sampling


def test_run_benchmarks_default_run_id_format(tmp_path: Path) -> None:
    """Khi không truyền --run-id, định dạng run_id phải là YYYYMMDD-HHMM-<suite>-<git7>."""
    ret = main([
        "--suite", "demo",
        "--graph", str(MINI_GRAPH_PATH),
        "--pairs", "3",
        "--out", str(tmp_path),
    ])
    assert ret == 0

    subdirs = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(subdirs) == 1
    run_dir = subdirs[0]
    run_id = run_dir.name

    pattern = r"^\d{8}-\d{4}-demo-[0-9a-fA-F]{7}$"
    assert re.match(pattern, run_id), f"run_id '{run_id}' không đúng định dạng {pattern}"
    assert (run_dir / "measurements.csv").is_file()
    assert (run_dir / "queries.csv").is_file()


def test_run_benchmarks_on_random_graph(tmp_path: Path) -> None:
    """Benchmark trên đồ thị ngẫu nhiên (T21): phân tầng 3 mức và 100% khớp chi phí."""
    # Sinh đồ thị ngẫu nhiên 40 node, 120 cạnh
    dict_data = random_graph_dict(seed=2026, n_nodes=40, n_edges=120)
    graph_file = tmp_path / "random_graph.json"
    graph_file.write_text(json.dumps(dict_data), encoding="utf-8")

    cmd_args = [
        "--suite", "scaling",
        "--graph", str(graph_file),
        "--pairs", "30",
        "--seed", "100",
        "--repeats", "3",
        "--run-id", "run_random",
        "--out", str(tmp_path),
    ]

    ret = main(cmd_args)
    assert ret == 0

    out_dir = tmp_path / "run_random"
    queries = read_queries_csv(out_dir / "queries.csv")
    assert len(queries) == 30

    # Đồ thị đủ lớn phải có cả 3 tầng khoảng cách
    strata = {q["stratum"] for q in queries}
    assert "ngan" in strata
    assert "trung_binh" in strata
    assert "dai" in strata

    # Đọc measurements và kiểm tra tính nhất quán
    with (out_dir / "measurements.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 60

    for q_id in range(30):
        d_row = next(r for r in rows if int(r["query_id"]) == q_id and r["algo"] == "dijkstra")
        a_row = next(r for r in rows if int(r["query_id"]) == q_id and r["algo"] == "astar")
        assert d_row["status"] == a_row["status"]
        if d_row["status"] == "ok":
            assert abs(float(d_row["cost_s"]) - float(a_row["cost_s"])) <= 1e-6 * max(1.0, float(d_row["cost_s"]))


def test_run_benchmarks_reusing_queries_csv(tmp_path: Path) -> None:
    """Tái lập benchmark bằng cách dùng lại queries.csv đã sinh trước đó."""
    main([
        "--suite", "demo",
        "--graph", str(MINI_GRAPH_PATH),
        "--pairs", "15",
        "--seed", "99",
        "--run-id", "run1",
        "--out", str(tmp_path),
    ])

    queries_file = tmp_path / "run1" / "queries.csv"
    assert queries_file.is_file()

    main([
        "--suite", "demo",
        "--graph", str(MINI_GRAPH_PATH),
        "--queries", str(queries_file),
        "--run-id", "run2",
        "--out", str(tmp_path),
    ])

    q1 = read_queries_csv(queries_file)
    q2 = read_queries_csv(tmp_path / "run2" / "queries.csv")
    assert q1 == q2, "hai lần chạy phải dùng cùng tập truy vấn"


def test_run_benchmarks_with_blocked_edges(tmp_path: Path) -> None:
    """Benchmark khi có danh sách cạnh bị chặn qua tham số --blocked."""
    ret = main([
        "--suite", "scenario",
        "--graph", str(MINI_GRAPH_PATH),
        "--pairs", "10",
        "--blocked", "0", "4",
        "--run-id", "run_blocked",
        "--out", str(tmp_path),
    ])
    assert ret == 0

    out_dir = tmp_path / "run_blocked"
    with (out_dir / "measurements.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        assert int(r["blocked_count"]) == 2


def test_run_benchmarks_scenario_un_tac_tam_a(tmp_path: Path) -> None:
    """Kiểm tra kịch bản un-tac-tam-a trên mini.json: scenario_id đúng và cost_s S->T = 100s."""
    # Tạo queries.csv chỉ chứa cặp S (0) -> T (2)
    q_file = tmp_path / "custom_queries.csv"
    write_queries_csv(q_file, [{
        "query_id": 0,
        "workload": "demo",
        "stratum": "trung_binh",
        "source": 0,
        "target": 2,
        "hav_m": 817.0,
        "delta": 0.74,
    }])

    ret = main([
        "--suite", "scenario",
        "--graph", str(MINI_GRAPH_PATH),
        "--scenario", "un-tac-tam-a",
        "--scenario-file", str(MINI_SCENARIOS_PATH),
        "--queries", str(q_file),
        "--run-id", "run_scen",
        "--out", str(tmp_path),
    ])
    assert ret == 0

    out_dir = tmp_path / "run_scen"
    with (out_dir / "measurements.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2  # 1 query × 2 algo
    for r in rows:
        assert r["scenario_id"] == "un-tac-tam-a"
        assert r["status"] == "ok"
        # Tuyến cơ sở S->A->T bị nhân đôi thành 160s, tuyến S->B->T là 100s
        assert float(r["cost_s"]) == pytest.approx(100.0)


def test_run_benchmarks_scenario_missing_fails(tmp_path: Path) -> None:
    """Kịch bản không tồn tại trong file phải báo lỗi và trả mã khác 0."""
    ret = main([
        "--suite", "scenario",
        "--graph", str(MINI_GRAPH_PATH),
        "--scenario", "khong-co",
        "--out", str(tmp_path),
    ])
    assert ret != 0, "--scenario khong-co phải trả về mã lỗi khác 0"


def test_run_benchmarks_invalid_blocked_fails(tmp_path: Path) -> None:
    """Cạnh đóng ngoài phạm vi phải báo lỗi qua validate_blocked và trả mã khác 0."""
    ret = main([
        "--suite", "scenario",
        "--graph", str(MINI_GRAPH_PATH),
        "--blocked", "9999",
        "--out", str(tmp_path),
    ])
    assert ret != 0, "--blocked ngoài biên phải trả về mã lỗi khác 0"


def test_side_m_and_l_source(tmp_path: Path) -> None:
    """Kiểm tra xác định L_m và L_source từ --side-m và bbox."""
    # 1. Có --side-m
    ret = main([
        "--suite", "demo",
        "--graph", str(MINI_GRAPH_PATH),
        "--pairs", "5",
        "--side-m", "2500.0",
        "--run-id", "run_side_m",
        "--out", str(tmp_path),
    ])
    assert ret == 0
    cfg1 = json.loads((tmp_path / "run_side_m" / "config.json").read_text(encoding="utf-8"))
    assert cfg1["sampling"]["L_source"] == "side_m"
    assert cfg1["sampling"]["L_m"] == 2500.0

    # 2. Mặc định dùng bbox (không có manifest trong fixtures)
    ret = main([
        "--suite", "demo",
        "--graph", str(MINI_GRAPH_PATH),
        "--pairs", "5",
        "--run-id", "run_bbox",
        "--out", str(tmp_path),
    ])
    assert ret == 0
    cfg2 = json.loads((tmp_path / "run_bbox" / "config.json").read_text(encoding="utf-8"))
    assert cfg2["sampling"]["L_source"] == "bbox"
    assert cfg2["sampling"]["L_m"] == pytest.approx(1098.8, rel=1e-2)


def test_cost_mismatch_raises_runtime_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Nếu thuật toán trả về chi phí không khớp, benchmark phải dừng ngay lập tức (fail-fast)."""
    import run_benchmarks
    orig_astar = run_benchmarks.astar

    def fake_astar(*args, **kwargs):
        res = orig_astar(*args, **kwargs)
        if res.cost_s is not None:
            # Tạo kết quả bị lệch chi phí cố ý
            from app.algorithms.result import SearchResult
            return SearchResult(
                status=res.status,
                cost_s=res.cost_s + 100.0,
                edge_ids=res.edge_ids,
                node_ids=res.node_ids,
                distance_m=res.distance_m,
                expanded=res.expanded,
                unique_expanded=res.unique_expanded,
                reopened=res.reopened,
                relaxations=res.relaxations,
                pushes=res.pushes,
                max_frontier=res.max_frontier,
            )
        return res

    monkeypatch.setattr(run_benchmarks, "astar", fake_astar)

    with pytest.raises(RuntimeError, match="Lỗi lệch chi phí"):
        main([
            "--suite", "demo",
            "--graph", str(MINI_GRAPH_PATH),
            "--pairs", "5",
            "--run-id", "run_fail",
            "--out", str(tmp_path),
        ])


def test_git_dirty_ignores_results_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Thư mục results/ do chính lần chạy tạo ra không làm git_dirty = True; file khác thì có."""
    import subprocess

    import run_benchmarks

    repo = tmp_path / "repo"
    repo.mkdir()
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "a.txt").write_text("a", encoding="utf-8")
    subprocess.run([*git, "-C", str(repo), "add", "a.txt"], check=True)
    subprocess.run([*git, "-C", str(repo), "commit", "-q", "-m", "init"], check=True)
    monkeypatch.setattr(run_benchmarks, "REPO_ROOT", repo)

    (repo / "results" / "20261029-0000-demo-abc1234").mkdir(parents=True)
    (repo / "results" / "20261029-0000-demo-abc1234" / "measurements.csv").write_text("x", encoding="utf-8")
    assert run_benchmarks._get_git_info()[2] is False

    (repo / "b.txt").write_text("b", encoding="utf-8")
    assert run_benchmarks._get_git_info()[2] is True

