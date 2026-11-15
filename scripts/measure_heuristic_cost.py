"""E2c: đo tách chi phí tính heuristic của A* trên đúng bộ cặp của E2 (RQ1).

**Chỉ dùng để đo.** App/API và mọi benchmark khác vẫn gọi `app.algorithms.astar.astar`; hai biến
thể dưới đây (`astar_precomputed`, `CountingHeuristic`) chỉ có trong script này, để trả lời câu
hỏi: A* mở ít node hơn Dijkstra (r ≈ 0,40) mà thời gian gần bằng (s ≈ 1,03), có phải vì mỗi lần
push A* phải tính một haversine không?

Hai cách đo, cùng một lần chạy, cùng `queries.csv` của run E2 chính thức (1.000 cặp, seed 42):

(a) **Tách bằng h tính sẵn.** `precompute_h` tính `h(n)` cho mọi node tới đích hiện tại thành mảng
    (|V| lần haversine, đo riêng là `t_pre`), rồi `astar_precomputed` chạy y hệt `astar` nhưng
    đọc `h_arr[v]` thay vì gọi hàm (đo riêng là `t_search`). Giá trị h trùng từng bit với
    `make_geo_heuristic`, nên thứ tự mở rộng, số node và chi phí trùng với A* gốc.
    Phần thời gian A* dành cho h ≈ (t_A − t_search) / t_A.
(b) **Đếm và nhân.** `CountingHeuristic` đếm số lần A* gọi h trong một truy vấn (chạy riêng,
    không tính giờ); micro-benchmark đo thời gian một lần gọi h (`microbench.csv`). Phần thời gian
    A* dành cho h ≈ số lần gọi × thời gian một lần gọi / t_A.

Mỗi cặp đo ba cấu hình D (Dijkstra), A (A* gốc, gồm dựng heuristic như E2) và P (tính sẵn + tìm
kiếm), mỗi cấu hình lặp `--repeats` lần lấy median; thứ tự ba cấu hình xoay vòng theo cặp,
`gc.disable()` trong lúc đo (EXPERIMENT_PLAN mục 3.1). Lệch chi phí hoặc lệch số node giữa A và P
là lỗi, dừng ngay.

Kết quả ghi vào `results/<YYYYMMDD-HHMM>-hcost-<git7>/` (hoặc `--out`): `queries.csv` (bản sao),
`hcost_measurements.csv` (một dòng một cặp), `microbench.csv`, `summary.csv` (theo tầng),
`env.json`, `config.json`. Bảng Markdown in ra stdout.

Cách chạy (sau khi script được commit, để `git_dirty = false`)::

    python scripts/measure_heuristic_cost.py --graph data/processed/hcm-benthanh-r2000-20261024.json
"""

from __future__ import annotations

