"""Vẽ biểu đồ từ `results/<run_id>/measurements.csv` (docs/EXPERIMENT_PLAN.md mục 3.3 và 10).

Cách dùng: `python scripts/plot_results.py <run_dir> [<run_dir> ...] [--out <dir>]` — đọc và **gộp**
CSV của mọi thư mục rồi ghi `fig_*.png` vào `--out` (mặc định: thư mục kết quả đầu tiên).
T60 đo một đồ thị mỗi lần chạy, nên E3 (4 kích thước) là 4 thư mục; khi gộp nhiều thư mục thì bắt
buộc truyền `--out` để không ghi hình E3 lẫn vào thư mục của riêng một kích thước. Backend `"Agg"`
nên chạy được cả trên máy không có màn hình.

Phạm vi: RQ1b workload **"fixed trips"**, **4 kích thước** — hình chọn theo cột `suite`
(docs/TASKS.md): `demo` = E2, `scaling` = E3, `scenario` = E4. E5 (tour) đọc thêm
`tour_measurements.csv` trong **cùng** các thư mục (định dạng docs/tasks/T74-tour-benchmark.md); thư mục không có
file này vẫn chạy như cũ, chỉ hình E5 bị bỏ qua. Thiếu dữ liệu cho hình nào thì hình đó bị bỏ qua
kèm lý do in ra màn hình; các hình còn lại vẫn được vẽ, không làm hỏng cả lần chạy.

Tour (mục 8): một **bộ** điểm là `(run_id, n_stops, set_id)`, các phương án của cùng bộ dùng chung
ma trận nên `feasible` luôn giống nhau; bộ không khả thi bị loại khỏi mọi chỉ số và chỉ được đếm
(không gán gap 0). `Improvement% = 100·(C_input − C_phương_án)/C_input` và
`Gap% = 100·(C_phương_án − C_held_karp)/C_held_karp` tính **từng bộ** rồi mới lấy median + tứ
phân vị, không lấy tỉ số của hai trung bình.

Mỗi hình ghi `run_id`, **số cặp** và `dataset_id` trong chú thích dưới hình (yêu cầu của mục 10).
`matplotlib` chỉ được nạp khi thực sự vẽ (extra `bench`), nhờ vậy phần đọc/kiểm CSV vẫn dùng được
ở nơi không cài matplotlib.
"""

from __future__ import annotations

import csv
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Sequence

if TYPE_CHECKING:                     # chỉ để đọc kiểu, không nạp matplotlib khi import
    from matplotlib.figure import Figure

MEASUREMENT_COLUMNS = (
    "run_id", "suite", "dataset_id", "size_label", "n_nodes", "n_edges", "query_id", "workload",
    "stratum", "source", "target", "hav_m", "algo", "scenario_id", "blocked_count", "status",
    "cost_s", "distance_m", "expanded", "unique_expanded", "reopened", "relaxations", "pushes",
    "max_frontier", "runtime_ns_median", "runtime_ns_min", "repeats",
)
ALGO_ORDER = ("dijkstra", "astar")
ALGO_LABEL = {"dijkstra": "Dijkstra", "astar": "A*"}
ALGO_COLOR = {"dijkstra": "#1f77b4", "astar": "#d62728"}
WORKLOAD_STYLE = ("-", "--", ":", "-.")
SUITE_DEMO, SUITE_SCALING, SUITE_SCENARIO = "demo", "scaling", "scenario"
MIN_SIZES = 2                                      # đường theo |V| cần ít nhất 2 kích thước
# T60 ghi tầng bằng các giá trị này; thứ tự trục x cố định, không phụ thuộc thứ tự dòng trong CSV.
STRATUM_ORDER = ("ngan", "trung_binh", "dai")
STRATUM_LABEL = {"ngan": "ngắn (δ<0,2)", "trung_binh": "trung bình", "dai": "dài (δ≥0,5)"}
USAGE = "cách dùng: python scripts/plot_results.py <run_dir> [<run_dir> ...] [--out <dir>]"


@dataclass(frozen=True)
class Row:
    """Một dòng `measurements.csv` đã đọc số (một cặp × một thuật toán)."""

    run_id: str
    suite: str
    dataset_id: str
    n_nodes: int
    query_id: str
    workload: str
    stratum: str
    algo: str
    scenario_id: str
    expanded: int
    runtime_ms: float


@dataclass(frozen=True)
class PlotReport:
    """Kết quả một lần vẽ: hình đã tạo, hình bị bỏ qua kèm lý do, chú thích của hình đã tạo."""

    created: dict[str, Path]
    skipped: dict[str, str]
    captions: dict[str, str]


