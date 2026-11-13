"""So sánh 4 thuật toán (Dijkstra, Dijkstra hai chiều, A*, ALT) trên r2000 và r4500 (PLAN O20).

Mỗi đồ thị: sinh 500 cặp ngẫu nhiên trong SCC (seed cố định, chia 3 tầng theo khoảng cách chim bay
như EXPERIMENT_PLAN 2.1), chạy trên 2 kịch bản `baseline` và `peak-center`. Mỗi cặp đo 4 thuật toán
trên cả hai kịch bản, xen kẽ trong cùng một cặp để máy đổi tốc độ giữa lần chạy ảnh hưởng lên hai
kịch bản như nhau; lặp 5 lần lấy median bằng `perf_counter_ns`, warm-up trước khi đo (`--warmup` cặp
+ `--warmup-seconds` ngân sách thời gian, vì khối đo đầu tiên của tiến trình chậm cỡ 2× nếu máy còn
nguội), `gc.disable()` trong lúc đo và đảo thứ tự đo giữa cặp chẵn/lẻ (EXPERIMENT_PLAN 3.1 bước 3–7).
A* tính cả lúc dựng heuristic trong phép đo; ALT không tính tiền xử lý index nhưng ghi riêng
`preprocess_ms` và `memory_bytes`. Mọi kết quả được so chi phí/trạng thái với Dijkstra trước khi ghi;
lệch là dừng. Cuối mỗi đồ thị, `_drift_check` đo lại vài truy vấn để cảnh báo nếu máy đã đổi tốc độ.

Kết quả ghi vào `results/<YYYYMMDD-HHMM>-compare-<git7>/` (hoặc `--out`):
`measurements.csv` (một dòng = đồ thị × kịch bản × cặp × thuật toán), `summary.csv` (median + IQR
theo đồ thị × kịch bản × tầng × thuật toán), `env.json`, `config.json` (lệnh chạy, sha256 đồ thị,
ngưỡng tầng, tham số, kết quả `drift_check`) và `fig_compare.png` (2 cột = hai đồ thị; hàng trên
median expanded thang log, hàng dưới median runtime).

Cách chạy (sau khi script được commit, để `git_dirty = false`):
    D:\\\\SaiGGo-wt\\\\venv311\\\\Scripts\\\\python.exe scripts/compare_algorithms.py

`collect_env`, `generate_queries`, `resolve_side_m`, `MEASUREMENT_COLUMNS` import từ
`run_benchmarks.py`; `percentile` import từ `plot_results.py`; hai file đó không bị sửa.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
SCRIPTS_DIR = Path(__file__).resolve().parent
for _path in (BACKEND_DIR, REPO_ROOT, SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from app.algorithms.alt import AltIndex, alt, build_alt_index
from app.algorithms.astar import astar
from app.algorithms.bidijkstra import bidijkstra
from app.algorithms.dijkstra import dijkstra
from app.algorithms.heuristics import make_geo_heuristic
from app.algorithms.result import SearchResult
from app.graph.model import Graph, GraphMeta, load_graph
from app.graph.scenario import Snapshot, build_snapshot, load_scenarios
from plot_results import percentile
from run_benchmarks import (
    MEASUREMENT_COLUMNS,
    _get_git_info,
    collect_env,
    generate_queries,
    resolve_side_m,
)

SUITE = "compare"
ALGOS = ("dijkstra", "bidijkstra", "astar", "alt")
ALGO_LABEL = {"dijkstra": "Dijkstra", "bidijkstra": "Dijkstra hai chiều",
              "astar": "A* (geo)", "alt": "ALT"}
STRATA = ("ngan", "trung_binh", "dai")
STRATUM_LABEL = {"ngan": "ngắn", "trung_binh": "trung bình", "dai": "dài"}
COLORS = {"dijkstra": "#1f77b4", "bidijkstra": "#d62728", "astar": "#2ca02c", "alt": "#9467bd"}

DEFAULT_GRAPHS = (
    Path("data/processed/hcm-benthanh-r2000-20261024.json"),
    Path("data/processed/hcm-benthanh-r4500-20261024.json"),
)
DEFAULT_SCENARIO_FILE = Path("data/config/scenarios.json")
DEFAULT_SCENARIOS = ("baseline", "peak-center")
DEFAULT_ALT_K = 8
N_PAIRS = 500
SEED = 20261113
REPEATS = 5          # EXPERIMENT_PLAN 3.1 bước 4
WARMUP = 20          # EXPERIMENT_PLAN 3.1 bước 3: số cặp chạy nóng mỗi kịch bản
WARMUP_SECONDS = 1.0  # thêm ngân sách thời gian chạy nóng để san phẳng khối đo đầu tiên (xem _warm_up)
DRIFT_OK_LOW = 0.83   # _drift_check: ngoài khoảng này là máy đã đổi tốc độ giữa lần chạy
DRIFT_OK_HIGH = 1.20
COST_TOL = 1e-6

# Ngưỡng tầng của EXPERIMENT_PLAN 2.1: delta = khoảng cách chim bay / L (cạnh hình vuông vùng).
DELTA_NGAN_LT = 0.2
DELTA_TRUNG_BINH_LT = 0.5

# Giữ nguyên 27 cột của run_benchmarks, thêm sha256 đồ thị và k của ALT.
COMPARE_MEASUREMENT_COLUMNS = [*MEASUREMENT_COLUMNS, "graph_sha256", "k"]

SUMMARY_COLUMNS = [
    "run_id", "dataset_id", "graph_sha256", "size_label", "n_nodes", "n_edges",
    "scenario_id", "stratum", "algo", "k", "n_queries",
    "expanded_median", "expanded_q1", "expanded_q3",
    "runtime_ns_median", "runtime_ns_q1", "runtime_ns_q3", "runtime_ms_median",
    "preprocess_ms", "memory_bytes",
]


@dataclass(frozen=True)
class GraphCase:
    """Một đồ thị đã nạp: cặp truy vấn, thông tin vùng đo và index ALT dựng sẵn."""

    path: Path
    graph: Graph
    meta: GraphMeta
    sha256: str
    file_bytes: int
    l_m: float
    l_source: str
    queries: list[dict]
    sampling: dict
    index: AltIndex


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_case(path: Path, *, n_pairs: int, seed: int, alt_k: int) -> GraphCase:
    """Nạp đồ thị, xác định L, sinh cặp phân tầng và dựng index ALT (đo tiền xử lý riêng)."""
    graph, meta = load_graph(path)
    l_m, l_source = resolve_side_m(path, graph)
    queries, sampling = generate_queries(
        graph, meta, n_pairs, seed, workload="demo", l_box_m=l_m, l_source=l_source)
    index = build_alt_index(graph, meta, k=alt_k)
    return GraphCase(path, graph, meta, _sha256(path), path.stat().st_size,
                     l_m, l_source, queries, sampling, index)


def _measure(fn, repeats: int) -> tuple[SearchResult, list[int]]:
    """Chạy `fn` `repeats` lần; mọi lần phải cùng `expanded` (số tất định)."""
    times: list[int] = []
    result = None
    expanded: set[int] = set()
    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        result = fn()
        t1 = time.perf_counter_ns()
        times.append(t1 - t0)
        expanded.add(result.expanded)
    if len(expanded) != 1:
        raise RuntimeError(f"expanded thay đổi giữa các lần lặp: {sorted(expanded)}")
    return result, times


def _check_cost(reference: SearchResult, candidate: SearchResult, where: str) -> None:
    """Chi phí/trạng thái của `candidate` phải khớp Dijkstra; lệch là lỗi, dừng không ghi."""
    if reference.status != candidate.status:
        raise RuntimeError(
            f"{where}: trạng thái lệch Dijkstra ({candidate.status!r} vs {reference.status!r})")
    if reference.status != "ok":
        return
    tol = COST_TOL * max(1.0, reference.cost_s)
    if abs(candidate.cost_s - reference.cost_s) > tol:
        raise RuntimeError(
            f"{where}: chi phí lệch Dijkstra ({candidate.cost_s} vs {reference.cost_s}, tol={tol})")


def _stats(values: list[float]) -> dict[str, float]:
    """Median + tứ phân vị (nội suy tuyến tính, cùng cách `plot_results.percentile`)."""
    return {
        "median": statistics.median(values),
        "q1": percentile(values, 0.25),
        "q3": percentile(values, 0.75),
    }


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _run_one(graph: Graph, snap: Snapshot, source: int, target: int, algo: str,
             index: AltIndex):
    """Gọi đúng thuật toán; heuristic A* dựng trong lần gọi nên được tính vào thời gian."""
    if algo == "dijkstra":
        return dijkstra(graph, snap, source, target)
    if algo == "bidijkstra":
        return bidijkstra(graph, snap, source, target)
    if algo == "astar":
        return astar(graph, snap, source, target, make_geo_heuristic(graph, target))
    return alt(graph, snap, source, target, index)


def _warm_up(graph: Graph, snap: Snapshot, queries: list[dict], index: AltIndex,
             warmup: int, budget_s: float) -> int:
    """Chạy nóng trước khi đo: `warmup` cặp đầu, lặp lại tới khi tiêu đủ `budget_s` giây.

    Chạy nóng theo số cặp (EXPERIMENT_PLAN 3.1 bước 3) cộng thêm ngân sách thời gian, vì trên máy
    đo thử khối đo đầu tiên của tiến trình chậm cỡ 2× so với các khối sau (xung CPU còn thấp, cache
    lạnh). Ngân sách thời gian không xoá được trôi theo phút — việc đó do `_drift_check` báo.
    Trả về số lượt gọi đã chạy.
    """
    if warmup <= 0 and budget_s <= 0:
        return 0
    subset = queries[:min(warmup, len(queries))] if warmup > 0 else queries[:1]
    calls = 0
    deadline = time.perf_counter() + max(0.0, budget_s)
    while True:
        for q in subset:
            for algo in ALGOS:
                _run_one(graph, snap, q["source"], q["target"], algo, index)
                calls += 1
        if budget_s <= 0 or time.perf_counter() >= deadline:
            return calls


def _drift_check(graph: Graph, snap: Snapshot, queries: list[dict], index: AltIndex,
                 rows: list[dict], dataset_id: str, sid: str, *, n: int = 3,
                 repeats: int = 3) -> dict:
    """Đo lại vài truy vấn tầng `dai` ở cuối mỗi đồ thị để phát hiện máy đổi tốc độ giữa lần chạy.

    Đo thử cho thấy cùng một khối (cùng 500 cặp, cùng expanded) có thể chênh 1,4–3,6× giữa các lần
    chạy cách nhau vài phút; nếu `ratio` lệch nhiều thì số runtime của lần chạy không dùng để so
    tuyệt đối được. Truy vấn tầng `dai` được chọn vì cỡ mili giây mới tái lập được (tầng `ngan`
    dưới 1 ms dao động 2× ngay giữa hai lần chạy sát nhau).
    """
    sample = [q for q in queries if q["stratum"] == "dai"][:n] or queries[:n]
    recorded = [
        int(next(r["runtime_ns_median"] for r in rows
                 if r["dataset_id"] == dataset_id and r["scenario_id"] == sid
                 and r["query_id"] == q["query_id"] and r["algo"] == "dijkstra"))
        for q in sample
    ]
    recheck: list[float] = []
    for q in sample:
        _, times = _measure(
            lambda q=q: _run_one(graph, snap, q["source"], q["target"], "dijkstra", index),
            repeats)
        recheck.append(statistics.median(times))
    before = statistics.median(recorded)
    after = statistics.median(recheck)
    ratio = after / before
    return {
        "dataset_id": dataset_id,
        "scenario_id": sid,
        "stratum": "dai",
        "n_queries": len(sample),
        "recorded_ms": round(before / 1e6, 4),
        "recheck_ms": round(after / 1e6, 4),
        "ratio": round(ratio, 3),
        "status": "ok" if DRIFT_OK_LOW <= ratio <= DRIFT_OK_HIGH else "canh_bao",
    }


def run_compare(
    graph_paths: list[Path],
    scenarios: dict,
    out_dir: Path,
    *,
    run_id: str,
    scenario_ids: tuple[str, ...] = DEFAULT_SCENARIOS,
    n_pairs: int = N_PAIRS,
    seed: int = SEED,
    repeats: int = REPEATS,
    warmup: int = WARMUP,
    warmup_seconds: float = WARMUP_SECONDS,
    alt_k: int = DEFAULT_ALT_K,
    command: str = "",
    make_figure: bool = True,
) -> dict:
    """Chạy toàn bộ phép so sánh và ghi measurements/summary/env/config (+ hình)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    graph_paths = [Path(p) for p in graph_paths]
    if not graph_paths:
        raise ValueError("cần ít nhất một đồ thị")
    missing = [str(p) for p in graph_paths if not p.is_file()]
    if missing:
        raise ValueError(f"không tìm thấy file đồ thị: {', '.join(missing)}")
    missing = [sid for sid in scenario_ids if sid not in scenarios]
    if missing:
        raise ValueError(f"kịch bản không có trong file: {', '.join(missing)}")
    if not scenario_ids:
        raise ValueError("cần ít nhất một kịch bản")
    if n_pairs <= 0 or repeats <= 0 or warmup < 0:
        raise ValueError("pairs/repeats phải dương và warmup không âm")
    if warmup_seconds < 0:
        raise ValueError("warmup_seconds không âm")

    cases = [load_case(path, n_pairs=n_pairs, seed=seed, alt_k=alt_k) for path in graph_paths]
    total_queries = sum(len(case.queries) for case in cases)
    print(f"Đã nạp {len(cases)} đồ thị · {total_queries} cặp · "
          f"{len(scenario_ids)} kịch bản · {len(ALGOS)} thuật toán")

    rows: list[dict] = []
    drift: list[dict] = []
    for case_index, case in enumerate(cases, 1):
        graph, meta, index = case.graph, case.meta, case.index
        n_nodes, n_edges = len(graph.node_lat), len(graph.edge_u)
        print(f"[{case_index}/{len(cases)}] {graph.dataset_id}: {n_nodes} node, {n_edges} cạnh, "
              f"ALT k={index.k}, tiền xử lý {index.preprocess_ms} ms")
        snapshots: dict[str, Snapshot] = {}
        for sid in scenario_ids:
            snapshots[sid] = build_snapshot(graph, meta, scenarios[sid])
            # Chạy nóng, không ghi kết quả (EXPERIMENT_PLAN 3.1 bước 3).
            warm_calls = _warm_up(graph, snapshots[sid], case.queries, index, warmup,
                                  warmup_seconds)
            print(f"    chạy nóng {sid}: {warm_calls} lượt gọi")

        # Đo xen kẽ kịch bản trong cùng một cặp: máy đổi tốc độ giữa lần chạy (xem `_drift_check`)
        # thì ảnh hưởng lên mọi kịch bản như nhau, không dồn vào kịch bản đo sau.
        for qi, q in enumerate(case.queries):
            source, target = q["source"], q["target"]
            jobs = [(sid, algo) for sid in scenario_ids for algo in ALGOS]
            if qi % 2:                # đảo thứ tự giữa cặp chẵn/lẻ (bước 4)
                jobs.reverse()
            measured: dict[tuple[str, str], tuple[SearchResult, list[int]]] = {}
            gc.collect()
            gc.disable()
            try:
                for sid, algo in jobs:
                    fn = lambda sid=sid, algo=algo: _run_one(  # noqa: E731
                        graph, snapshots[sid], source, target, algo, index)
                    measured[(sid, algo)] = _measure(fn, repeats)
            finally:
                gc.enable()

            for sid in scenario_ids:
                snap = snapshots[sid]
                reference = measured[(sid, "dijkstra")][0]
                where = f"{graph.dataset_id} {sid} q{q['query_id']} ({source}->{target})"
                for algo in ALGOS:
                    res, times = measured[(sid, algo)]
                    _check_cost(reference, res, f"{where} {ALGO_LABEL[algo]}")
                    rows.append({
                        "run_id": run_id,
                        "suite": SUITE,
                        "dataset_id": graph.dataset_id,
                        "size_label": graph.dataset_id,
                        "n_nodes": n_nodes,
                        "n_edges": n_edges,
                        "query_id": q["query_id"],
                        "workload": q["workload"],
                        "stratum": q["stratum"],
                        "source": source,
                        "target": target,
                        "hav_m": q["hav_m"],
                        "algo": algo,
                        "scenario_id": sid,
                        "blocked_count": len(snap.blocked),
                        "status": res.status,
                        "cost_s": round(res.cost_s, 6) if res.cost_s is not None else "",
                        "distance_m": round(res.distance_m, 2) if res.distance_m is not None else "",
                        "expanded": res.expanded,
                        "unique_expanded": res.unique_expanded,
                        "reopened": res.reopened,
                        "relaxations": res.relaxations,
                        "pushes": res.pushes,
                        "max_frontier": res.max_frontier,
                        "runtime_ns_median": int(statistics.median(times)),
                        "runtime_ns_min": min(times),
                        "repeats": repeats,
                        "graph_sha256": case.sha256,
                        "k": index.k if algo == "alt" else "",
                    })
        print(f"    xong {len(case.queries)} cặp × {len(scenario_ids)} kịch bản")

        drift.append(_drift_check(graph, snapshots[scenario_ids[0]], case.queries, index, rows,
                                  graph.dataset_id, scenario_ids[0]))
        last = drift[-1]
        print(f"    kiểm tra trôi: {last['recorded_ms']:.3f} → {last['recheck_ms']:.3f} ms "
              f"(×{last['ratio']:.2f}, {last['status']})")
        if last["status"] != "ok":
            sys.stderr.write(
                f"Cảnh báo: máy đổi tốc độ trong lúc đo {graph.dataset_id} "
                f"(×{last['ratio']:.2f}); số runtime lần này không dùng để so tuyệt đối được.\n")

    _write_csv(out_dir / "measurements.csv", COMPARE_MEASUREMENT_COLUMNS, rows)
    summary = build_summary(rows, cases, run_id, scenario_ids)
    _write_csv(out_dir / "summary.csv", SUMMARY_COLUMNS, summary)

    env = collect_env()
    (out_dir / "env.json").write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")

    config = {
        "run_id": run_id,
        "suite": SUITE,
        "command": command,
        "graphs": [{
            "path": str(case.path),
            "dataset_id": case.graph.dataset_id,
            "sha256": case.sha256,
            "file_bytes": case.file_bytes,
            "n_nodes": len(case.graph.node_lat),
            "n_edges": len(case.graph.edge_u),
            "scc_nodes": sum(1 for v in case.meta.node_in_scc if v),
            "L_m": round(case.l_m, 2),
            "L_source": case.l_source,
            "warmup_used": min(warmup, len(case.queries)),
            "warmup_seconds": warmup_seconds,
            "sampling": case.sampling,
        } for case in cases],
        "scenarios": list(scenario_ids),
        "algorithms": list(ALGOS),
        "alt_k_requested": alt_k,
        "alt_index": [{
            "dataset_id": case.graph.dataset_id,
            "k": case.index.k,
            "landmarks": list(case.index.landmarks),
            "preprocess_ms": case.index.preprocess_ms,
            "memory_bytes": case.index.memory_bytes,
        } for case in cases],
        "n_pairs": n_pairs,
        "seed": seed,
        "repeats": repeats,
        "warmup": warmup,
        "warmup_seconds": warmup_seconds,
        "drift_check": {
            "ok_range": [DRIFT_OK_LOW, DRIFT_OK_HIGH],
            "method": "đo lại 3 truy vấn tầng dai của kịch bản đầu bằng Dijkstra ở cuối mỗi đồ thị",
            "runs": drift,
        },
        "strata_thresholds": {
            "delta_ngan_lt": DELTA_NGAN_LT,
            "delta_trung_binh_lt": DELTA_TRUNG_BINH_LT,
            "delta_dai_ge": DELTA_TRUNG_BINH_LT,
            "delta": "hav_m / L_m của từng đồ thị (bảng graphs)",
            "strata": list(STRATA),
        },
        "cost_check": "cả 4 kết quả phải khớp Dijkstra (1e-6 · max(1, cost)), lệch là dừng",
        "design": "mỗi cặp đo cả 2 kịch bản xen kẽ (không đo theo khối kịch bản) để trôi tốc độ máy "
                  "ảnh hưởng lên mọi kịch bản như nhau; thứ tự đo đảo giữa cặp chẵn/lẻ",
        "runtime_timing": "perf_counter_ns sát quanh lời gọi; A* gồm dựng heuristic; ALT gồm "
                          "ensure_alt_compatible nhưng không gồm tiền xử lý index",
        "python_executable": sys.executable,
        "python_version": sys.version,
        "measurement_columns": COMPARE_MEASUREMENT_COLUMNS,
        "summary_columns": SUMMARY_COLUMNS,
        "cli_args": {},
    }
    (out_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    if make_figure:
        plot_compare(summary, out_dir / "fig_compare.png", run_id, cases, scenario_ids,
                     seed, n_pairs)

    return {"run_id": run_id, "out_dir": str(out_dir), "n_rows": len(rows),
            "n_queries": total_queries, "summary": summary}


def build_summary(rows: list[dict], cases: list[GraphCase], run_id: str,
                  scenario_ids: tuple[str, ...]) -> list[dict]:
    """Median/IQR expanded và runtime theo đồ thị × kịch bản × tầng × thuật toán."""
    summary: list[dict] = []
    for case in cases:
        dataset_id = case.graph.dataset_id
        for sid in scenario_ids:
            for stratum in STRATA:
                for algo in ALGOS:
                    group = [r for r in rows if r["dataset_id"] == dataset_id
                             and r["scenario_id"] == sid and r["stratum"] == stratum
                             and r["algo"] == algo]
                    if not group:
                        continue
                    exp_stats = _stats([r["expanded"] for r in group])
                    rt_stats = _stats([r["runtime_ns_median"] for r in group])
                    is_alt = algo == "alt"
                    summary.append({
                        "run_id": run_id,
                        "dataset_id": dataset_id,
                        "graph_sha256": case.sha256,
                        "size_label": dataset_id,
                        "n_nodes": len(case.graph.node_lat),
                        "n_edges": len(case.graph.edge_u),
                        "scenario_id": sid,
                        "stratum": stratum,
                        "algo": algo,
                        "k": case.index.k if is_alt else "",
                        "n_queries": len(group),
                        "expanded_median": exp_stats["median"],
                        "expanded_q1": exp_stats["q1"],
                        "expanded_q3": exp_stats["q3"],
                        "runtime_ns_median": int(rt_stats["median"]),
                        "runtime_ns_q1": int(rt_stats["q1"]),
                        "runtime_ns_q3": int(rt_stats["q3"]),
                        "runtime_ms_median": round(rt_stats["median"] / 1e6, 4),
                        "preprocess_ms": case.index.preprocess_ms if is_alt else "",
                        "memory_bytes": case.index.memory_bytes if is_alt else "",
                    })
    return summary


# --- Hình ---

def _pyplot():
    """Nạp matplotlib với backend `"Agg"`; chỉ gọi khi thực sự vẽ (như plot_results)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_compare(summary: list[dict], path: Path, run_id: str, cases: list[GraphCase],
                 scenario_ids: tuple[str, ...], seed: int, n_pairs: int) -> Path:
    """2 cột = hai đồ thị; hàng trên median expanded (log), hàng dưới median runtime."""
    plt = _pyplot()
    fig, axes = plt.subplots(2, len(cases), figsize=(6.0 * len(cases), 7.6), squeeze=False)
    x = list(range(len(STRATA)))
    linestyles = ("-", "--", ":", "-.")
    for col, case in enumerate(cases):
        dataset_id = case.graph.dataset_id
        for row, metric in enumerate(("expanded_median", "runtime_ms_median")):
            ax = axes[row][col]
            for algo in ALGOS:
                for pos, sid in enumerate(scenario_ids):
                    points = sorted(
                        (STRATA.index(r["stratum"]), r[metric])
                        for r in summary
                        if r["dataset_id"] == dataset_id and r["scenario_id"] == sid
                        and r["algo"] == algo)
                    if not points:
                        continue
                    ax.plot([p[0] for p in points], [p[1] for p in points], marker="o",
                            markersize=4, color=COLORS[algo],
                            linestyle=linestyles[pos % len(linestyles)])
            ax.set_xticks(x)
            ax.set_xticklabels([STRATUM_LABEL[s] for s in STRATA])
            ax.grid(True, alpha=0.3, linewidth=0.5)
            if row == 0:
                ax.set_yscale("log")
                ax.set_ylabel("median expanded (log)")
                ax.set_title(f"{dataset_id} — số node mở rộng", fontsize=9)
            else:
                ax.set_ylabel("median runtime (ms)")
                ax.set_title(f"{dataset_id} — thời gian truy vấn", fontsize=9)
                ax.set_xlabel("tầng khoảng cách chim bay")
    # Chú giải: 4 màu = 4 thuật toán; nét liền/nét đứt = 2 kịch bản.
    from matplotlib.lines import Line2D

    handles = [Line2D([], [], color=COLORS[a], marker="o", markersize=4, label=ALGO_LABEL[a])
               for a in ALGOS]
    handles += [Line2D([], [], color="#555555", linestyle=linestyles[pos % len(linestyles)],
                       label=sid) for pos, sid in enumerate(scenario_ids)]
    axes[0][0].legend(handles=handles, fontsize=7, frameon=False, loc="best")

    l_m = ", ".join(f"{c.graph.dataset_id}: L={c.l_m:.0f} m ({c.l_source})" for c in cases)
    caption = (f"run_id: {run_id} · seed: {seed} · {n_pairs} cặp/đồ thị · "
               f"nét liền = {scenario_ids[0]}, nét đứt = {scenario_ids[1] if len(scenario_ids) > 1 else '—'}\n"
               f"ngưỡng tầng: delta < {DELTA_NGAN_LT} / < {DELTA_TRUNG_BINH_LT} / ≥ "
               f"{DELTA_TRUNG_BINH_LT} · {l_m}")
    fig.suptitle("So sánh 4 thuật toán trên hai đồ thị — median theo tầng", fontsize=11)
    fig.text(0.5, -0.01, caption, ha="center", va="top", fontsize=7, color="#444")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# --- CLI ---

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="So sánh 4 thuật toán trên r2000 và r4500 (PLAN O20)")
    parser.add_argument("--graphs", type=Path, nargs="+", default=list(DEFAULT_GRAPHS),
                        help="các file đồ thị cần đo (mặc định: r2000 và r4500)")
    parser.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO_FILE,
                        help="file kịch bản (mặc định: data/config/scenarios.json)")
    parser.add_argument("--scenarios", nargs="+", default=list(DEFAULT_SCENARIOS),
                        help="các kịch bản cần đo (mặc định: baseline peak-center)")
    parser.add_argument("--pairs", type=int, default=N_PAIRS,
                        help=f"số cặp mỗi đồ thị (mặc định: {N_PAIRS})")
    parser.add_argument("--seed", type=int, default=SEED,
                        help=f"seed sinh cặp (mặc định: {SEED})")
    parser.add_argument("--repeats", type=int, default=REPEATS,
                        help=f"số lần lặp mỗi truy vấn (mặc định: {REPEATS})")
    parser.add_argument("--warmup", type=int, default=WARMUP,
                        help=f"số cặp warm-up mỗi kịch bản (mặc định: {WARMUP})")
    parser.add_argument("--warmup-seconds", type=float, default=WARMUP_SECONDS,
                        help="ngân sách thời gian chạy nóng mỗi kịch bản, giây "
                             f"(mặc định: {WARMUP_SECONDS}; 0 = chỉ chạy --warmup cặp)")
    parser.add_argument("--alt-k", type=int, default=DEFAULT_ALT_K,
                        help=f"số landmark của ALT (mặc định: {DEFAULT_ALT_K})")
    parser.add_argument("--run-id", default=None,
                        help="ép run_id (mặc định: YYYYMMDD-HHMM-compare-<git7>)")
    parser.add_argument("--out", type=Path, default=None,
                        help="thư mục cha ghi kết quả (mặc định: results/)")
    parser.add_argument("--no-figure", action="store_true", help="không vẽ fig_compare.png")
    return parser.parse_args(argv)


def _resolve(path: Path) -> Path:
    """Đường dẫn tương đối tính từ gốc repo, không phụ thuộc cwd khi chạy."""
    return path if path.is_absolute() else REPO_ROOT / path


def _jsonable(value):
    """Đổi Path (kể cả trong list/dict của argparse) thành chuỗi để ghi config.json."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    args = parse_args(argv)
    graph_paths = [_resolve(p) for p in args.graphs]
    scenario_path = _resolve(args.scenario_file)
    if not scenario_path.is_file():
        sys.stderr.write(f"Lỗi: không tìm thấy file kịch bản {scenario_path}\n")
        return 1
    scenarios = load_scenarios(scenario_path)

    commit, _, _ = _get_git_info()
    run_id = args.run_id or f"{datetime.now():%Y%m%d-%H%M}-{SUITE}-{commit}"
    out_base = args.out if args.out is not None else REPO_ROOT / "results"
    out_dir = Path(out_base) / run_id

    raw_args = list(sys.argv[1:] if argv is None else argv)
    command = subprocess.list2cmdline([sys.executable, str(Path(__file__).resolve()), *raw_args])

    result = run_compare(
        graph_paths, scenarios, out_dir,
        run_id=run_id,
        scenario_ids=tuple(args.scenarios),
        n_pairs=args.pairs,
        seed=args.seed,
        repeats=args.repeats,
        warmup=args.warmup,
        warmup_seconds=args.warmup_seconds,
        alt_k=args.alt_k,
        command=command,
        make_figure=not args.no_figure,
    )

    # Ghi lại tham số CLI thật vào config.json (run_compare đã ghi bản cơ bản).
    config_path = out_dir / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["cli_args"] = {key: _jsonable(value) for key, value in vars(args).items()}
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nĐã chạy xong so sánh: {run_id}")
    print(f"- Số dòng measurements: {result['n_rows']} · số cặp mỗi đồ thị: {args.pairs}")
    print(f"- Thư mục kết quả: {result['out_dir']}")
    print(f"- Lệnh: {command}")
    print("\nMedian theo (đồ thị, kịch bản, tầng, thuật toán):")
    for row in result["summary"]:
        print(f"  {row['dataset_id']:32s} {row['scenario_id']:12s} {row['stratum']:10s} "
              f"{row['algo']:10s} expanded={row['expanded_median']:9.1f} "
              f"runtime={row['runtime_ms_median']:8.3f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