import argparse
import csv
import gc
import heapq
import json
import math
import random
import shutil
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
SCRIPTS_DIR = Path(__file__).resolve().parent
for _path in (BACKEND_DIR, REPO_ROOT, SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from app.algorithms.astar import astar
from app.algorithms.dijkstra import dijkstra
from app.algorithms.heuristics import Heuristic, geo_scale, make_geo_heuristic
from app.algorithms.result import SearchResult, build_route, check_endpoints
from app.graph.geo import haversine_m
from app.graph.model import Graph, load_graph
from app.graph.scenario import Snapshot, build_snapshot, load_scenarios
from run_benchmarks import _get_git_info, collect_env, read_queries_csv
from summarize_results import bootstrap_median_ci, fmt_number, median

SUITE = "hcost"
DEFAULT_GRAPH = Path("data/processed/hcm-benthanh-r2000-20261024.json")
DEFAULT_QUERIES = Path("results/20261031-1556-demo-054f300/queries.csv")   # bộ cặp của E2
STRATUM_ORDER = ("ngan", "trung_binh", "dai")
ALL = "tat_ca"
COST_TOL = 1e-6

MEASUREMENT_COLUMNS = [
    "run_id", "suite", "dataset_id", "n_nodes", "n_edges", "query_id", "workload", "stratum",
    "source", "target", "hav_m", "status", "cost_s",
    "expanded_d", "expanded_a", "pushes_d", "pushes_a", "h_calls",
    "t_d_ns", "t_a_ns", "t_pre_ns", "t_search_ns", "repeats",
]
MICRO_COLUMNS = ["target", "n_calls", "loop_empty_ns", "loop_index_ns", "loop_h_ns",
                 "loop_haversine_ns", "h_call_ns", "h_extra_vs_index_ns", "haversine_ns"]
SUMMARY_COLUMNS = [
    "run_id", "stratum", "n_pairs", "t_d_ms", "t_a_ms", "t_search_ms", "t_pre_ms", "h_calls",
    "expanded_a",
    *[f"{name}{suffix}" for name in ("s", "s_search", "s_with_pre", "share_a", "share_b")
      for suffix in ("", "_ci_low", "_ci_high")],
    "ns_per_node_d", "ns_per_node_a", "ns_per_node_search",
]


# --- Biến thể chỉ dùng để đo ---

def precompute_h(graph: Graph, target: int, c: float | None = None) -> list[float]:
    """h(n) cho mọi node tới `target`, cùng công thức (và cùng phép tính dấu phẩy động) với
    `make_geo_heuristic`: `c / v_max · haversine(n, target)`. Tốn |V| lần haversine. Chỉ để đo."""
    if c is None:
        c = geo_scale(graph)
    lat, lon = graph.node_lat, graph.node_lon
    lat_t, lon_t = lat[target], lon[target]
    scale = c / graph.v_max_mps
    return [scale * haversine_m(lat[n], lon[n], lat_t, lon_t) for n in range(len(lat))]


def astar_precomputed(graph: Graph, snap: Snapshot, source: int, target: int, h_arr: list[float],
                      *, trace_limit: int = 0) -> SearchResult:
    """Bản sao của `app.algorithms.astar.astar`, chỉ khác `heuristic(v)` thành `h_arr[v]`.

    **Chỉ dùng để đo** phần thời gian A* dành cho việc tính h (E2c); app/API không gọi hàm này.
    Giữ nguyên heap (f, counter, node, g), lazy deletion, mở lại node và các bộ đếm để so được
    từng dòng với A* gốc.
    """
    check_endpoints(graph, source, target)
    if source == target:
        return SearchResult("ok", 0.0, [], [source], 0.0, 0, 0, 0, 0, 0, 0)

    weights, out_edges, edge_v = snap.weights, graph.out_edges, graph.edge_v
    n = len(graph.node_lat)
    g = [math.inf] * n
    pred_edge = [-1] * n
    closed = bytearray(n)
    g[source] = 0.0
    heap = [(h_arr[source], 0, source, 0.0)]
    counter = 1
    expanded = reopened = relaxations = 0
    pushes = max_frontier = 1
    trace: list[int] = []

    while heap:
        _, _, u, d = heapq.heappop(heap)
        if d > g[u]:
            continue
        if u == target:
            edges, nodes = build_route(graph, pred_edge, source, target)
            return SearchResult("ok", d, edges, nodes, sum(graph.edge_length_m[e] for e in edges),
                                expanded, expanded - reopened, reopened, relaxations, pushes, max_frontier,
                                trace, trace_limit > 0 and expanded > trace_limit)
        if closed[u]:
            reopened += 1
        closed[u] = 1
        expanded += 1
        if len(trace) < trace_limit:
            trace.append(u)
        for e in out_edges[u]:
            w = weights[e]
            if w == math.inf:
                continue
            v = edge_v[e]
            nd = d + w
            if nd < g[v]:
                g[v] = nd
                pred_edge[v] = e
                relaxations += 1
                heapq.heappush(heap, (nd + h_arr[v], counter, v, nd))
                counter += 1
                pushes += 1
                max_frontier = max(max_frontier, len(heap))

    return SearchResult("no_path", None, [], [], None, expanded, expanded - reopened, reopened, relaxations,
                        pushes, max_frontier, trace, trace_limit > 0 and expanded > trace_limit)


class CountingHeuristic:
    """Bọc một heuristic và đếm số lần được gọi. Chỉ dùng để đo (chậm hơn h gốc, không tính giờ)."""

    def __init__(self, heuristic: Heuristic) -> None:
        self._h = heuristic
        self.calls = 0

    def __call__(self, node: int) -> float:
        self.calls += 1
        return self._h(node)


# --- Micro-benchmark một lần gọi h ---

def _loop_empty(nodes: list[int]) -> None:
    for _v in nodes:
        pass


def _loop_index(arr: list[float], nodes: list[int]) -> None:
    for v in nodes:
        arr[v]


def _loop_h(h: Callable[[int], float], nodes: list[int]) -> None:
    for v in nodes:
        h(v)


def _loop_haversine(lat: list[float], lon: list[float], lat_t: float, lon_t: float,
                    nodes: list[int]) -> None:
    for v in nodes:
        haversine_m(lat[v], lon[v], lat_t, lon_t)


def _best_ns(fn: Callable[[], None], rounds: int) -> int:
    """Thời gian nhỏ nhất qua `rounds` lần (như `timeit`: lấy min để bớt nhiễu của máy)."""
    best = None
    for _ in range(rounds):
        t0 = time.perf_counter_ns()
        fn()
        elapsed = time.perf_counter_ns() - t0
        best = elapsed if best is None else min(best, elapsed)
    return int(best)


def microbench(graph: Graph, targets: list[int], *, n_calls: int, rounds: int,
               seed: int) -> list[dict]:
    """Thời gian một lần gọi h (ns) cho từng đích: (vòng gọi h − vòng rỗng) / số lần gọi.

    Đo thêm vòng đọc mảng (`h_extra_vs_index_ns` = phần đắt hơn so với `h_arr[v]`) và vòng gọi
    thẳng `haversine_m` (phần lượng giác, không có lớp closure của h).
    """
    rng = random.Random(seed)
    n = len(graph.node_lat)
    nodes = [rng.randrange(n) for _ in range(n_calls)]
    lat, lon = graph.node_lat, graph.node_lon
    out = []
    gc.collect()
    gc.disable()
    try:
        for t in targets:
            h = make_geo_heuristic(graph, t)
            arr = precompute_h(graph, t)
            empty = _best_ns(lambda: _loop_empty(nodes), rounds)
            index = _best_ns(lambda: _loop_index(arr, nodes), rounds)
            call = _best_ns(lambda: _loop_h(h, nodes), rounds)
            hav = _best_ns(lambda: _loop_haversine(lat, lon, lat[t], lon[t], nodes), rounds)
            out.append({
                "target": t, "n_calls": n_calls, "loop_empty_ns": empty, "loop_index_ns": index,
                "loop_h_ns": call, "loop_haversine_ns": hav,
                "h_call_ns": round((call - empty) / n_calls, 2),
                "h_extra_vs_index_ns": round((call - index) / n_calls, 2),
                "haversine_ns": round((hav - empty) / n_calls, 2),
            })
    finally:
        gc.enable()
    return out


# --- Đo từng cặp ---

def _check_same(ref: SearchResult, other: SearchResult, where: str, *, same_expanded: bool) -> None:
    if ref.status != other.status:
        raise RuntimeError(f"{where}: lệch trạng thái {ref.status} / {other.status}")
    if ref.status == "ok" and abs(other.cost_s - ref.cost_s) > COST_TOL * max(1.0, ref.cost_s):
        raise RuntimeError(f"{where}: lệch chi phí {ref.cost_s} / {other.cost_s}")
    if same_expanded and (ref.expanded, ref.pushes, ref.edge_ids) != (other.expanded, other.pushes,
                                                                     other.edge_ids):
        raise RuntimeError(f"{where}: A* tính sẵn h khác A* gốc (expanded/pushes/tuyến)")


def measure_pair(graph: Graph, snap: Snapshot, q: dict, q_idx: int, repeats: int) -> dict:
    """Đo D, A, P của một cặp (mỗi cấu hình `repeats` lần, lấy median), đếm số lần gọi h."""
    source, target = q["source"], q["target"]
    times: dict[str, list[int]] = {"d": [], "a": [], "pre": [], "search": []}
    last: dict[str, SearchResult] = {}

    def run_d() -> None:
        for _ in range(repeats):
            t0 = time.perf_counter_ns()
            last["d"] = dijkstra(graph, snap, source, target, trace_limit=0)
            times["d"].append(time.perf_counter_ns() - t0)

    def run_a() -> None:
        for _ in range(repeats):
            t0 = time.perf_counter_ns()
            h = make_geo_heuristic(graph, target)
            last["a"] = astar(graph, snap, source, target, h, trace_limit=0)
            times["a"].append(time.perf_counter_ns() - t0)

    def run_p() -> None:
        for _ in range(repeats):
            t0 = time.perf_counter_ns()
            arr = precompute_h(graph, target)
            t1 = time.perf_counter_ns()
            last["p"] = astar_precomputed(graph, snap, source, target, arr, trace_limit=0)
            t2 = time.perf_counter_ns()
            times["pre"].append(t1 - t0)
            times["search"].append(t2 - t1)

    order = (run_d, run_a, run_p)
    shift = q_idx % 3
    gc.collect()
    gc.disable()
    try:
        for fn in order[shift:] + order[:shift]:
            fn()
    finally:
        gc.enable()

    where = f"query {q['query_id']} ({source} -> {target})"
    _check_same(last["d"], last["a"], where, same_expanded=False)
    _check_same(last["a"], last["p"], where, same_expanded=True)

    counting = CountingHeuristic(make_geo_heuristic(graph, target))
    counted = astar(graph, snap, source, target, counting, trace_limit=0)
    _check_same(last["a"], counted, where, same_expanded=True)

    res_d, res_a = last["d"], last["a"]
    return {
        "query_id": q["query_id"], "workload": q["workload"], "stratum": q["stratum"],
        "source": source, "target": target, "hav_m": q["hav_m"], "status": res_a.status,
        "cost_s": round(res_a.cost_s, 6) if res_a.cost_s is not None else "",
        "expanded_d": res_d.expanded, "expanded_a": res_a.expanded,
        "pushes_d": res_d.pushes, "pushes_a": res_a.pushes, "h_calls": counting.calls,
        "t_d_ns": int(statistics.median(times["d"])), "t_a_ns": int(statistics.median(times["a"])),
        "t_pre_ns": int(statistics.median(times["pre"])),
        "t_search_ns": int(statistics.median(times["search"])), "repeats": repeats,
    }


def warm_up(graph: Graph, snap: Snapshot, queries: list[dict], n: int) -> None:
    for q in queries[:n]:
        s, t = q["source"], q["target"]
        dijkstra(graph, snap, s, t)
        astar(graph, snap, s, t, make_geo_heuristic(graph, t))
        astar_precomputed(graph, snap, s, t, precompute_h(graph, t))


# --- Tổng hợp ---

CI_METRICS = ("s", "s_search", "s_with_pre", "share_a", "share_b")


def pair_metrics(row: dict, h_call_ns: float) -> dict[str, float]:
    """Chỉ số của một cặp (tỉ số tính **từng cặp**, mục 3.2 EXPERIMENT_PLAN).

    `s_search`: A* nếu h có sẵn miễn phí; `s_with_pre`: A* nếu mỗi truy vấn tự tính sẵn cả mảng h;
    `share_a`, `share_b`: % thời gian A* dành cho h theo cách (a) và (b) ở docstring đầu file.
    """
    t_d, t_a = float(row["t_d_ns"]), float(row["t_a_ns"])
    t_s, t_pre = float(row["t_search_ns"]), float(row["t_pre_ns"])
    return {
        "s": t_d / t_a,
        "s_search": t_d / t_s,
        "s_with_pre": t_d / (t_pre + t_s),
        "share_a": 100.0 * (t_a - t_s) / t_a,
        "share_b": 100.0 * int(row["h_calls"]) * h_call_ns / t_a,
        "ns_per_node_d": t_d / max(1, int(row["expanded_d"])),
        "ns_per_node_a": t_a / max(1, int(row["expanded_a"])),
        "ns_per_node_search": t_s / max(1, int(row["expanded_a"])),
    }


def summarize(rows: list[dict], h_call_ns: float, run_id: str) -> list[dict]:
    """Median theo tầng và toàn bộ; các tỉ số/phần trăm kèm CI 95% bootstrap của median."""
    out = []
    for key in [*[s for s in STRATUM_ORDER if any(r["stratum"] == s for r in rows)], ALL]:
        group = [r for r in rows if key == ALL or r["stratum"] == key]
        if not group:
            continue
        metrics = [pair_metrics(r, h_call_ns) for r in group]

        def raw(name: str) -> list[float]:
            return [float(r[name]) for r in group]

        entry: dict = {"run_id": run_id, "stratum": key, "n_pairs": len(group),
                       "t_d_ms": median(raw("t_d_ns")) / 1e6, "t_a_ms": median(raw("t_a_ns")) / 1e6,
                       "t_search_ms": median(raw("t_search_ns")) / 1e6,
                       "t_pre_ms": median(raw("t_pre_ns")) / 1e6,
                       "h_calls": median(raw("h_calls")), "expanded_a": median(raw("expanded_a"))}
        for name in CI_METRICS:
            values = [m[name] for m in metrics]
            low, high = bootstrap_median_ci(values) or (None, None)
            entry[name], entry[f"{name}_ci_low"], entry[f"{name}_ci_high"] = median(values), low, high
        for name in ("ns_per_node_d", "ns_per_node_a", "ns_per_node_search"):
            entry[name] = median([m[name] for m in metrics])
        out.append(entry)
    return out


def _ci(entry: dict, name: str, digits: int) -> str:
    text = fmt_number(entry[name], digits)
    low, high = entry.get(f"{name}_ci_low"), entry.get(f"{name}_ci_high")
    if low is None:
        return text
    return f"{text} [{fmt_number(low, digits)}; {fmt_number(high, digits)}]"


def render(summary: list[dict], micro: list[dict], run_id: str) -> str:
    """Bảng Markdown in ra stdout (người dẫn số vào docs/EXPERIMENTS.md mục E2c)."""
    label = {"ngan": "ngắn", "trung_binh": "trung bình", "dai": "dài", ALL: "tất cả"}
    h_call = median([m["h_call_ns"] for m in micro])
    lines = [f"# E2c — chi phí heuristic của A* (`{run_id}`)", "",
             f"Micro-benchmark: một lần gọi h = {fmt_number(h_call, 1)} ns (median qua "
             f"{len(micro)} đích), trong đó haversine_m = "
             f"{fmt_number(median([m['haversine_ns'] for m in micro]), 1)} ns; đắt hơn đọc mảng "
             f"{fmt_number(median([m['h_extra_vs_index_ns'] for m in micro]), 1)} ns.", "",
             "| Tầng | Cặp | D ms | A* ms | A* tìm (h sẵn) ms | Tính sẵn h ms | Gọi h | s [CI] | "
             "s nếu h sẵn [CI] | s nếu tự tính sẵn [CI] | % cho h, cách a [CI] | % cho h, cách b [CI] "
             "| ns/node D / A* / A* h sẵn |",
             "|---|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|"]
    for e in summary:
        lines.append(
            f"| {label.get(e['stratum'], e['stratum'])} | {e['n_pairs']} | "
            f"{fmt_number(e['t_d_ms'], 3)} | {fmt_number(e['t_a_ms'], 3)} | "
            f"{fmt_number(e['t_search_ms'], 3)} | {fmt_number(e['t_pre_ms'], 3)} | "
            f"{fmt_number(e['h_calls'], 1)} | {_ci(e, 's', 2)} | {_ci(e, 's_search', 2)} | "
            f"{_ci(e, 's_with_pre', 2)} | {_ci(e, 'share_a', 1)} | {_ci(e, 'share_b', 1)} | "
            f"{round(e['ns_per_node_d'])} / {round(e['ns_per_node_a'])} / "
            f"{round(e['ns_per_node_search'])} |")
    lines += ["", "s = t_D/t_A*; s nếu h sẵn = t_D/t_tìm; s nếu tự tính sẵn = t_D/(t_tính_sẵn + t_tìm); "
              "% cho h cách a = 100·(t_A* − t_tìm)/t_A*; cách b = 100·số lần gọi h·thời gian một "
              "lần gọi/t_A*. Tính từng cặp rồi lấy median; CI 95% bootstrap "
              "(`bootstrap_median_ci` của summarize_results.py)."]
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(graph_path: Path, queries_path: Path, out_dir: Path, run_id: str, *, repeats: int,
        warmup: int, limit: int | None, micro_targets: int, micro_calls: int, micro_rounds: int,
        seed: int, scenario_file: Path, cli_args: dict) -> dict:
    graph, meta = load_graph(graph_path)
    scenarios = load_scenarios(scenario_file)
    snap = build_snapshot(graph, meta, scenarios["baseline"])
    queries = read_queries_csv(queries_path)
    if limit is not None:
        queries = queries[:limit]
    geo_scale(graph)                                  # c được cache trước khi đo, như E2

    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(queries_path, out_dir / "queries.csv")

    warm_up(graph, snap, queries, warmup)
    rows = []
    for q_idx, q in enumerate(queries):
        row = measure_pair(graph, snap, q, q_idx, repeats)
        row.update({"run_id": run_id, "suite": SUITE, "dataset_id": graph.dataset_id,
                    "n_nodes": len(graph.node_lat), "n_edges": len(graph.edge_u)})
        rows.append(row)

    targets = list(dict.fromkeys(q["target"] for q in queries))[:micro_targets]
    micro = microbench(graph, targets, n_calls=micro_calls, rounds=micro_rounds, seed=seed)
    h_call_ns = median([m["h_call_ns"] for m in micro])
    summary = summarize(rows, h_call_ns, run_id)

    _write_csv(out_dir / "hcost_measurements.csv", MEASUREMENT_COLUMNS, rows)
    _write_csv(out_dir / "microbench.csv", MICRO_COLUMNS, micro)
    _write_csv(out_dir / "summary.csv", SUMMARY_COLUMNS,
               [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in e.items()}
                for e in summary])
    env = collect_env(graph_path)
    (out_dir / "env.json").write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")
    config = {
        "run_id": run_id, "suite": SUITE, "graph": Path(graph_path).as_posix(), "dataset_id": graph.dataset_id,
        "queries": Path(queries_path).as_posix(), "n_queries": len(queries), "scenario": "baseline",
        "repeats": repeats, "warmup": warmup,
        "microbench": {"targets": targets, "n_calls": micro_calls, "rounds": micro_rounds,
                       "seed": seed, "h_call_ns_median": h_call_ns},
        "bootstrap": {"n": 10_000, "seed": 20261116, "level": 0.95,
                      "function": "summarize_results.bootstrap_median_ci"},
        "configs": {
            "d": "dijkstra(), như E2",
            "a": "make_geo_heuristic() + astar(), như E2 (thời gian gồm dựng heuristic)",
            "p": "precompute_h() đo riêng (t_pre) rồi astar_precomputed() đo riêng (t_search)",
        },
        "order": "xoay vòng D,A,P theo query_idx % 3; mỗi cấu hình lặp `repeats` lần, lấy median",
        "h_calls": "đếm bằng CountingHeuristic trong một lần chạy riêng, không tính giờ",
        "measurement_columns": MEASUREMENT_COLUMNS, "summary_columns": SUMMARY_COLUMNS,
        "cli_args": cli_args,
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    return {"rows": rows, "micro": micro, "summary": summary, "out_dir": out_dir}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="E2c: đo tách chi phí heuristic của A*")
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES,
                        help="queries.csv có sẵn (mặc định: bộ cặp của run E2 chính thức)")
    parser.add_argument("--scenario-file", type=Path, default=Path("data/config/scenarios.json"))
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--limit", type=int, default=None, help="chỉ đo N cặp đầu (để thử)")
    parser.add_argument("--micro-targets", type=int, default=20)
    parser.add_argument("--micro-calls", type=int, default=20_000)
    parser.add_argument("--micro-rounds", type=int, default=7)
    parser.add_argument("--seed", type=int, default=42, help="seed chọn node cho micro-benchmark")
    parser.add_argument("--run-id", default=None, help="mặc định: YYYYMMDD-HHMM-hcost-<git7>")
    parser.add_argument("--out", type=Path, default=None, help="thư mục cha (mặc định: results/)")
    return parser.parse_args(argv)


def _resolve(path: Path) -> Path:
    if path.is_absolute() or path.exists():
        return path
    return REPO_ROOT / path


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
    args = parse_args(argv)
    graph_path, queries_path = _resolve(args.graph), _resolve(args.queries)
    scenario_file = _resolve(args.scenario_file)
    for path in (graph_path, queries_path, scenario_file):
        if not path.is_file():
            print(f"Lỗi: không tìm thấy {path}", file=sys.stderr)
            return 1
    commit, _, _ = _get_git_info()
    run_id = args.run_id or f"{datetime.now():%Y%m%d-%H%M}-{SUITE}-{commit[:7]}"
    out_dir = (args.out if args.out is not None else REPO_ROOT / "results") / run_id
    cli_args = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    result = run(graph_path, queries_path, out_dir, run_id, repeats=args.repeats,
                 warmup=args.warmup, limit=args.limit, micro_targets=args.micro_targets,
                 micro_calls=args.micro_calls, micro_rounds=args.micro_rounds, seed=args.seed,
                 scenario_file=scenario_file, cli_args=cli_args)
    print(render(result["summary"], result["micro"], run_id), end="")
    print(f"\nThư mục kết quả: {result['out_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