def _number(path: Path, lineno: int, raw: dict[str, str], name: str) -> float:
    """Đọc một ô số; ô rỗng hoặc không phải số là lỗi dữ liệu, không im lặng bỏ qua."""
    try:
        return float(raw[name])
    except (TypeError, ValueError):
        raise ValueError(f"{path}:{lineno}: cột {name} = {raw[name]!r} không phải số") from None


def read_measurements(run_dir: Path | str) -> list[Row]:
    """Đọc `measurements.csv` trong `run_dir`; thiếu file/cột hoặc ô số sai thì `ValueError`."""
    run_dir = Path(run_dir)
    path = run_dir / "measurements.csv"
    if not path.is_file():
        raise FileNotFoundError(f"không thấy {path}")
    rows: list[Row] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in MEASUREMENT_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: thiếu cột {', '.join(missing)} (mục 3.3 EXPERIMENT_PLAN)")
        for lineno, raw in enumerate(reader, start=2):
            rows.append(Row(
                run_id=(raw["run_id"] or "").strip(),
                suite=(raw["suite"] or "").strip().lower(),
                dataset_id=(raw["dataset_id"] or "").strip(),
                n_nodes=int(_number(path, lineno, raw, "n_nodes")),
                query_id=(raw["query_id"] or "").strip(),
                workload=(raw["workload"] or "").strip(),
                stratum=(raw["stratum"] or "").strip(),
                algo=(raw["algo"] or "").strip().lower(),
                scenario_id=(raw["scenario_id"] or "").strip(),
                expanded=int(_number(path, lineno, raw, "expanded")),
                runtime_ms=_number(path, lineno, raw, "runtime_ns_median") / 1e6,
            ))
    return rows


# --- Tour (E5): đọc tour_measurements.csv và tính chỉ số từng bộ (EXPERIMENT_PLAN mục 8) ---

# 15 cột của tour_measurements.csv (docs/tasks/T74-tour-benchmark.md)
TOUR_COLUMNS = (
    "run_id", "suite", "dataset_id", "set_id", "n_stops", "seed", "depot_node", "stop_nodes",
    "method", "feasible", "cost_s", "order", "matrix_ns", "order_ns", "route_ns",
)
TOUR_METHOD_ORDER = ("input", "nearest_neighbor", "nearest_neighbor_2opt", "held_karp")
TOUR_METHOD_LABEL = {"input": "thứ tự nhập", "nearest_neighbor": "NN",
                     "nearest_neighbor_2opt": "NN + 2-opt", "held_karp": "Held–Karp"}
TOUR_METHOD_COLOR = {"input": "#9467bd", "nearest_neighbor": "#2ca02c",
                     "nearest_neighbor_2opt": "#ff7f0e", "held_karp": "#7f7f7f"}


@dataclass(frozen=True)
class TourRow:
    """Một dòng `tour_measurements.csv` đã đọc số (một bộ × một phương án)."""

    run_id: str
    dataset_id: str
    set_id: int
    n_stops: int
    feasible: bool
    method: str
    cost_s: float | None
    order_ms: float                  # order_ns / 1e6


@dataclass(frozen=True)
class TourStats:
    """Chỉ số E5 tính **từng bộ** rồi gom theo `(n_stops, phương án)`.

    `improvements` so với `input`, `gaps` so với `held_karp` (chi phí thô×100); `input` không có
    Improvement (là mốc), `held_karp` không có Gap (là mốc). Bộ `feasible = false` bị loại khỏi
    mọi danh sách và chỉ được đếm trong `n_total`, không vào `n_feasible` (mục 8: không gán gap 0).
    """

    improvements: dict[tuple[int, str], list[float]]
    gaps: dict[tuple[int, str], list[float]]
    order_ms: dict[tuple[int, str], list[float]]
    n_feasible: dict[int, int]
    n_total: dict[int, int]
    missing_input: int               # số (bộ, phương án) bị bỏ khỏi Improvement vì thiếu `input`
    missing_held_karp: int           # số (bộ, phương án) bị bỏ khỏi Gap vì thiếu `held_karp`


def _boolean(path: Path, lineno: int, raw_value: str, name: str) -> bool:
    """Đọc ô `true`/`false` (không phân biệt hoa thường); khác là lỗi dữ liệu."""
    text = (raw_value or "").strip().lower()
    if text in ("true", "1"):
        return True
    if text in ("false", "0"):
        return False
    raise ValueError(f"{path}:{lineno}: cột {name} = {raw_value!r} không phải true/false")


