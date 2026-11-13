"""Kiểm tra script tổng hợp kết quả benchmark (T65, issue #31).

Tiêu chuẩn: docs/EXPERIMENT_PLAN.md mục 3.2, 3.3 và 9 — bảng E2/E3/E4 bằng Markdown, r và s tính
từng cặp rồi mới lấy median, gộp nhiều lần chạy theo `run_id`, mỗi bảng có dòng nguồn.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import summarize_results as summary

RUN_ID = "20261029-1552-demo-abc1234"

# --- Helper E5 (tour): tour_measurements.csv đúng định dạng docs/tasks/T74-tour-benchmark.md ---

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


def write_tour(run_dir: Path, rows: list[dict[str, str]], *, run_id: str = TOUR_RUN_ID,
               python: str = "3.11.9", commit: str = "def5678", dirty: bool = False) -> Path:
    """Ghi tour_measurements.csv + env.json + config.json vào `run_dir` (chỉ dữ liệu tour)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "tour_measurements.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TOUR_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (run_dir / "env.json").write_text(json.dumps({
        "python_version": python, "git_commit": commit, "git_dirty": dirty,
    }), encoding="utf-8")
    (run_dir / "config.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    return run_dir


def tour_scenario_rows() -> list[dict[str, str]]:
    """5 bộ với số tính tay được (cùng một kịch bản với test E5 của plot_results).

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
            rows.append(make_tour_row(run_id=TOUR_RUN_ID, set_id=set_id, n_stops=n_stops,
                                      method=method, feasible=cost is not None,
                                      cost_s="" if cost is None else cost))
    return rows


def make_row(*, algo: str, expanded: int, runtime_ms: float, query_id: str = "0",
             stratum: str = "", suite: str = "demo", run_id: str = RUN_ID,
             status: str = "ok", cost_s: float | None = 100.0, source: int = 10,
             target: int = 20, n_nodes: int = 1000, n_edges: int = 2000,
             dataset_id: str = "demo-hcm", size_label: str = "demo",
             workload: str = "demo", scenario_id: str = "baseline") -> dict[str, str]:
    """Một dòng measurements.csv giả với đủ 27 cột (dữ liệu thử, không phải kết quả thật)."""
    return {
        "run_id": run_id,
        "suite": suite,
        "dataset_id": dataset_id,
        "size_label": size_label,
        "n_nodes": str(n_nodes),
        "n_edges": str(n_edges),
        "query_id": str(query_id),
        "workload": workload,
        "stratum": stratum,
        "source": str(source),
        "target": str(target),
        "hav_m": "250.0",
        "algo": algo,
        "scenario_id": scenario_id,
        "blocked_count": "0",
        "status": status,
        "cost_s": "" if cost_s is None else str(cost_s),
        "distance_m": "800.0",
        "expanded": str(expanded),
        "unique_expanded": str(expanded),
        "reopened": "0",
        "relaxations": "0",
        "pushes": "0",
        "max_frontier": "0",
        "runtime_ns_median": str(int(round(runtime_ms * 1e6))),
        "runtime_ns_min": "0",
        "repeats": "5",
    }


def write_run(run_dir: Path, rows: list[dict[str, str]], *, run_id: str = RUN_ID,
              python: str = "3.14.4 (main, Oct 2026)", commit: str = "abc1234",
              dirty: bool = False) -> Path:
    """Ghi một thư mục kết quả tối thiểu: measurements.csv + env.json + config.json."""
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "measurements.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=summary.MEASUREMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    (run_dir / "env.json").write_text(json.dumps({
        "python_version": python, "git_commit": commit, "git_dirty": dirty,
    }), encoding="utf-8")
    (run_dir / "config.json").write_text(json.dumps({
        "run_id": run_id, "suite": "demo",
    }), encoding="utf-8")
    return run_dir


def demo_rows(run_id: str = RUN_ID) -> list[dict[str, str]]:
    """3 cặp E2 (mỗi tầng một cặp) với số tính tay được.

    Dijkstra: expanded 10/20/40, ms 1/2/4 · A*: expanded 5/10/30, ms 0,5/1/3.
    """
    rows: list[dict[str, str]] = []
    spec = (("ngan", 10, 5, 1.0, 0.5), ("trung_binh", 20, 10, 2.0, 1.0),
            ("dai", 40, 30, 4.0, 3.0))
    for index, (stratum, exp_d, exp_a, ms_d, ms_a) in enumerate(spec):
        rows.append(make_row(algo="dijkstra", expanded=exp_d, runtime_ms=ms_d,
                             query_id=str(index), stratum=stratum, run_id=run_id,
                             source=10 + index, target=20 + index))
        rows.append(make_row(algo="astar", expanded=exp_a, runtime_ms=ms_a,
                             query_id=str(index), stratum=stratum, run_id=run_id,
                             source=10 + index, target=20 + index))
    return rows


def cells_by_key(section: summary.Section) -> dict[tuple[str, str], tuple[str, ...]]:
    """Bảng E2 → {(thuật toán, tầng): các ô còn lại} để kiểm từng ô."""
    assert section.table is not None, section.skipped
    return {(row[0], row[1]): row[2:] for row in section.table.rows}


def single_table_row(section: summary.Section) -> tuple[str, ...]:
    assert section.table is not None, section.skipped
    assert len(section.table.rows) == 1, section.table.rows
    return section.table.rows[0]


# --- E2 ---

def test_e2_table_cells_hand_computed(tmp_path):
    run = write_run(tmp_path / "run", demo_rows())
    rows = summary.read_rows(run)
    section = summary.e2_section(rows, [summary.read_meta(run)])

    cells = cells_by_key(section)
    assert cells[("Dijkstra", "ngắn (δ<0,2)")] == ("1", "1", "10", "—")
    assert cells[("A*", "ngắn (δ<0,2)")] == ("0,5", "0,5", "5", "100,0 %")
    assert cells[("Dijkstra", "trung bình")] == ("2", "2", "20", "—")
    assert cells[("A*", "trung bình")] == ("1", "1", "10", "100,0 %")
    assert cells[("Dijkstra", "tất cả")] == ("2", "3,8", "20", "—")       # p95 của [1, 2, 4]
    assert cells[("A*", "tất cả")] == ("1", "2,8", "10", "100,0 %")       # p95 của [0,5; 1; 3]

    assert section.table.headers == ("Thuật toán", "Tầng", "Median ms", "p95 ms",
                                     "Median expanded", "Khớp chi phí")
    assert RUN_ID in section.source
    assert "demo-hcm" in section.source
    assert "· 3 cặp" in section.source
    assert "Python 3.14.4" in section.source
    assert "git abc1234" in section.source and "dirty: false" in section.source


def test_e2_cost_mismatch_is_reported(tmp_path):
    rows = demo_rows()
    for row in rows:
        if row["algo"] == "astar" and row["query_id"] == "2":
            row["cost_s"] = "200.0"                    # lệch hẳn so với Dijkstra 100.0
    run = write_run(tmp_path / "run", rows)
    section = summary.e2_section(summary.read_rows(run), [summary.read_meta(run)])
    cells = cells_by_key(section)
    assert cells[("A*", "dài (δ≥0,5)")][3] == "0,0 %"
    assert cells[("A*", "tất cả")][3] == "66,7 %"       # 2/3 cặp khớp


# --- E3 ---

def scaling_rows() -> list[dict[str, str]]:
    """2 cặp cùng |V|: r = 0,5 và 0,25 → median 0,375 (không phải 5/15 = 0,333)."""
    common = {"suite": "scaling", "size_label": "1 km", "n_nodes": 1000, "n_edges": 2000,
              "cost_s": 10.0}
    return [
        make_row(algo="dijkstra", expanded=10, runtime_ms=2.0, query_id="0", **common),
        make_row(algo="astar", expanded=5, runtime_ms=1.0, query_id="0", **common),
        make_row(algo="dijkstra", expanded=20, runtime_ms=3.0, query_id="1", **common),
        make_row(algo="astar", expanded=5, runtime_ms=1.5, query_id="1", **common),
    ]


def test_e3_ratio_is_median_of_pair_ratios(tmp_path):
    run = write_run(tmp_path / "run", scaling_rows())
    section = summary.e3_section(summary.read_rows(run), [summary.read_meta(run)])
    row = single_table_row(section)
    assert row == ("1 km", "1000", "2000", "demo", "0,375", "2", "2,5", "1,25")
    assert section.table.headers == ("Kích thước", "|V|", "|E|", "Workload", "Median r",
                                     "Median s", "Median ms Dijkstra", "Median ms A*")
    assert "| Kích thước | \\|V\\| | \\|E\\| |" in section.table.to_markdown()
    # Tứ phân vị của r = [0,25; 0,5] là [0,3125; 0,4375] (nội suy tuyến tính)
    assert any("0,3125; 0,4375" in note for note in section.table.notes)


def test_e3_skips_pairs_with_zero_expanded_dijkstra(tmp_path):
    rows = scaling_rows()
    rows[0]["expanded"] = "0"                          # cặp 0: expanded_D = 0 → loại khỏi r
    run = write_run(tmp_path / "run", rows)
    section = summary.e3_section(summary.read_rows(run), [summary.read_meta(run)])
    row = single_table_row(section)
    assert row[4] == "0,25"                            # chỉ còn r của cặp 1
    assert any("Bỏ 1 cặp có expanded_D = 0" in note for note in section.table.notes)


# --- Gộp nhiều lần chạy ---

def test_two_runs_with_same_query_ids_are_merged(tmp_path):
    first = write_run(tmp_path / "a", demo_rows("20261029-1552-demo-aaaaaaa"),
                      run_id="20261029-1552-demo-aaaaaaa")
    second_rows = demo_rows("20261029-1600-demo-bbbbbbb")
    for row in second_rows:                            # dịch số để phát hiện ghi đè
        row["expanded"] = str(int(row["expanded"]) + 100)
    second = write_run(tmp_path / "b", second_rows, run_id="20261029-1600-demo-bbbbbbb")

    rows = summary.read_rows(first) + summary.read_rows(second)
    metas = [summary.read_meta(first), summary.read_meta(second)]
    section = summary.e2_section(rows, metas)
    cells = cells_by_key(section)
    assert "· 6 cặp" in section.source
    assert "20261029-1552-demo-aaaaaaa" in section.source
    assert "20261029-1600-demo-bbbbbbb" in section.source
    assert cells[("Dijkstra", "tất cả")][2] == "75"     # median của 10/20/40 và 110/120/140


# --- E4 ---

def e4_rows() -> list[dict[str, str]]:
    """2 cặp có baseline 100/200, kịch bản 150/300 → tăng 50 %; r = 0,8."""
    rows: list[dict[str, str]] = []
    for index, (base, cost) in enumerate(((100.0, 150.0), (200.0, 300.0))):
        common = {"query_id": str(index), "source": 30 + index, "target": 40 + index}
        rows.append(make_row(algo="dijkstra", expanded=10, runtime_ms=2.0, cost_s=base, **common))
        rows.append(make_row(algo="astar", expanded=5, runtime_ms=1.0, cost_s=base, **common))
        rows.append(make_row(algo="dijkstra", expanded=10, runtime_ms=3.0, cost_s=cost,
                             suite="scenario", scenario_id="peak-center", **common))
        rows.append(make_row(algo="astar", expanded=8, runtime_ms=2.0, cost_s=cost,
                             suite="scenario", scenario_id="peak-center", **common))
    return rows


def test_e4_uses_baseline_for_cost_increase(tmp_path):
    run = write_run(tmp_path / "run", e4_rows())
    section = summary.e4_section(summary.read_rows(run), [summary.read_meta(run)])
    row = single_table_row(section)
    assert row == ("peak-center", "—", "50,0 %", "0,8", "100,0 %")
    assert section.table.headers == ("Kịch bản", "% đổi tuyến", "Median % tăng chi phí",
                                     "Median r", "Tỉ lệ còn đường")
    assert any("% đổi tuyến" in note for note in section.table.notes)


def test_e4_without_baseline_leaves_cost_increase_empty(tmp_path):
    rows = [row for row in e4_rows() if row["suite"] == "scenario"]
    run = write_run(tmp_path / "run", rows)
    section = summary.e4_section(summary.read_rows(run), [summary.read_meta(run)])
    row = single_table_row(section)
    assert row[2] == "—"
    assert any("không có mốc `baseline`" in note for note in section.table.notes)


# --- E5 (tour) ---

def test_e5_table_cells_hand_computed(tmp_path):
    run = write_tour(tmp_path / "run", tour_scenario_rows())
    section = summary.e5_section(summary.read_tour_rows(run), [summary.read_meta(run)])
    assert section.table is not None, section.skipped
    # median/Tứ phân vị tính từng bộ rồi mới gom; sắp theo n_stops rồi theo phương án
    assert section.table.rows == (
        ("4", "thứ tự nhập", "—", "—", "100", "[100; 100]", "2", "2/2"),
        ("4", "NN", "17,5", "[16,25; 18,75]", "65", "[62,5; 67,5]", "4", "2/2"),
        ("4", "NN + 2-opt", "40", "[40; 40]", "20", "[20; 20]", "12", "2/2"),
        ("4", "Held–Karp", "—", "—", "—", "—", "200", "2/2"),
        ("6", "thứ tự nhập", "—", "—", "66,67", "—", "2", "1/2"),
        ("6", "NN", "40", "—", "0", "—", "4", "1/2"),
        ("6", "NN + 2-opt", "40", "—", "0", "—", "12", "1/2"),
        ("6", "Held–Karp", "—", "—", "—", "—", "200", "1/2"),
        ("8", "thứ tự nhập", "—", "—", "—", "—", "2", "1/1"),
        ("8", "NN", "20", "—", "—", "—", "4", "1/1"),
        ("8", "NN + 2-opt", "30", "—", "—", "—", "12", "1/1"),
    )
    assert section.table.headers == ("Điểm giao", "Phương án", "Median Improvement %",
                                     "IQR Improvement %", "Median Gap %", "IQR Gap %",
                                     "Median order_ms", "Bộ khả thi")
    assert "run_id `20261105-0800-tour-abc9999`" in section.source
    assert "· 5 bộ ·" in section.source
    assert "Python 3.11.9" in section.source and "git def5678" in section.source
    # ghi chú: 1 bộ không khả thi + 3 (bộ, phương án) n=8 thiếu held_karp bị bỏ khỏi Gap
    notes = section.table.notes
    assert any("Bỏ 1 bộ có `feasible = false`" in note for note in notes)
    assert any("3 bộ–phương án bị bỏ khỏi Gap vì thiếu dòng `held_karp`" in note for note in notes)
    assert "C_input" in section.table.formulas and "C_held_karp" in section.table.formulas


def test_e5_skipped_without_tour_csv_and_other_sections_unchanged(tmp_path):
    run = write_run(tmp_path / "run", demo_rows())
    section = summary.e5_section(summary.read_tour_rows(run), [summary.read_meta(run)])
    assert section.table is None and "tour_measurements.csv" in section.skipped
    rows = summary.read_rows(run)
    metas = [summary.read_meta(run)]
    text = summary.render(rows, metas)
    assert "Bỏ qua: không có dòng nào thuộc tour_measurements.csv (E5)." in text
    assert "## E2 — A* vs Dijkstra trên vùng demo" in text          # bảng cũ vẫn như trước


def test_e5_missing_input_is_excluded_and_counted(tmp_path):
    run = write_tour(tmp_path / "run", [
        make_tour_row(set_id=0, method="nearest_neighbor", cost_s=80.0),
        make_tour_row(set_id=0, method="held_karp", cost_s=50.0),
    ])
    section = summary.e5_section(summary.read_tour_rows(run), [summary.read_meta(run)])
    assert section.table.rows == (
        ("4", "NN", "—", "—", "60", "—", "4", "1/1"),
        ("4", "Held–Karp", "—", "—", "—", "—", "200", "1/1"),
    )
    assert any("1 bộ–phương án bị bỏ khỏi Improvement vì thiếu dòng `input`" in note
               for note in section.table.notes)


def test_tour_only_dir_is_accepted_by_cli(tmp_path, capsys):
    run = write_tour(tmp_path / "run", tour_scenario_rows())
    assert summary.main([str(run)]) == 0
    out = capsys.readouterr().out
    assert "## E5 — Tour: Improvement và Gap theo số điểm giao" in out
    assert "| Điểm giao | Phương án | Median Improvement % |" in out
    assert "Bỏ qua: không có dòng nào thuộc suite demo (E2)." in out   # không có measurements.csv


def test_inverted_row_order_still_sorts_by_n_stops(tmp_path):
    # n_stops xuất hiện không theo thứ tự trong CSV (ngược): bảng vẫn sắp 4 → 6
    rows = list(reversed(tour_scenario_rows()))
    run = write_tour(tmp_path / "run", rows)
    section = summary.e5_section(summary.read_tour_rows(run), [summary.read_meta(run)])
    sizes = [row[0] for row in section.table.rows]
    assert sizes == sorted(sizes, key=int) and sizes[0] == "4"


# --- Lỗi dữ liệu và CLI ---

def test_read_rows_rejects_missing_column_bad_number_and_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError, match="measurements.csv"):
        summary.read_rows(tmp_path / "khong-co")

    run = write_run(tmp_path / "thieu-cot", demo_rows())
    csv_path = run / "measurements.csv"
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    csv_path.write_text("\n".join(line.replace(",expanded,", ",") for line in lines) + "\n",
                        encoding="utf-8")
    with pytest.raises(ValueError, match="thiếu cột expanded"):
        summary.read_rows(run)

    broken = write_run(tmp_path / "hong-so", demo_rows())
    text = (broken / "measurements.csv").read_text(encoding="utf-8")
    (broken / "measurements.csv").write_text(
        text.replace(",1000,2000,", ",khong-phai-so,2000,", 1), encoding="utf-8")
    with pytest.raises(ValueError, match="không phải số"):
        summary.read_rows(broken)

    bad_env = write_run(tmp_path / "env-hong", demo_rows())
    (bad_env / "env.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="object JSON"):
        summary.read_meta(bad_env)


def test_missing_suites_are_skipped_with_reason(tmp_path):
    run = write_run(tmp_path / "run", demo_rows())
    rows = summary.read_rows(run)
    metas = [summary.read_meta(run)]
    e3 = summary.e3_section(rows, metas)
    e4 = summary.e4_section(rows, metas)
    assert e3.table is None and "suite scaling" in e3.skipped
    assert e4.table is None and "suite scenario" in e4.skipped
    text = summary.render(rows, metas)
    assert "Bỏ qua: không có dòng nào thuộc suite scaling (E3)." in text
    assert "Bỏ qua: không có dòng nào thuộc suite scenario (E4)." in text


def test_cli_prints_markdown_and_exit_codes(tmp_path, capsys):
    run = write_run(tmp_path / "run", demo_rows())
    assert summary.main([str(run)]) == 0
    out = capsys.readouterr().out
    assert "# Tổng hợp kết quả benchmark" in out
    assert "## E2 — A* vs Dijkstra trên vùng demo" in out
    assert "| Thuật toán | Tầng | Median ms | p95 ms | Median expanded | Khớp chi phí |" in out
    assert f"Nguồn: run_id `{RUN_ID}`" in out

    assert summary.main([]) == 2
    assert "cách dùng" in capsys.readouterr().err
    assert summary.main(["--khong-phai-thu-muc"]) == 2
    assert summary.main([str(tmp_path / "thieu")]) == 1
    assert "không thấy" in capsys.readouterr().err
    assert summary.main(["--help"]) == 0
    assert "summarize_results.py" in capsys.readouterr().out


def test_duplicate_directory_argument_is_counted_once(tmp_path, capsys):
    run = write_run(tmp_path / "run", demo_rows())
    assert summary.main([str(run), str(run)]) == 0
    assert capsys.readouterr().out.count("· 3 cặp") == 1


def test_duplicate_run_id_warns_on_stderr(tmp_path, capsys):
    # run_id chỉ có phút nên hai lần chạy trong cùng phút dễ trùng: phải cảnh báo, không im lặng
    first = write_run(tmp_path / "a", demo_rows())
    second = write_run(tmp_path / "b", demo_rows())
    assert summary.main([str(first), str(second)]) == 0
    err = capsys.readouterr().err
    assert "cảnh báo" in err and RUN_ID in err
