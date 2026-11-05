"""T64: biểu đồ từ `measurements.csv` — test bằng **CSV giả sinh trong `tmp_path`** (dữ liệu THỬ,
không phải số đo thật; không ảnh/CSV nào được ghi vào repo).
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

_path = Path(__file__).resolve().parent.parent / "scripts" / "plot_results.py"
_spec = importlib.util.spec_from_file_location("plot_results", _path)
plot = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = plot          # dataclass cần thấy module trong sys.modules khi exec
_spec.loader.exec_module(plot)

# Chép nguyên văn danh sách cột của docs/EXPERIMENT_PLAN.md mục 3.3 (không lấy từ script) để test
# bắt được nếu script lệch tài liệu.
COLUMNS = [
    "run_id", "suite", "dataset_id", "size_label", "n_nodes", "n_edges", "query_id", "workload",
    "stratum", "source", "target", "hav_m", "algo", "scenario_id", "blocked_count", "status",
    "cost_s", "distance_m", "expanded", "unique_expanded", "reopened", "relaxations", "pushes",
    "max_frontier", "runtime_ns_median", "runtime_ns_min", "repeats",
]

needs_matplotlib = pytest.mark.skipif(
    importlib.util.find_spec("matplotlib") is None,
    reason="cần matplotlib (extra 'bench') để vẽ hình",
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# --- Dữ liệu giả cho E5 (tour): đúng định dạng tour_measurements.csv (E5_proposal.md mục 2) ---

TOUR_COLUMNS = [
    "run_id", "suite", "dataset_id", "set_id", "n_stops", "seed", "depot_node", "stop_nodes",
    "method", "feasible", "cost_s", "order", "matrix_ns", "order_ns", "route_ns",
]
TOUR_RUN_ID = "20261105-0800-tour-abc9999"
# order_ns mặc định theo phương án, dễ tính tay: input 2 ms, NN 4 ms, NN+2-opt 12 ms, HK 200 ms
ORDER_NS_DEFAULT = {"input": 2_000_000, "nearest_neighbor": 4_000_000,
                    "nearest_neighbor_2opt": 12_000_000, "held_karp": 200_000_000}


def make_tour_row(**values) -> dict[str, str]:
    """Một dòng tour CSV đủ 15 cột (dữ liệu THỬ, không phải số đo thật)."""
    row = dict.fromkeys(TOUR_COLUMNS, "")
    method = values.get("method", "input")
    row.update({
        "run_id": TOUR_RUN_ID,
        "suite": "tour",
        "dataset_id": "hcm-benthanh-r2000-20261024",
        "set_id": "0",
        "n_stops": "4",
        "seed": "1",
        "depot_node": "100",
        "stop_nodes": "10;11;12;13",
        "method": method,
        "feasible": "true",
        "cost_s": "100.0",
        "order": "0;1;2;3",
        "matrix_ns": "1500000",
        "order_ns": str(ORDER_NS_DEFAULT.get(method, 2_000_000)),
        "route_ns": "800000",
    })
    row.update({key: str(value) for key, value in values.items()})
    return row


def write_tour_csv(run_dir: Path, rows: list[dict[str, str]],
                   columns: list[str] | None = None) -> Path:
    """Ghi tour_measurements.csv (dữ liệu thử) vào `run_dir` và trả đường dẫn file."""
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "tour_measurements.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns or TOUR_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def tour_block(run_id: str = TOUR_RUN_ID) -> list[dict[str, str]]:
    """5 bộ với số tính tay được: 4 bộ khả thi + 1 bộ `feasible = false`.

    set0 (n=4): input 100, NN 80, NN+2-opt 60, HK 50 → Imp NN 20 %, 2-opt 40 %; Gap NN 60 %,
    2-opt 20 %, input 100 %.
    set1 (n=4): input 200, NN 170, NN+2-opt 120, HK 100 → Imp 15 %/40 %; Gap 70 %/20 %, input 100 %.
    set2 (n=6): input 150, NN 90, NN+2-opt 90, HK 90 → Imp 40 %/40 %; Gap 0 %/0 %, input 66,67 %.
    set3 (n=6): `feasible = false`, chi phí rỗng → chỉ đếm.
    set4 (n=8): input 120, NN 96, NN+2-opt 84, **thiếu held_karp** → Gap bị loại kèm đếm.
    """
    methods = ("input", "nearest_neighbor", "nearest_neighbor_2opt", "held_karp")
    scenario = {
        (4, 0): {"input": 100.0, "nearest_neighbor": 80.0, "nearest_neighbor_2opt": 60.0,
                 "held_karp": 50.0},
        (4, 1): {"input": 200.0, "nearest_neighbor": 170.0, "nearest_neighbor_2opt": 120.0,
                 "held_karp": 100.0},
        (6, 2): {"input": 150.0, "nearest_neighbor": 90.0, "nearest_neighbor_2opt": 90.0,
                 "held_karp": 90.0},
        (6, 3): {method: None for method in methods},       # bộ không khả thi
        (8, 4): {"input": 120.0, "nearest_neighbor": 96.0, "nearest_neighbor_2opt": 84.0},
    }
    rows: list[dict[str, str]] = []
    for (n_stops, set_id), costs in scenario.items():
        for method, cost in costs.items():
            rows.append(make_tour_row(run_id=run_id, set_id=set_id, n_stops=n_stops,
                                      method=method, feasible=cost is not None,
                                      cost_s="" if cost is None else cost))
    return rows


def make_row(**values) -> dict[str, str]:
    """Một dòng CSV đủ 27 cột với giá trị mặc định hợp lệ; `values` ghi đè cột cần đổi."""
    row = dict.fromkeys(COLUMNS, "")
    row.update({
        "run_id": "20261101-0900-demo-abc1234",
        "suite": "demo",
        "dataset_id": "demo-hcm",
        "size_label": "4.5km",
        "n_nodes": "1000",
        "n_edges": "2000",
        "query_id": "q1",
        "workload": "fixed trips",
        "stratum": "short",
        "source": "10",
        "target": "20",
        "hav_m": "500",
        "algo": "dijkstra",
        "scenario_id": "baseline",
        "blocked_count": "0",
        "status": "ok",
        "cost_s": "12.5",
        "distance_m": "1200",
        "expanded": "10",
        "unique_expanded": "9",
        "reopened": "0",
        "relaxations": "20",
        "pushes": "15",
        "max_frontier": "8",
        "runtime_ns_median": "1000000",
        "runtime_ns_min": "900000",
        "repeats": "5",
    })
    row.update({key: str(value) for key, value in values.items()})
    return row


def write_csv(run_dir: Path, rows: list[dict[str, str]], columns: list[str] | None = None) -> Path:
    """Ghi measurements.csv (dữ liệu thử) vào `run_dir` và trả đường dẫn file."""
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "measurements.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns or COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def demo_rows(run_id: str = "20261101-0900-demo-abc1234",
              offset: int = 0) -> list[dict[str, str]]:
    """E2 giả: 4 chuyến × 3 tầng × 2 thuật toán; `offset` dịch `expanded` cho lần chạy thứ hai."""
    rows: list[dict[str, str]] = []
    for stratum in ("dai", "ngan", "trung_binh"):        # cố ý xáo: hình phải tự sắp lại
        for index in range(4):
            for algo, expanded in (("dijkstra", 10 + index + offset),
                                   ("astar", 4 + index + offset)):
                rows.append(make_row(run_id=run_id, query_id=f"{stratum}-{index}",
                                     stratum=stratum, algo=algo, expanded=expanded))
    return rows


def scaling_rows(sizes: tuple[int, ...] = (1200, 4800, 10800),
                 run_id: str = "20261102-1000-scaling-def5678") -> list[dict[str, str]]:
    """E3 giả: mỗi kích thước 2 chuyến dùng lại y hệt, chỉ workload "fixed trips"."""
    rows: list[dict[str, str]] = []
    for size in sizes:
        for index in range(2):
            for algo, expanded in (("dijkstra", size // 10), ("astar", size // 25)):
                rows.append(make_row(run_id=run_id, suite="scaling",
                                     dataset_id="hcm-scaling", size_label=f"{size}",
                                     n_nodes=size, query_id=f"trip-{index}", algo=algo,
                                     expanded=expanded, runtime_ns_median=1000000 + size))
    return rows


def assert_png(path: Path) -> None:
    """File tồn tại, nằm đúng thư mục, là PNG thật (đọc chữ ký 8 byte đầu)."""
    assert path.is_file()
    assert path.stat().st_size > 1000
    assert path.read_bytes()[:8] == PNG_MAGIC


# --- Đọc CSV ---

def test_read_measurements_parses_numbers_and_units(tmp_path):
    write_csv(tmp_path, [make_row(expanded=42, runtime_ns_median=2500000, n_nodes=1234)])
    rows = plot.read_measurements(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row.expanded == 42 and row.n_nodes == 1234
    assert row.runtime_ms == pytest.approx(2.5)          # ns → ms
    assert row.suite == "demo" and row.algo == "dijkstra"


def test_missing_column_is_rejected(tmp_path):
    columns = [c for c in COLUMNS if c != "expanded"]
    write_csv(tmp_path, [make_row()], columns=columns)
    with pytest.raises(ValueError, match="thiếu cột.*expanded"):
        plot.read_measurements(tmp_path)


def test_non_numeric_cell_is_rejected(tmp_path):
    write_csv(tmp_path, [make_row(expanded="không-phải-số")])
    with pytest.raises(ValueError, match="expanded.*không phải số"):
        plot.read_measurements(tmp_path)


def test_pair_ratios_skips_zero_and_incomplete_pairs(tmp_path):
    write_csv(tmp_path, [
        make_row(query_id="q0", algo="dijkstra", expanded=0),            # mẫu số 0: bỏ
        make_row(query_id="q0", algo="astar", expanded=5),
        make_row(query_id="q1", algo="dijkstra", expanded=10),           # thiếu A*: bỏ
        make_row(query_id="q2", algo="dijkstra", expanded=10),
        make_row(query_id="q2", algo="astar", expanded=5),
    ])
    rows = plot.read_measurements(tmp_path)
    ratios = plot.pair_ratios(rows, ("run_id", "workload", "n_nodes", "query_id"))
    assert ratios == {("20261101-0900-demo-abc1234", "fixed trips", 1000, "q2"): 0.5}


# --- Vẽ hình ---

@needs_matplotlib
def test_demo_run_creates_both_e2_figures(tmp_path):
    write_csv(tmp_path, demo_rows())
    report = plot.plot_run(tmp_path)
    assert set(report.created) == {"fig_e2_expanded_box.png", "fig_e2_expanded_scatter.png"}
    for name, path in report.created.items():
        assert path.parent == tmp_path
        assert_png(path)
        caption = report.captions[name]
        assert "run_id: 20261101-0900-demo-abc1234" in caption
        assert "số cặp: 12" in caption                      # 3 tầng × 4 chuyến
        assert "dataset_id: demo-hcm" in caption


@needs_matplotlib
def test_three_sizes_create_both_scaling_figures(tmp_path):
    write_csv(tmp_path, scaling_rows())
    report = plot.plot_run(tmp_path)
    assert set(report.created) == {"fig_e3_expanded_runtime.png", "fig_e3_ratio_by_size.png"}
    for name, path in report.created.items():
        assert_png(path)
        assert "số cặp: 6" in report.captions[name]          # 3 kích thước × 2 chuyến
        assert "dataset_id: hcm-scaling" in report.captions[name]
    assert "suite demo" in report.skipped["fig_e2_expanded_box.png"]
    assert "suite scenario" in report.skipped["fig_e4_ratio_by_scenario.png"]


@needs_matplotlib
def test_single_size_skips_line_charts_with_reason(tmp_path):
    write_csv(tmp_path, scaling_rows(sizes=(1200,)))
    report = plot.plot_run(tmp_path)
    assert report.created == {}
    for name in ("fig_e3_expanded_runtime.png", "fig_e3_ratio_by_size.png"):
        reason = report.skipped[name]
        assert "1 kích thước" in reason and "ít nhất 2" in reason


@needs_matplotlib
def test_three_scaling_runs_merge_into_e3_figures(tmp_path):
    # T60 đo một đồ thị mỗi lần chạy: 3 kích thước = 3 thư mục, mỗi thư mục 1 giá trị |V|.
    runs = []
    for size in (1200, 4800, 10800):
        run_id = f"20261102-1000-scaling-{size:05d}"
        write_csv(tmp_path / run_id, scaling_rows(sizes=(size,), run_id=run_id))
        runs.append(tmp_path / run_id)
    out = tmp_path / "figs"
    report = plot.plot_run(runs, out)
    assert set(report.created) == {"fig_e3_expanded_runtime.png", "fig_e3_ratio_by_size.png"}
    for name, path in report.created.items():
        assert path.parent == out and path.is_file()        # ghi vào --out, không vào 1 run_dir
        assert_png(path)
        caption = report.captions[name]
        assert "số cặp: 6" in caption                       # 3 kích thước × 2 chuyến
        for run_id in (f"20261102-1000-scaling-{s:05d}" for s in (1200, 4800, 10800)):
            assert run_id in caption                        # chú thích ghi mọi run_id đã gộp
    assert out.is_dir()


@needs_matplotlib
def test_two_demo_runs_with_same_query_ids_are_not_merged(tmp_path):
    # run_benchmarks.py đánh query_id từ 0 mỗi lần chạy: gộp hai lần chạy thì query_id trùng nhau.
    first, second = tmp_path / "run-a", tmp_path / "run-b"
    write_csv(first, demo_rows(run_id="20261107-0800-demo-aaaaaaa"))
    write_csv(second, demo_rows(run_id="20261107-0900-demo-bbbbbbb", offset=100))
    out = tmp_path / "figs"
    report = plot.plot_run([first, second], out)
    for name in ("fig_e2_expanded_box.png", "fig_e2_expanded_scatter.png"):
        assert_png(out / name)
        caption = report.captions[name]
        assert "số cặp: 24" in caption                       # 12 cặp mỗi lần chạy, không ghi đè
        assert "20261107-0800-demo-aaaaaaa" in caption
        assert "20261107-0900-demo-bbbbbbb" in caption


def test_pair_ratios_keeps_pairs_of_two_runs_with_same_size(tmp_path):
    runs = ("20261107-1000-scaling-aaaaaaa", "20261107-1100-scaling-bbbbbbb")
    for run_id in runs:
        write_csv(tmp_path / run_id, scaling_rows(sizes=(4800,), run_id=run_id))
    rows: list[plot.Row] = []
    for run_id in runs:
        rows.extend(plot.read_measurements(tmp_path / run_id))
    ratios = plot.pair_ratios(rows, ("run_id", "workload", "n_nodes", "query_id"))
    assert len(ratios) == 4                                  # 2 lần chạy × 2 chuyến, không trộn
    assert {key[0] for key in ratios} == set(runs)


@needs_matplotlib
def test_two_scaling_runs_same_size_count_all_pairs(tmp_path):
    # Hai lần chạy cùng |V| cộng một kích thước khác: hình E3 phải đếm đủ cặp của cả ba.
    runs = (("20261107-1000-scaling-aaaaaaa", 4800), ("20261107-1100-scaling-bbbbbbb", 4800),
            ("20261107-1200-scaling-ccccccc", 9600))
    for run_id, size in runs:
        write_csv(tmp_path / run_id, scaling_rows(sizes=(size,), run_id=run_id))
    out = tmp_path / "figs"
    report = plot.plot_run([tmp_path / run_id for run_id, _ in runs], out)
    for name in ("fig_e3_expanded_runtime.png", "fig_e3_ratio_by_size.png"):
        assert_png(out / name)
        assert "số cặp: 6" in report.captions[name]          # (2 + 2 + 2) cặp


def test_stratum_order_is_fixed_and_unknown_last():
    assert plot.order_strata(["dai", "ngan", "khac", "trung_binh"]) == [
        "ngan", "trung_binh", "dai", "khac"]
    assert plot.order_strata(["trung_binh", "ngan", "trung_binh"]) == ["ngan", "trung_binh"]
    assert plot.stratum_label("ngan") == "ngắn (δ<0,2)"
    assert plot.stratum_label("dai") == "dài (δ≥0,5)"
    assert plot.stratum_label("khac") == "khac"             # tầng lạ giữ nguyên giá trị CSV


@needs_matplotlib
def test_scenario_run_creates_ratio_box(tmp_path):
    rows = [make_row(run_id="20261103-0800-scenario-aaa1111", suite="scenario",
                     dataset_id="demo-hcm", workload="", stratum="", scenario_id=scenario,
                     query_id=f"trip-{index}", algo=algo, expanded=expanded)
            for scenario in ("baseline", "peak-center")
            for index in range(2)
            for algo, expanded in (("dijkstra", 20), ("astar", 12))]
    write_csv(tmp_path, rows)
    report = plot.plot_run(tmp_path)
    assert set(report.created) == {"fig_e4_ratio_by_scenario.png"}
    caption = report.captions["fig_e4_ratio_by_scenario.png"]
    assert "số cặp: 4" in caption and "run_id: 20261103-0800-scenario-aaa1111" in caption


@needs_matplotlib
def test_header_only_csv_skips_all_figures_without_error(tmp_path):
    write_csv(tmp_path, [])
    report = plot.plot_run(tmp_path)
    assert report.created == {}
    assert len(report.skipped) == 6           # E2 ×2, E3 ×2, E4, E5
    assert "tour_measurements.csv" in report.skipped["fig_e5_tour.png"]
    assert all(report.skipped.values())


# --- CLI ---

@needs_matplotlib
def test_cli_reports_created_and_skipped(tmp_path, capsys):
    write_csv(tmp_path, demo_rows())
    code = plot.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "đã tạo" in out and "fig_e2_expanded_box.png" in out
    assert "bỏ qua fig_e3_expanded_runtime.png" in out and "suite scaling" in out


@needs_matplotlib
def test_cli_out_dir_receives_merged_figures(tmp_path, capsys):
    runs = []
    for size in (1200, 4800, 10800):
        run_id = f"20261102-1000-scaling-{size:05d}"
        write_csv(tmp_path / run_id, scaling_rows(sizes=(size,), run_id=run_id))
        runs.append(str(tmp_path / run_id))
    out = tmp_path / "figs"
    code = plot.main([*runs, "--out", str(out)])
    printed = capsys.readouterr().out
    assert code == 0
    assert (out / "fig_e3_expanded_runtime.png").is_file()
    assert (out / "fig_e3_ratio_by_size.png").is_file()
    assert "số cặp: 6" in printed


def test_cli_requires_out_when_merging_many_dirs(tmp_path, capsys):
    first, second = tmp_path / "run-a", tmp_path / "run-b"
    write_csv(first, scaling_rows(sizes=(1200,)))
    write_csv(second, scaling_rows(sizes=(4800,)))
    code = plot.main([str(first), str(second)])
    assert code == 2
    assert "--out" in capsys.readouterr().err

    with pytest.raises(ValueError, match="--out"):           # cùng luật ở tầng hàm
        plot.plot_run([first, second])
    assert not list(first.glob("fig_*.png")) and not list(second.glob("fig_*.png"))


def test_cli_rejects_wrong_usage_and_missing_file(tmp_path, capsys):
    assert plot.main([]) == 2
    assert "cách dùng" in capsys.readouterr().err

    assert plot.main(["--out"]) == 2                          # thiếu giá trị
    assert "--out" in capsys.readouterr().err

    missing = tmp_path / "khong-co"
    assert plot.main([str(missing)]) == 1
    assert "không thấy" in capsys.readouterr().err


@needs_matplotlib
def test_single_dir_still_accepts_str_and_writes_beside_csv(tmp_path):
    write_csv(tmp_path, demo_rows())
    report = plot.plot_run(str(tmp_path))                     # một str vẫn chạy như cũ
    assert report.created
    assert all(path.parent == tmp_path for path in report.created.values())


# --- E5 (tour) ---

def test_read_tour_measurements_parses_and_tolerates_missing_file(tmp_path):
    assert plot.read_tour_measurements(tmp_path) == []        # không có file → rỗng, không lỗi
    write_tour_csv(tmp_path, [make_tour_row(method="nearest_neighbor", feasible="false",
                                            cost_s="", order_ns="4000000")])
    row = plot.read_tour_measurements(tmp_path)[0]
    assert row.method == "nearest_neighbor" and row.feasible is False and row.cost_s is None
    assert row.n_stops == 4 and row.order_ms == pytest.approx(4.0)   # ns → ms


def test_read_tour_rejects_bad_cell_missing_column_and_bad_boolean(tmp_path):
    write_tour_csv(tmp_path / "hong-so", [make_tour_row(cost_s="khong-phai-so")])
    with pytest.raises(ValueError, match="cost_s.*không phải số"):
        plot.read_tour_measurements(tmp_path / "hong-so")

    columns = [c for c in TOUR_COLUMNS if c != "order_ns"]
    write_tour_csv(tmp_path / "thieu-cot", [make_tour_row()], columns=columns)
    with pytest.raises(ValueError, match="thiếu cột.*order_ns"):
        plot.read_tour_measurements(tmp_path / "thieu-cot")

    write_tour_csv(tmp_path / "hong-feasible", [make_tour_row(feasible="co-le")])
    with pytest.raises(ValueError, match="feasible.*không phải true/false"):
        plot.read_tour_measurements(tmp_path / "hong-feasible")


def test_tour_stats_are_per_set_hand_computed(tmp_path):
    write_tour_csv(tmp_path, tour_block())
    stats = plot.tour_stats(plot.read_tour_measurements(tmp_path))
    # Improvement tính từng bộ rồi mới gom: set0 20 %, set1 15 % → median của [20, 15]
    assert stats.improvements[(4, "nearest_neighbor")] == pytest.approx([20.0, 15.0])
    assert stats.improvements[(4, "nearest_neighbor_2opt")] == pytest.approx([40.0, 40.0])
    assert stats.improvements[(8, "nearest_neighbor")] == pytest.approx([20.0])
    assert stats.gaps[(4, "input")] == pytest.approx([100.0, 100.0])
    assert stats.gaps[(4, "nearest_neighbor")] == pytest.approx([60.0, 70.0])
    assert stats.gaps[(6, "input")] == pytest.approx([200.0 / 3.0])   # (150−90)/90
    assert "input" not in {m for (_n, m) in stats.improvements}        # mốc không có Improvement
    assert "held_karp" not in {m for (_n, m) in stats.gaps}           # mốc không có Gap
    assert stats.n_total == {4: 2, 6: 2, 8: 1} and stats.n_feasible == {4: 2, 6: 1, 8: 1}
    assert stats.missing_held_karp == 3        # bộ n=8 thiếu held_karp: input, NN, NN+2-opt
    assert stats.missing_input == 0
    assert stats.order_ms[(4, "nearest_neighbor")] == pytest.approx([4.0, 4.0])


def test_tour_stats_counts_pairs_missing_a_method(tmp_path):
    write_tour_csv(tmp_path, [make_tour_row(set_id=1, method="nearest_neighbor", cost_s=80.0),
                              make_tour_row(set_id=1, method="held_karp", cost_s=50.0)])
    stats = plot.tour_stats(plot.read_tour_measurements(tmp_path))
    assert (4, "nearest_neighbor") not in stats.improvements        # thiếu `input` → loại
    assert stats.gaps[(4, "nearest_neighbor")] == pytest.approx([60.0])
    assert stats.missing_input == 1 and stats.missing_held_karp == 0


@needs_matplotlib
def test_tour_only_dir_creates_e5_and_skips_measurement_figures(tmp_path):
    write_tour_csv(tmp_path, tour_block())
    report = plot.plot_run(tmp_path)                          # thư mục chỉ có tour CSV vẫn chạy
    assert set(report.created) == {"fig_e5_tour.png"}
    path = report.created["fig_e5_tour.png"]
    assert path.parent == tmp_path
    assert_png(path)
    caption = report.captions["fig_e5_tour.png"]
    assert f"run_id: {TOUR_RUN_ID}" in caption
    assert "số bộ khả thi: 4/5" in caption                    # set3 `feasible = false` chỉ đếm
    assert "dataset_id: hcm-benthanh-r2000-20261024" in caption
    assert "suite demo" in report.skipped["fig_e2_expanded_box.png"]


@needs_matplotlib
def test_mixed_dir_creates_e2_and_e5(tmp_path):
    write_csv(tmp_path, demo_rows())
    write_tour_csv(tmp_path, tour_block())
    report = plot.plot_run(tmp_path)
    assert {"fig_e2_expanded_box.png", "fig_e2_expanded_scatter.png",
            "fig_e5_tour.png"} <= set(report.created)
    assert_png(report.created["fig_e5_tour.png"])