def read_tour_measurements(run_dir: Path | str) -> list[TourRow]:
    """Đọc `tour_measurements.csv` (docs/tasks/T74-tour-benchmark.md); file vắng mặt → rỗng, không lỗi."""
    path = Path(run_dir) / "tour_measurements.csv"
    if not path.is_file():
        return []
    rows: list[TourRow] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in TOUR_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: thiếu cột {', '.join(missing)} (docs/tasks/T74-tour-benchmark.md)")
        for lineno, raw in enumerate(reader, start=2):
            cost = (raw["cost_s"] or "").strip()
            rows.append(TourRow(
                run_id=(raw["run_id"] or "").strip(),
                dataset_id=(raw["dataset_id"] or "").strip(),
                set_id=int(_number(path, lineno, raw, "set_id")),
                n_stops=int(_number(path, lineno, raw, "n_stops")),
                feasible=_boolean(path, lineno, raw["feasible"], "feasible"),
                method=(raw["method"] or "").strip().lower(),
                cost_s=_number(path, lineno, raw, "cost_s") if cost else None,
                order_ms=_number(path, lineno, raw, "order_ns") / 1e6,
            ))
    return rows


def percentile(values: Sequence[float], fraction: float) -> float | None:
    """Phân vị bằng nội suy tuyến tính trên vị trí `(n-1)·p` (mục 3.2, cùng cách của E2/E3/E4)."""
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def tour_stats(tour_rows: Sequence[TourRow]) -> TourStats:
    """Tính chỉ số E5 **từng bộ** `(run_id, n_stops, set_id)` rồi gom theo `(n_stops, phương án)`.

    Bộ `feasible = false` chỉ được đếm, không gán gap 0; bộ thiếu phương án cần đến bị bỏ khỏi
    chỉ số đó, mỗi cặp (bộ, phương án) bị bỏ như vậy được đếm vào `missing_input` /
    `missing_held_karp` để ghi chú thay vì im lặng.
    """
    costs: dict[tuple[str, int, int], dict[str, float]] = {}
    timings: dict[tuple[str, int, int], dict[str, float]] = {}
    feasible: dict[tuple[str, int, int], bool] = {}
    seen: dict[tuple[str, int, int], None] = {}   # dict giữ thứ tự xuất hiện, set thì không
    for row in tour_rows:
        key = (row.run_id, row.n_stops, row.set_id)
        seen[key] = None
        feasible[key] = feasible.get(key, True) and row.feasible
        if row.cost_s is not None:                     # bộ khả thi mới có chi phí/timing dùng được
            costs.setdefault(key, {})[row.method] = row.cost_s
            timings.setdefault(key, {})[row.method] = row.order_ms

    improvements: dict[tuple[int, str], list[float]] = {}
    gaps: dict[tuple[int, str], list[float]] = {}
    order_ms: dict[tuple[int, str], list[float]] = {}
    n_feasible: dict[int, int] = {}
    n_total: dict[int, int] = {}
    missing_input = 0
    missing_held_karp = 0
    for key in seen:
        by_method = costs.get(key, {})
        n_stops = key[1]
        n_total[n_stops] = n_total.get(n_stops, 0) + 1
        if not feasible[key] or not by_method:
            # không khả thi (hoặc thiếu chi phí dùng được): chỉ đếm, không vào các chỉ số
            continue
        n_feasible[n_stops] = n_feasible.get(n_stops, 0) + 1
        base, optimum = by_method.get("input"), by_method.get("held_karp")
        for method, cost in by_method.items():
            if method not in ("input", "held_karp"):    # Improvement so với thứ tự nhập
                if base is not None and base > 0:
                    improvements.setdefault((n_stops, method), []).append(
                        (base - cost) / base * 100.0)
                else:
                    missing_input += 1
            if method != "held_karp":                   # Gap so với Held–Karp (mốc tối ưu)
                if optimum is not None and optimum > 0:
                    gaps.setdefault((n_stops, method), []).append(
                        (cost - optimum) / optimum * 100.0)
                else:
                    missing_held_karp += 1
            order_ms.setdefault((n_stops, method), []).append(timings[key][method])
    return TourStats(improvements=improvements, gaps=gaps, order_ms=order_ms,
                     n_feasible=n_feasible, n_total=n_total,
                     missing_input=missing_input, missing_held_karp=missing_held_karp)


