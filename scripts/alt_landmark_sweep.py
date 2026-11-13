"""Thí nghiệm số landmark k của ALT trên một đồ thị (PLAN O18, docs/EXPERIMENT_PLAN.md mục 3).

Với k ∈ {1, 2, 4, 8, 16}: dựng `AltIndex` trên chi phí cơ sở, đo `expanded` và thời gian truy vấn
trên cùng một bộ cặp ngẫu nhiên trong SCC, ở hai kịch bản `baseline` và `peak-center`; mỗi truy vấn
lặp 5 lần lấy median như mục 3.1. Kèm tham chiếu Dijkstra và A* (heuristic địa lý) trên đúng bộ cặp
đó, và kiểm 100% chi phí khớp Dijkstra (lệch là dừng, không ghi kết quả sai).

Kết quả ghi vào `results/<YYYYMMDD-HHMM>-altk-<git7>/`:
`queries.csv`, `measurements.csv` (một dòng = cặp × k × kịch bản, kèm cột tham chiếu Dijkstra/A*),
`summary.csv` (median + IQR theo k, preprocess_ms, memory_bytes), `env.json`, `config.json`
(lệnh chạy + tham số) và `fig_altk.png`.

Cách chạy chính thức (Python 3.11.9 của worktree):
    D:\\SaiGGo-wt\\venv311\\Scripts\\python.exe scripts/alt_landmark_sweep.py

`collect_env` và `percentile` được import lại từ `run_benchmarks.py` / `plot_results.py` để cùng
định dạng môi trường và cùng cách tính tứ phân vị; hai file đó không bị sửa.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
SCRIPTS_DIR = REPO_ROOT / "scripts"
for _path in (BACKEND_DIR, REPO_ROOT, SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from app.algorithms.alt import alt, build_alt_index
from app.algorithms.astar import astar
from app.algorithms.dijkstra import dijkstra
from app.algorithms.heuristics import make_geo_heuristic
from app.graph.geo import haversine_m
from app.graph.model import Graph, GraphMeta, load_graph
from app.graph.scenario import Snapshot, build_snapshot, load_scenarios
from plot_results import percentile
from run_benchmarks import _get_git_info, collect_env

SUITE = "altk"
K_VALUES = (1, 2, 4, 8, 16)
DEFAULT_SCENARIOS = ("baseline", "peak-center")
DEFAULT_GRAPH = Path("data/processed/hcm-benthanh-r2000-20261024.json")
DEFAULT_SCENARIO_FILE = Path("data/config/scenarios.json")
N_PAIRS = 300
SEED = 20261113
REPEATS = 5          # EXPERIMENT_PLAN 3.1 bước 4
WARMUP = 20          # EXPERIMENT_PLAN 3.1 bước 3
COST_TOL = 1e-6

QUERY_COLUMNS = ["query_id", "source", "target", "hav_m"]

# Một dòng = cặp × k × kịch bản; tham chiếu Dijkstra/A* nằm ở cột `ref_*` trên cùng dòng.
MEASUREMENT_COLUMNS = [
    "run_id", "suite", "dataset_id", "size_label", "n_nodes", "n_edges", "query_id",
    "scenario_id", "source", "target", "hav_m", "k", "algo",
    "status", "cost_s", "distance_m", "expanded", "unique_expanded", "reopened",
    "relaxations", "pushes", "max_frontier", "runtime_ns_median", "runtime_ns_min", "repeats",
    "ref_dijkstra_status", "ref_dijkstra_cost_s", "ref_dijkstra_expanded",
    "ref_dijkstra_runtime_ns_median", "ref_dijkstra_runtime_ns_min",
    "ref_astar_status", "ref_astar_cost_s", "ref_astar_expanded",
    "ref_astar_runtime_ns_median", "ref_astar_runtime_ns_min",
]

SUMMARY_COLUMNS = [
    "run_id", "dataset_id", "scenario_id", "algo", "k", "n_queries",
    "expanded_median", "expanded_q1", "expanded_q3",
    "runtime_ns_median", "runtime_ns_q1", "runtime_ns_q3", "runtime_ms_median",
    "preprocess_ms", "memory_bytes",
]


# --- Sinh cặp và đo ---

def sample_pairs(graph: Graph, meta: GraphMeta, n_pairs: int, seed: int) -> list[dict]:
    """`n_pairs` cặp (source, target) ngẫu nhiên trong SCC, seed cố định, không có source == target.

    Cặp được lấy không lặp khi SCC đủ lớn; nếu `n_pairs` vượt số cặp có thể có thì lấy thêm có lặp
    (mini.json chỉ có 4 node có cạnh ra nên không đủ 300 cặp khác nhau).
    """
    n = len(graph.node_lat)
    nodes = [i for i in range(n) if meta.node_in_scc[i]]
    if len(nodes) < 2:
        nodes = list(range(n))
    if len(nodes) < 2:
        raise ValueError("đồ thị cần ít nhất 2 node trong SCC để sinh cặp")
    capacity = len(nodes) * (len(nodes) - 1)
    rng = random.Random(seed)
    pairs: list[dict] = []
    seen: set[tuple[int, int]] = set()
    while len(pairs) < n_pairs:
        source = rng.choice(nodes)
        target = rng.choice(nodes)
        if source == target:
            continue
        if len(pairs) < capacity:
            if (source, target) in seen:
                continue
            seen.add((source, target))
        hav = haversine_m(graph.node_lat[source], graph.node_lon[source],
                          graph.node_lat[target], graph.node_lon[target])
        pairs.append({"query_id": len(pairs), "source": source, "target": target,
                      "hav_m": round(hav, 2)})
    return pairs


def _measure(fn, repeats: int) -> tuple[object, list[int]]:
    """Chạy `fn` `repeats` lần, trả kết quả lần cuối và danh sách thời gian (ns) từng lần."""
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


def _check_cost(reference, candidate, where: str) -> None:
    """Chi phí/trạng thái của `candidate` phải khớp Dijkstra; lệch là lỗi, không ghi kết quả."""
    if reference.status != candidate.status:
        raise RuntimeError(f"{where}: trạng thái lệch Dijkstra "
                           f"({candidate.status!r} vs {reference.status!r})")
    if reference.status != "ok":
        return
    tol = COST_TOL * max(1.0, reference.cost_s)
    if abs(candidate.cost_s - reference.cost_s) > tol:
        raise RuntimeError(f"{where}: chi phí lệch Dijkstra "
                           f"({candidate.cost_s} vs {reference.cost_s}, tol={tol})")


def _stats(values: list[float]) -> dict[str, float]:
    """Median + tứ phân vị (nội suy tuyến tính, cùng cách `plot_results.percentile`)."""
    return {
        "median": statistics.median(values),
        "q1": percentile(values, 0.25),
        "q3": percentile(values, 0.75),
    }


def run_sweep(
    graph: Graph,
    meta: GraphMeta,
    scenarios: dict,
    out_dir: Path,
    *,
    run_id: str,
    scenario_ids: tuple[str, ...] = DEFAULT_SCENARIOS,
    k_values: tuple[int, ...] = K_VALUES,
    n_pairs: int = N_PAIRS,
    seed: int = SEED,
    repeats: int = REPEATS,
    warmup: int = WARMUP,
    dataset_path: Path | None = None,
    command: str = "",
    make_figure: bool = True,
) -> dict:
    """Chạy toàn bộ thí nghiệm và ghi queries/measurements/summary/env/config (+ hình).

    Trả dict tóm tắt: `run_id`, `out_dir`, `n_rows`, `summary` (list dict) để test và bàn giao dùng.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    missing = [sid for sid in scenario_ids if sid not in scenarios]
    if missing:
        raise ValueError(f"kịch bản không có trong file: {', '.join(missing)}")
    if not k_values or any(k <= 0 for k in k_values):
        raise ValueError("k phải là số nguyên dương")
    if repeats <= 0:
        raise ValueError("repeats phải dương")

    pairs = sample_pairs(graph, meta, n_pairs, seed)
    snaps: dict[str, Snapshot] = {
        sid: build_snapshot(graph, meta, scenarios[sid]) for sid in scenario_ids}

    # Tiền xử lý đo riêng, một lần cho mỗi k (bảng khoảng cách không phụ thuộc kịch bản).
    indexes = {}
    preprocess = {}
    for k in k_values:
        index = build_alt_index(graph, meta, k=k)
        indexes[k] = index
        preprocess[k] = index

    n_nodes, n_edges = len(graph.node_lat), len(graph.edge_u)
    size_label = graph.dataset_id

    with (out_dir / "queries.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=QUERY_COLUMNS)
        writer.writeheader()
        writer.writerows(pairs)

    # Warm-up: chạy mọi thuật toán trên các cặp đầu, không ghi kết quả (mục 3.1 bước 3).
    warm = min(warmup, len(pairs))
    for sid in scenario_ids:
        snap = snaps[sid]
        for q in pairs[:warm]:
            s, t = q["source"], q["target"]
            dijkstra(graph, snap, s, t)
            astar(graph, snap, s, t, make_geo_heuristic(graph, t))
            for k in k_values:
                alt(graph, snap, s, t, indexes[k])

    rows: list[dict] = []
    for sid in scenario_ids:
        snap = snaps[sid]
        for q_idx, q in enumerate(pairs):
            source, target = q["source"], q["target"]
            jobs: list[tuple[str, int | None]] = [("dijkstra", None), ("astar", None)]
            jobs += [("alt", k) for k in k_values]
            if q_idx % 2:                 # đổi thứ tự giữa cặp chẵn/lẻ như mục 3.1 bước 4
                jobs.reverse()

            measured: dict[tuple[str, int | None], tuple[object, list[int]]] = {}
            gc.collect()
            gc.disable()
            try:
                for algo, k in jobs:
                    if algo == "dijkstra":
                        fn = lambda: dijkstra(graph, snap, source, target)  # noqa: E731
                    elif algo == "astar":
                        fn = lambda: astar(graph, snap, source, target,  # noqa: E731
                                           make_geo_heuristic(graph, target))
                    else:
                        fn = lambda k=k: alt(graph, snap, source, target, indexes[k])  # noqa: E731
                    measured[(algo, k)] = _measure(fn, repeats)
            finally:
                gc.enable()

            ref_d, times_d = measured[("dijkstra", None)]
            ref_a, times_a = measured[("astar", None)]
            where = f"{sid} q{q['query_id']} ({source}->{target})"
            _check_cost(ref_d, ref_a, f"{where} A*")
            for k in k_values:
                _check_cost(ref_d, measured[("alt", k)][0], f"{where} ALT k={k}")

            base = {
                "run_id": run_id, "suite": SUITE, "dataset_id": graph.dataset_id,
                "size_label": size_label, "n_nodes": n_nodes, "n_edges": n_edges,
                "query_id": q["query_id"], "scenario_id": sid,
                "source": source, "target": target, "hav_m": q["hav_m"],
                "repeats": repeats,
                "ref_dijkstra_status": ref_d.status,
                "ref_dijkstra_cost_s": round(ref_d.cost_s, 6) if ref_d.cost_s is not None else "",
                "ref_dijkstra_expanded": ref_d.expanded,
                "ref_dijkstra_runtime_ns_median": int(statistics.median(times_d)),
                "ref_dijkstra_runtime_ns_min": min(times_d),
                "ref_astar_status": ref_a.status,
                "ref_astar_cost_s": round(ref_a.cost_s, 6) if ref_a.cost_s is not None else "",
                "ref_astar_expanded": ref_a.expanded,
                "ref_astar_runtime_ns_median": int(statistics.median(times_a)),
                "ref_astar_runtime_ns_min": min(times_a),
            }
            for k in k_values:
                res, times = measured[("alt", k)]
                row = dict(base)
                row.update({
                    "k": k, "algo": "alt", "status": res.status,
                    "cost_s": round(res.cost_s, 6) if res.cost_s is not None else "",
                    "distance_m": round(res.distance_m, 2) if res.distance_m is not None else "",
                    "expanded": res.expanded, "unique_expanded": res.unique_expanded,
                    "reopened": res.reopened, "relaxations": res.relaxations,
                    "pushes": res.pushes, "max_frontier": res.max_frontier,
                    "runtime_ns_median": int(statistics.median(times)),
                    "runtime_ns_min": min(times),
                })
                rows.append(row)

    with (out_dir / "measurements.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MEASUREMENT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = build_summary(rows, preprocess, run_id, graph.dataset_id, scenario_ids, k_values)
    with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary)

    env = collect_env(Path(dataset_path) if dataset_path else None)
    (out_dir / "env.json").write_text(
        json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")

    config = {
        "run_id": run_id,
        "suite": SUITE,
        "dataset_id": graph.dataset_id,
        "graph_path": str(dataset_path) if dataset_path else "",
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "scc_nodes": sum(1 for v in meta.node_in_scc if v),
        "k_values": list(k_values),
        "scenarios": list(scenario_ids),
        "n_pairs": len(pairs),
        "seed": seed,
        "repeats": repeats,
        "warmup": warm,
        "algorithms": ["dijkstra", "astar", "alt"],
        "cost_check": "mọi kết quả ALT/A* phải khớp Dijkstra (1e-6 · max(1, cost)) trước khi ghi",
        "runtime_timing": "perf_counter_ns sát quanh lời gọi, gồm dựng heuristic (A*/ALT) và "
                          "kiểm ensure_alt_compatible của ALT; warm-up ngoài phép đo",
        "preprocess": "build_alt_index trên chi phí cơ sở, đo riêng một lần cho mỗi k",
        "python_executable": sys.executable,
        "python_version": sys.version,
        "command": command,
        "cli_args": {},
    }
    (out_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    if make_figure:
        plot_sweep(summary, out_dir / "fig_altk.png", run_id, len(pairs), graph.dataset_id,
                   scenario_ids, tuple(k_values))

    return {"run_id": run_id, "out_dir": str(out_dir), "n_rows": len(rows), "summary": summary,
            "n_pairs": len(pairs)}


def build_summary(rows: list[dict], indexes: dict[int, object], run_id: str, dataset_id: str,
                  scenario_ids: tuple[str, ...], k_values: tuple[int, ...]) -> list[dict]:
    """Median/IQR expanded và runtime theo k, kèm dòng tham chiếu Dijkstra và A*.

    Giá trị tham chiếu lấy từ các cột `ref_*` (đã đo đúng bộ cặp), mỗi cặp chỉ tính một lần dù
    xuất hiện ở nhiều dòng k. `preprocess_ms`/`memory_bytes` chỉ có ở dòng ALT vì chỉ ALT cần index.
    """
    summary: list[dict] = []
    for sid in scenario_ids:
        subset = [r for r in rows if r["scenario_id"] == sid]
        for algo, prefix in (("dijkstra", "ref_dijkstra"), ("astar", "ref_astar")):
            per_pair = {}
            for row in subset:
                per_pair.setdefault(row["query_id"], row)
            expanded = [r[f"{prefix}_expanded"] for r in per_pair.values()]
            runtime = [r[f"{prefix}_runtime_ns_median"] for r in per_pair.values()]
            stats_ex, stats_rt = _stats(expanded), _stats(runtime)
            summary.append({
                "run_id": run_id, "dataset_id": dataset_id, "scenario_id": sid, "algo": algo,
                "k": "", "n_queries": len(per_pair),
                "expanded_median": stats_ex["median"], "expanded_q1": stats_ex["q1"],
                "expanded_q3": stats_ex["q3"],
                "runtime_ns_median": int(stats_rt["median"]),
                "runtime_ns_q1": int(stats_rt["q1"]), "runtime_ns_q3": int(stats_rt["q3"]),
                "runtime_ms_median": round(stats_rt["median"] / 1e6, 4),
                "preprocess_ms": "", "memory_bytes": "",
            })
        for k in k_values:
            group = [r for r in subset if r["k"] == k]
            if not group:
                continue
            expanded = [r["expanded"] for r in group]
            runtime = [r["runtime_ns_median"] for r in group]
            stats_ex, stats_rt = _stats(expanded), _stats(runtime)
            index = indexes[k]
            summary.append({
                "run_id": run_id, "dataset_id": dataset_id, "scenario_id": sid, "algo": "alt",
                "k": k, "n_queries": len(group),
                "expanded_median": stats_ex["median"], "expanded_q1": stats_ex["q1"],
                "expanded_q3": stats_ex["q3"],
                "runtime_ns_median": int(stats_rt["median"]),
                "runtime_ns_q1": int(stats_rt["q1"]), "runtime_ns_q3": int(stats_rt["q3"]),
                "runtime_ms_median": round(stats_rt["median"] / 1e6, 4),
                "preprocess_ms": index.preprocess_ms,
                "memory_bytes": index.memory_bytes,
            })
    return summary


# --- Hình ---

def _pyplot():
    """Nạp matplotlib với backend `"Agg"`; chỉ gọi khi thực sự vẽ (như plot_results)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def plot_sweep(summary: list[dict], path: Path, run_id: str, n_pairs: int, dataset_id: str,
               scenario_ids: tuple[str, ...], k_values: tuple[int, ...]) -> Path:
    """Vẽ `fig_altk.png`: trái median expanded, phải median runtime + tiền xử lý; đường tham chiếu."""
    plt = _pyplot()
    colors = ("#1f77b4", "#d62728", "#2ca02c", "#9467bd")
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(11.0, 4.4), sharex=True)
    ax_pre = ax_right.twinx()

    preprocess_ms: dict[int, float] = {}
    for row in summary:
        if row["algo"] == "alt" and row["k"] != "":
            preprocess_ms.setdefault(row["k"], row["preprocess_ms"])

    for index, sid in enumerate(scenario_ids):
        color = colors[index % len(colors)]
        alt_rows = sorted((r for r in summary if r["scenario_id"] == sid and r["algo"] == "alt"),
                          key=lambda r: r["k"])
        ks = [r["k"] for r in alt_rows]
        ax_left.plot(ks, [r["expanded_median"] for r in alt_rows], marker="o", markersize=4,
                     color=color, label=f"ALT · {sid}")
        ax_right.plot(ks, [r["runtime_ms_median"] for r in alt_rows], marker="o", markersize=4,
                      color=color, label=f"ALT · {sid}")

        refs = {r["algo"]: r for r in summary if r["scenario_id"] == sid and r["algo"] != "alt"}
        dijkstra, astar = refs["dijkstra"], refs["astar"]
        ax_left.axhline(dijkstra["expanded_median"], color=color, linestyle="--", linewidth=1,
                        label=f"Dijkstra · {sid}")
        ax_left.axhline(astar["expanded_median"], color=color, linestyle=":", linewidth=1,
                        label=f"A* · {sid}")
        ax_right.axhline(dijkstra["runtime_ms_median"], color=color, linestyle="--", linewidth=1,
                         label=f"Dijkstra · {sid}")
        ax_right.axhline(astar["runtime_ms_median"], color=color, linestyle=":", linewidth=1,
                         label=f"A* · {sid}")

    ks = sorted(preprocess_ms)
    ax_pre.plot(ks, [preprocess_ms[k] for k in ks], marker="s", markersize=4, color="#666666",
                linewidth=1, label="tiền xử lý (ms)")

    for axis in (ax_left, ax_right):
        axis.set_xscale("log", base=2)
        axis.set_xticks(list(k_values))
        axis.set_xticklabels([str(k) for k in k_values])
        axis.set_xlabel("số landmark k (thang log2)")
        axis.grid(True, alpha=0.3, linewidth=0.5)
    ax_left.set_ylabel("median số node mở rộng (expanded)")
    ax_left.set_title("median expanded theo k", fontsize=9)
    ax_right.set_ylabel("median thời gian truy vấn (ms)")
    ax_right.set_title("median thời gian truy vấn và tiền xử lý theo k", fontsize=9)
    ax_pre.set_ylabel("thời gian tiền xử lý (ms)")
    ax_left.legend(fontsize=6.5, frameon=False, loc="upper right")
    ax_right.legend(fontsize=6.5, frameon=False, loc="upper right")
    ax_pre.legend(fontsize=6.5, frameon=False, loc="lower right")

    caption = (f"run_id: {run_id} · số cặp: {n_pairs} · dataset_id: {dataset_id}")
    fig.suptitle(f"ALT — ảnh hưởng của số landmark k (kịch bản: {', '.join(scenario_ids)})",
                 fontsize=11)
    fig.text(0.5, -0.02, caption, ha="center", va="top", fontsize=7, color="#444")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# --- CLI ---

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thí nghiệm số landmark k của ALT (PLAN O18)")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH,
                        help="file đồ thị saigo-graph/1 (mặc định: đồ thị demo)")
    parser.add_argument("--scenario-file", type=Path, default=DEFAULT_SCENARIO_FILE,
                        help="file kịch bản (mặc định: data/config/scenarios.json)")
    parser.add_argument("--scenarios", nargs="+", default=list(DEFAULT_SCENARIOS),
                        help="các kịch bản cần đo (mặc định: baseline peak-center)")
    parser.add_argument("--k", type=int, nargs="+", default=list(K_VALUES),
                        help="các giá trị landmark k (mặc định: 1 2 4 8 16)")
    parser.add_argument("--pairs", type=int, default=N_PAIRS,
                        help=f"số cặp trong SCC (mặc định: {N_PAIRS})")
    parser.add_argument("--seed", type=int, default=SEED,
                        help=f"seed sinh cặp (mặc định: {SEED})")
    parser.add_argument("--repeats", type=int, default=REPEATS,
                        help=f"số lần lặp mỗi truy vấn (mặc định: {REPEATS})")
    parser.add_argument("--warmup", type=int, default=WARMUP,
                        help=f"số cặp warm-up (mặc định: {WARMUP})")
    parser.add_argument("--run-id", default=None,
                        help="ép run_id (mặc định: YYYYMMDD-HHMM-altk-<git7>)")
    parser.add_argument("--out", type=Path, default=None,
                        help="thư mục cha ghi kết quả (mặc định: results/)")
    parser.add_argument("--no-figure", action="store_true", help="không vẽ fig_altk.png")
    return parser.parse_args(argv)


def _resolve(path: Path) -> Path:
    """Đường dẫn tương đối tính từ gốc repo, không phụ thuộc cwd khi chạy."""
    return path if path.is_absolute() else REPO_ROOT / path


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
    graph_path = _resolve(args.graph)
    scenario_path = _resolve(args.scenario_file)
    if not graph_path.is_file():
        sys.stderr.write(f"Lỗi: không tìm thấy file đồ thị {graph_path}\n")
        return 1
    if not scenario_path.is_file():
        sys.stderr.write(f"Lỗi: không tìm thấy file kịch bản {scenario_path}\n")
        return 1

    graph, meta = load_graph(graph_path)
    scenarios = load_scenarios(scenario_path)

    commit, _, _ = _get_git_info()
    run_id = args.run_id or f"{datetime.now():%Y%m%d-%H%M}-{SUITE}-{commit}"
    out_base = args.out if args.out is not None else REPO_ROOT / "results"
    out_dir = Path(out_base) / run_id

    raw_args = list(sys.argv[1:] if argv is None else argv)
    command = subprocess.list2cmdline([sys.executable, str(Path(__file__).resolve()), *raw_args])

    result = run_sweep(
        graph, meta, scenarios, out_dir,
        run_id=run_id,
        scenario_ids=tuple(args.scenarios),
        k_values=tuple(sorted(set(args.k))),
        n_pairs=args.pairs,
        seed=args.seed,
        repeats=args.repeats,
        warmup=args.warmup,
        dataset_path=graph_path,
        command=command,
        make_figure=not args.no_figure,
    )

    # Ghi lại tham số CLI thật vào config.json (run_sweep đã ghi bản cơ bản).
    config_path = out_dir / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["cli_args"] = {key: (str(value) if isinstance(value, Path) else value)
                          for key, value in vars(args).items()}
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Đã chạy xong ALT k-sweep: {run_id}")
    print(f"- Đồ thị: {graph.dataset_id} (|V|={len(graph.node_lat)}, |E|={len(graph.edge_u)})")
    print(f"- Số cặp: {result['n_pairs']} · số dòng measurements: {result['n_rows']}")
    print(f"- Thư mục kết quả: {result['out_dir']}")
    print(f"- Lệnh: {command}")
    print("\nMedian theo k (scenario, k, expanded, runtime_ms, preprocess_ms):")
    for row in result["summary"]:
        print(f"  {row['scenario_id']:12s} {str(row['algo']):9s} k={str(row['k']):>2s} "
              f"expanded={row['expanded_median']:8.1f} "
              f"runtime={row['runtime_ms_median']:7.3f} ms "
              f"preprocess={row['preprocess_ms']!s:>6s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