def _first_seen(values: Iterable[str]) -> list[str]:
    """Giữ thứ tự xuất hiện trong CSV để hình tái lập được, thay vì sắp xếp tuỳ ý."""
    return list(dict.fromkeys(values))


def order_strata(strata: Iterable[str]) -> list[str]:
    """Sắp tầng theo thứ tự cố định `ngan → trung_binh → dai`; tầng lạ (nếu có) đặt sau.

    CSV ghi tầng theo thứ tự cặp ngẫu nhiên, nên không dùng thứ tự xuất hiện cho trục x.
    """
    present = _first_seen(s for s in strata if s)
    known = [s for s in STRATUM_ORDER if s in present]
    return known + [s for s in present if s not in STRATUM_ORDER]


def stratum_label(stratum: str) -> str:
    """Nhãn đọc được cho trục x; tầng lạ giữ nguyên giá trị trong CSV."""
    return STRATUM_LABEL.get(stratum, stratum)


def pair_ratios(rows: Sequence[Row], keys: Sequence[str]) -> dict[tuple, float]:
    """Tỉ lệ `r = expanded_A* / expanded_D` **từng cặp**, gom theo các cột trong `keys`.

    Chỉ lấy cặp có đủ hai thuật toán và `expanded_D > 0` (mục 3.2: cặp mở rộng 0 node không dùng).
    Khi gộp nhiều lần chạy, `keys` **phải chứa `run_id`**: `query_id` chỉ duy nhất trong một lần
    chạy, thiếu `run_id` thì cặp của hai lần chạy sẽ ghi đè nhau.
    """
    per_pair: dict[tuple, dict[str, int]] = {}
    for row in rows:
        if row.algo not in ALGO_ORDER:
            continue
        key = tuple(getattr(row, name) for name in keys)
        per_pair.setdefault(key, {})[row.algo] = row.expanded
    ratios: dict[tuple, float] = {}
    for key, expanded in per_pair.items():
        base, guided = expanded.get("dijkstra"), expanded.get("astar")
        if base is None or guided is None or base <= 0:
            continue
        ratios[key] = guided / base
    return ratios


def _caption(rows: Sequence[Row], n_pairs: int) -> str:
    """Chú thích dưới mọi hình: `run_id`, số cặp và `dataset_id` (mục 10)."""
    run_ids = _first_seen(r.run_id for r in rows) or ["?"]
    datasets = _first_seen(r.dataset_id for r in rows) or ["?"]
    return (f"run_id: {', '.join(run_ids)} · số cặp: {n_pairs} · "
            f"dataset_id: {', '.join(datasets)}")


def _pyplot():
    """Nạp `matplotlib.pyplot` với backend `"Agg"`; chỉ gọi khi thực sự vẽ."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _save(fig: Figure, path: Path, caption: str, title: str) -> None:
    """Gắn tiêu đề + chú thích, lưu PNG rồi đóng figure để không rò rỉ bộ nhớ."""
    plt = _pyplot()
    fig.suptitle(title, fontsize=11)
    fig.text(0.5, -0.02, caption, ha="center", va="top", fontsize=7, color="#444")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _fig_expanded_box(rows: Sequence[Row]) -> tuple[Figure | None, str]:
    """Hình 1 (E2): boxplot `expanded` của Dijkstra và A* theo tầng.

    Trả `(None, lý do)` nếu suite demo không có dòng nào hoặc thiếu cột `stratum`.
    """
    demo = [r for r in rows if r.suite == SUITE_DEMO and r.algo in ALGO_ORDER]
    if not demo:
        return None, f"không có dòng nào thuộc suite {SUITE_DEMO} (E2)"
    strata = order_strata(r.stratum for r in demo)
    if not strata:
        return None, "dòng suite demo không có cột stratum, không chia tầng được"

    plt = _pyplot()
    from matplotlib.patches import Patch

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    offset = 0.22
    for index, stratum in enumerate(strata):
        for order, algo in enumerate(ALGO_ORDER):
            values = [r.expanded for r in demo if r.algo == algo and r.stratum == stratum]
            if not values:
                continue
            position = index + (order - 0.5) * offset
            box = ax.boxplot([values], positions=[position], widths=0.18, patch_artist=True,
                             medianprops={"color": "#222", "linewidth": 1})
            box["boxes"][0].set_facecolor(ALGO_COLOR[algo])
            box["boxes"][0].set_alpha(0.7)
    ax.set_xticks(range(len(strata)))
    ax.set_xticklabels([stratum_label(s) for s in strata])
    ax.set_xlabel("tầng độ dài chuyến (stratum)")
    ax.set_ylabel("số node mở rộng (expanded)")
    ax.legend(handles=[Patch(facecolor=ALGO_COLOR[a], alpha=0.7, label=ALGO_LABEL[a])
                       for a in ALGO_ORDER], frameon=False)
    n_pairs = len({(r.run_id, r.query_id) for r in demo})   # query_id chỉ duy nhất trong một run
    return fig, _caption(demo, n_pairs)


def _fig_expanded_scatter(rows: Sequence[Row]) -> tuple[Figure | None, str]:
    """Hình 2 (E2): scatter `expanded_D` với `expanded_A*` trên trục log, kèm đường y = x."""
    demo = [r for r in rows if r.suite == SUITE_DEMO and r.algo in ALGO_ORDER]
    if not demo:
        return None, f"không có dòng nào thuộc suite {SUITE_DEMO} (E2)"
    per_pair: dict[tuple[str, str], dict[str, int]] = {}
    for row in demo:
        per_pair.setdefault((row.run_id, row.query_id), {})[row.algo] = row.expanded
    points = [(ex["dijkstra"], ex["astar"]) for ex in per_pair.values()
              if "dijkstra" in ex and "astar" in ex and ex["dijkstra"] > 0 and ex["astar"] > 0]
    if not points:
        return None, "không có cặp nào đủ expanded của cả hai thuật toán và > 0 để vẽ log–log"

    plt = _pyplot()

    fig, ax = plt.subplots(figsize=(5.2, 5.0))
    ax.scatter([p[0] for p in points], [p[1] for p in points], s=12, alpha=0.6,
               color="#1f77b4", linewidths=0)
    low = min(min(p) for p in points)
    high = max(max(p) for p in points)
    ax.plot([low, high], [low, high], color="#444", linewidth=1, linestyle="--", label="y = x")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("expanded của Dijkstra (node)")
    ax.set_ylabel("expanded của A* (node)")
    ax.legend(frameon=False)
    ax.grid(True, which="both", alpha=0.25, linewidth=0.5)
    return fig, _caption(demo, len(points))


def _fig_scaling(rows: Sequence[Row]) -> tuple[Figure | None, str]:
    """Hình 3 (E3): median `expanded` và median thời gian theo `|V|`, mỗi workload một đường."""
    scaling = [r for r in rows if r.suite == SUITE_SCALING and r.algo in ALGO_ORDER]
    if not scaling:
        return None, f"không có dòng nào thuộc suite {SUITE_SCALING} (E3)"
    sizes = sorted({r.n_nodes for r in scaling})
    if len(sizes) < MIN_SIZES:
        return None, f"chỉ có {len(sizes)} kích thước |V|, cần ít nhất {MIN_SIZES} để vẽ đường"
    workloads = _first_seen(r.workload for r in scaling)

    plt = _pyplot()

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for index, workload in enumerate(workloads):
        style = WORKLOAD_STYLE[index % len(WORKLOAD_STYLE)]
        for algo in ALGO_ORDER:
            subset = [r for r in scaling if r.workload == workload and r.algo == algo]
            xs, expanded, runtime = [], [], []
            for size in sizes:
                group = [r for r in subset if r.n_nodes == size]
                if not group:
                    continue
                xs.append(size)
                expanded.append(statistics.median(r.expanded for r in group))
                runtime.append(statistics.median(r.runtime_ms for r in group))
            if not xs:
                continue
            label = f"{ALGO_LABEL[algo]} · {workload or 'mọi workload'}"
            for axis, ys in ((ax_left, expanded), (ax_right, runtime)):
                axis.plot(xs, ys, style, marker="o", markersize=4,
                          color=ALGO_COLOR[algo], label=label)
    for axis in (ax_left, ax_right):
        axis.set_xlabel("|V| — số node của vùng đo (node)")
        axis.grid(True, alpha=0.3, linewidth=0.5)
    ax_left.set_ylabel("median số node mở rộng (expanded)")
    ax_left.set_title("median expanded theo |V|", fontsize=9)
    ax_right.set_ylabel("median thời gian truy vấn (ms)")
    ax_right.set_title("median thời gian theo |V|", fontsize=9)
    ax_left.legend(frameon=False, fontsize=7)
    # mỗi lần chạy × chuyến × kích thước là một cặp riêng (query_id chỉ duy nhất trong một run)
    n_pairs = len({(r.run_id, r.workload, r.n_nodes, r.query_id) for r in scaling})
    return fig, _caption(scaling, n_pairs)


def _fig_ratio_by_size(rows: Sequence[Row]) -> tuple[Figure | None, str]:
    """Hình 4 (E3): median `r = expanded_A* / expanded_D` theo `|V|`, mỗi workload một đường."""
    scaling = [r for r in rows if r.suite == SUITE_SCALING and r.algo in ALGO_ORDER]
    if not scaling:
        return None, f"không có dòng nào thuộc suite {SUITE_SCALING} (E3)"
    ratios = pair_ratios(scaling, ("run_id", "workload", "n_nodes", "query_id"))
    if not ratios:
        return None, "không có cặp nào đủ expanded của cả hai thuật toán để tính r"
    sizes = sorted({key[2] for key in ratios})
    if len(sizes) < MIN_SIZES:
        return None, f"chỉ có {len(sizes)} kích thước |V|, cần ít nhất {MIN_SIZES} để vẽ đường"

    plt = _pyplot()

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    workloads = _first_seen(key[1] for key in ratios)
    colors = ("#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#8c564b")
    for index, workload in enumerate(workloads):
        xs, medians = [], []
        for size in sizes:
            values = [value for (_, w, n, _q), value in ratios.items()
                      if w == workload and n == size]
            if not values:
                continue
            xs.append(size)
            medians.append(statistics.median(values))
        if not xs:
            continue
        ax.plot(xs, medians, marker="o", markersize=4,
                color=colors[index % len(colors)],
                label=workload or "mọi workload")
    ax.set_xlabel("|V| — số node của vùng đo (node)")
    ax.set_ylabel("median r = expanded A* / expanded Dijkstra")
    ax.set_title("tỉ lệ node mở rộng theo |V|", fontsize=9)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.legend(frameon=False, fontsize=8)
    n_pairs = len(ratios)
    return fig, _caption(scaling, n_pairs)


def _fig_ratio_by_scenario(rows: Sequence[Row]) -> tuple[Figure | None, str]:
    """Hình 5 (E4): boxplot `r` theo kịch bản ùn tắc/đóng đường."""
    scenario = [r for r in rows if r.suite == SUITE_SCENARIO and r.algo in ALGO_ORDER]
    if not scenario:
        return None, f"không có dòng nào thuộc suite {SUITE_SCENARIO} (E4)"
    ratios = pair_ratios(scenario, ("run_id", "scenario_id", "query_id"))
    if not ratios:
        return None, "không có cặp nào đủ expanded của cả hai thuật toán để tính r"
    scenarios = _first_seen(key[1] for key in ratios)

    plt = _pyplot()

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    data = [[value for (_, name, _q), value in ratios.items() if name == scenario_id]
            for scenario_id in scenarios]
    box = ax.boxplot(data, patch_artist=True, medianprops={"color": "#222", "linewidth": 1})
    for patch in box["boxes"]:
        patch.set_facecolor("#1f77b4")
        patch.set_alpha(0.65)
    ax.set_xticks(range(1, len(scenarios) + 1))
    ax.set_xticklabels(scenarios)
    ax.set_xlabel("kịch bản (scenario_id)")
    ax.set_ylabel("r = expanded A* / expanded Dijkstra")
    ax.set_title("tỉ lệ node mở rộng theo kịch bản", fontsize=9)
    ax.grid(True, axis="y", alpha=0.3, linewidth=0.5)
    n_pairs = len(ratios)
    return fig, _caption(scenario, n_pairs)


def _tour_caption(tour_rows: Sequence[TourRow], n_feasible: int, n_total: int) -> str:
    """Chú thích hình E5: run_id, số bộ khả thi/tổng (bộ `feasible = false` bị bỏ) và dataset_id."""
    run_ids = _first_seen(r.run_id for r in tour_rows) or ["?"]
    datasets = _first_seen(r.dataset_id for r in tour_rows) or ["?"]
    return (f"run_id: {', '.join(run_ids)} · số bộ khả thi: {n_feasible}/{n_total} · "
            f"dataset_id: {', '.join(datasets)}")


def _fig_e5_tour(tour_rows: Sequence[TourRow]) -> tuple[Figure | None, str]:
    """Hình 6 (E5): median Improvement% (so với thứ tự nhập) và Gap% vs Held–Karp theo `n_stops`.

    Mỗi phương án một đường median + vùng tứ phân vị (nội suy tuyến tính, mục 3.2); hai chỉ số
    tính **từng bộ** rồi mới gom (mục 8). `input` là mốc của Improvement, `held_karp` là mốc của
    Gap nên không nằm trên đường nào. Trả `(None, lý do)` nếu không có file tour hoặc không đủ
    dữ liệu để vẽ đường nào.
    """
    if not tour_rows:
        return None, "không có dòng nào thuộc tour_measurements.csv (E5)"
    stats = tour_stats(tour_rows)
    sizes = sorted({n for (n, _method) in {**stats.improvements, **stats.gaps}})
    if not sizes:
        return None, "không có cặp (bộ, phương án) nào đủ dữ liệu để tính Improvement/Gap (E5)"
    present = {m for (_n, m) in stats.improvements} | {m for (_n, m) in stats.gaps}
    methods = [m for m in TOUR_METHOD_ORDER if m in present]
    methods += sorted(m for m in present if m not in TOUR_METHOD_ORDER)

    plt = _pyplot()
    fig, (ax_impr, ax_gap) = plt.subplots(1, 2, figsize=(10.5, 4.2))

    def draw(axis, cells: dict[tuple[int, str], list[float]], names: Iterable[str]) -> bool:
        """Vẽ mỗi phương án một đường median + vùng tứ phân vị; trả về có vẽ gì không."""
        drawn = False
        for method in names:
            xs, medians, lows, highs = [], [], [], []
            for size in sizes:
                values = cells.get((size, method))
                if not values:
                    continue
                xs.append(size)
                medians.append(statistics.median(values))
                if len(values) >= 2:
                    lows.append(percentile(values, 0.25))
                    highs.append(percentile(values, 0.75))
                else:
                    lows.append(None)
                    highs.append(None)
            if not xs:
                continue
            color = TOUR_METHOD_COLOR.get(method, "#1f77b4")
            axis.plot(xs, medians, marker="o", markersize=4, color=color,
                      label=TOUR_METHOD_LABEL.get(method, method))
            drawn = True
            # fill_between không nhận None: chỉ tô theo từng đoạn liền có đủ tứ phân vị
            index, total = 0, len(xs)
            while index < total:
                if lows[index] is None:
                    index += 1
                    continue
                start = index
                while index < total and lows[index] is not None:
                    index += 1
                axis.fill_between(xs[start:index], lows[start:index], highs[start:index],
                                  color=color, alpha=0.15, linewidth=0)
        return drawn

    drew_impr = draw(ax_impr, stats.improvements,
                     [m for m in methods if m not in ("input", "held_karp")])
    drew_gap = draw(ax_gap, stats.gaps, [m for m in methods if m != "held_karp"])
    if not drew_impr and not drew_gap:
        plt.close(fig)
        return None, "không có cặp (bộ, phương án) nào đủ dữ liệu để tính Improvement/Gap (E5)"
    if drew_gap:
        ax_gap.axhline(0, color="#555555", linestyle=":", linewidth=1,
                       label="Held–Karp (mốc tối ưu)")
    for axis in (ax_impr, ax_gap):
        axis.set_xlabel("số điểm giao trong bộ (n_stops)")
        axis.grid(True, alpha=0.3, linewidth=0.5)
    ax_impr.set_ylabel("median Improvement % (so với thứ tự nhập)")
    ax_impr.set_title("median Improvement% theo số điểm giao", fontsize=9)
    ax_gap.set_ylabel("median Gap % (so với Held–Karp)")
    ax_gap.set_title("median Gap% theo số điểm giao", fontsize=9)
    ax_impr.legend(frameon=False, fontsize=8)
    ax_gap.legend(frameon=False, fontsize=8)
    return fig, _tour_caption(tour_rows, sum(stats.n_feasible.values()),
                              sum(stats.n_total.values()))


# Tên file → (hàm vẽ, tiêu đề, nguồn). Nguồn "tour" đọc tour_measurements.csv thay cho
# measurements.csv, nên thư mục không có file tour vẫn vẽ được mọi hình còn lại.
FIGURES: tuple[tuple[str, str, str, Callable[..., tuple[Figure | None, str]]], ...] = (
    ("fig_e2_expanded_box.png", "E2 — expanded theo tầng chuyến", "measurements",
     _fig_expanded_box),
    ("fig_e2_expanded_scatter.png", "E2 — expanded A* so với Dijkstra", "measurements",
     _fig_expanded_scatter),
    ("fig_e3_expanded_runtime.png", "E3 — median expanded và thời gian theo |V|", "measurements",
     _fig_scaling),
    ("fig_e3_ratio_by_size.png", "E3 — median r theo |V|", "measurements", _fig_ratio_by_size),
    ("fig_e4_ratio_by_scenario.png", "E4 — r theo kịch bản", "measurements",
     _fig_ratio_by_scenario),
    ("fig_e5_tour.png", "E5 — tour: Improvement và Gap theo số điểm giao", "tour", _fig_e5_tour),
)


def _run_dirs(run_dirs: Sequence[Path | str] | Path | str) -> list[Path]:
    """Chuẩn hoá tham số: một thư mục (str/Path) hoặc dãy thư mục; rỗng là lỗi."""
    if isinstance(run_dirs, (str, Path)):
        dirs = [Path(run_dirs)]
    else:
        dirs = [Path(d) for d in run_dirs]
    if not dirs:
        raise ValueError("cần ít nhất một thư mục kết quả")
    return dirs


def plot_run(run_dirs: Sequence[Path | str] | Path | str,
             out_dir: Path | str | None = None) -> PlotReport:
    """Gộp CSV của mọi thư mục trong `run_dirs` rồi vẽ hình vào `out_dir`.

    `out_dir` mặc định là thư mục đầu tiên; nhiều thư mục mà không chỉ định `out_dir` là lỗi, vì
    hình E3 gộp nhiều kích thước không được ghi lẫn vào thư mục của riêng một kích thước.
    Hình thiếu dữ liệu bị bỏ qua kèm lý do, không làm hỏng cả lần chạy.
    """
    dirs = _run_dirs(run_dirs)
    if out_dir is None:
        if len(dirs) > 1:
            raise ValueError("gộp nhiều thư mục kết quả thì phải chỉ định thư mục ra (--out)")
        out = dirs[0]
    else:
        out = Path(out_dir)
    rows: list[Row] = []
    tour_rows: list[TourRow] = []
    for directory in dirs:
        measure_path = directory / "measurements.csv"
        tour_path = directory / "tour_measurements.csv"
        if not measure_path.is_file() and not tour_path.is_file():
            raise FileNotFoundError(f"không thấy {measure_path}")   # thông báo lỗi như trước
        if measure_path.is_file():
            rows.extend(read_measurements(directory))
        if tour_path.is_file():
            tour_rows.extend(read_tour_measurements(directory))
    out.mkdir(parents=True, exist_ok=True)
    created: dict[str, Path] = {}
    skipped: dict[str, str] = {}
    captions: dict[str, str] = {}
    for name, title, source, build in FIGURES:
        fig, note = build(tour_rows if source == "tour" else rows)
        if fig is None:
            skipped[name] = note
            continue
        path = out / name
        _save(fig, path, note, title)
        created[name] = path
        captions[name] = note
    return PlotReport(created=created, skipped=skipped, captions=captions)


def _parse_args(args: Sequence[str]) -> tuple[list[str], str | None]:
    """Tách `run_dir...` và `--out <dir>` (hỗ trợ cả `--out=<dir>`); tham số lạ là lỗi."""
    run_dirs: list[str] = []
    out: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--out":
            if index + 1 >= len(args):
                raise ValueError("--out cần một thư mục")
            out = args[index + 1]
            index += 2
        elif arg.startswith("--out="):
            out = arg.split("=", 1)[1]
            index += 1
        elif arg in ("-h", "--help"):
            raise ValueError("")
        else:
            run_dirs.append(arg)
            index += 1
    return run_dirs, out


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: `python scripts/plot_results.py <run_dir> [...] [--out <dir>]`; mã thoát 0/1/2."""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        run_dirs, out = _parse_args(args)
    except ValueError as exc:
        if str(exc):
            print(f"lỗi: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    if not run_dirs:
        print(USAGE, file=sys.stderr)
        return 2
    if len(run_dirs) > 1 and out is None:
        print(f"lỗi: gộp {len(run_dirs)} thư mục kết quả thì phải truyền --out <dir> "
              "để không ghi hình E3 vào thư mục của riêng một kích thước", file=sys.stderr)
        return 2
    try:
        report = plot_run(run_dirs, out)
    except ImportError as exc:
        print(f"lỗi: cần matplotlib để vẽ hình — cài extra 'bench' ({exc})", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"lỗi: {exc}", file=sys.stderr)
        return 1
    for name, path in report.created.items():
        print(f"đã tạo {path} — {report.captions[name]}")
    for name, reason in report.skipped.items():
        print(f"bỏ qua {name}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
