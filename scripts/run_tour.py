"""E5 — benchmark tour (EXPERIMENT_PLAN mục 8; docs/tasks/T74-tour-benchmark.md).

Với mỗi n điểm giao, sinh `--sets` bộ (seed), mỗi bộ = kho + n điểm trong SCC, cách nhau ≥ `--min-sep` m.
Mỗi bộ: dựng ma trận chi phí từ đồ thị (`services/tour.cost_matrix`, cùng hàm với `/api/tour`), rồi xếp thứ tự
bằng 4 phương án: thứ tự nhập, Nearest Neighbor, NN + 2-opt, Held–Karp (tối ưu, khi n + 1 ≤ 11).
Ghi `tour_measurements.csv` đúng 15 cột mà `plot_results.py` và `summarize_results.py` đọc.

Thời gian ghi riêng (U3): `matrix_ns` một lần mỗi bộ; `order_ns` là thời gian ra thứ tự của phương án đó
(NN + 2-opt tính cả NN); `route_ns` là thời gian nối các chặng thành tuyến và cộng chi phí.

Ví dụ:
    python scripts/run_tour.py --graph data/processed/hcm-benthanh-r2000-20261024.json --seed 42
    python scripts/run_benchmarks.py --suite tour --graph data/processed/hcm-benthanh-r2000-20261024.json --seed 42
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.algorithms.tour import HELD_KARP_MAX_POINTS, held_karp, nearest_neighbor, two_opt  # noqa: E402
from app.graph.geo import haversine_m  # noqa: E402
from app.graph.model import Graph, GraphMeta, load_graph  # noqa: E402
from app.graph.scenario import Snapshot, baseline_snapshot  # noqa: E402
from app.services.tour import cost_matrix  # noqa: E402

TOUR_COLUMNS = (
    "run_id", "suite", "dataset_id", "set_id", "n_stops", "seed", "depot_node", "stop_nodes",
    "method", "feasible", "cost_s", "order", "matrix_ns", "order_ns", "route_ns",
)
METHODS = ("input", "nearest_neighbor", "nearest_neighbor_2opt", "held_karp")


def _rel(path: Path) -> Path:
    try:
        return Path(path).resolve().relative_to(ROOT.resolve())
    except ValueError:
        return Path(path)


def sample_sets(graph: Graph, meta: GraphMeta, n_stops: int, count: int, seed: int,
                min_sep_m: float = 150.0, max_tries: int = 20000) -> list[list[int]]:
    """`count` bộ [kho, điểm 1..n] trong SCC, mọi cặp điểm cách nhau ≥ `min_sep_m` (U1). Tất định theo (seed, n)."""
    rng = random.Random(seed * 1000 + n_stops)
    pool = [i for i in range(len(graph.node_lat)) if meta.node_in_scc[i]]
    sets: list[list[int]] = []
    tries = 0
    while len(sets) < count:
        chosen: list[int] = []
        while len(chosen) < n_stops + 1:
            tries += 1
            if tries > max_tries:
                raise ValueError(f"không sinh đủ {count} bộ {n_stops} điểm cách nhau ≥ {min_sep_m} m "
                                 f"sau {max_tries} lần thử")
            v = rng.choice(pool)
            if all(v != u and haversine_m(graph.node_lat[v], graph.node_lon[v],
                                          graph.node_lat[u], graph.node_lon[u]) >= min_sep_m for u in chosen):
                chosen.append(v)
        sets.append(chosen)
    return sets


def plan_set(graph: Graph, snap: Snapshot, nodes: list[int]) -> dict:
    """Ma trận + 4 phương án cho một bộ `nodes` (chỉ số 0 là kho). Bộ có chặng không đi được → không khả thi (U4)."""
    t0 = time.perf_counter_ns()
    D, legs = cost_matrix(graph, snap, nodes)
    matrix_ns = time.perf_counter_ns() - t0
    n = len(nodes)
    feasible = all(D[i][j] < math.inf for i in range(n) for j in range(n) if i != j)
    methods: dict[str, dict] = {}
    if not feasible:
        for m in METHODS:
            methods[m] = {"cost_s": None, "order": [], "order_ns": 0, "route_ns": 0}
        return {"feasible": False, "matrix_ns": matrix_ns, "methods": methods}

    orders: dict[str, tuple[list[int], int]] = {"input": (list(range(n)), 0)}
    t0 = time.perf_counter_ns()
    nn = nearest_neighbor(D)
    nn_ns = time.perf_counter_ns() - t0
    orders["nearest_neighbor"] = (nn, nn_ns)
    t0 = time.perf_counter_ns()
    opt = two_opt(D, nn)
    orders["nearest_neighbor_2opt"] = (opt, nn_ns + time.perf_counter_ns() - t0)
    if n <= HELD_KARP_MAX_POINTS:
        t0 = time.perf_counter_ns()
        hk = held_karp(D)
        orders["held_karp"] = (hk, time.perf_counter_ns() - t0)

    for m in METHODS:
        if m not in orders:
            methods[m] = {"cost_s": None, "order": [], "order_ns": 0, "route_ns": 0}
            continue
        order, order_ns = orders[m]
        t0 = time.perf_counter_ns()
        closed = order + [0]
        edges = [e for a, b in zip(closed, closed[1:]) for e in legs[a][b]]
        cost = sum(snap.weights[e] for e in edges)
        route_ns = time.perf_counter_ns() - t0
        methods[m] = {"cost_s": cost, "order": [k - 1 for k in order[1:]], "order_ns": order_ns,
                      "route_ns": route_ns}
    return {"feasible": True, "matrix_ns": matrix_ns, "methods": methods}


def check_order_costs(rows: list[dict]) -> list[dict]:
    """Bộ khả thi: Held–Karp ≤ NN + 2-opt ≤ NN (2-opt chỉ nhận nước làm giảm chi phí). Rỗng là đạt."""
    bad = []
    by_set: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_set.setdefault(str(r["set_id"]), {})[r["method"]] = r
    for set_id, g in by_set.items():
        if g["input"]["feasible"] != "true" or not g["held_karp"]["cost_s"]:
            continue
        hk, opt, nn = (float(g[m]["cost_s"]) for m in ("held_karp", "nearest_neighbor_2opt", "nearest_neighbor"))
        if not (hk <= opt + 1e-6 and opt <= nn + 1e-6):
            bad.append({"set_id": set_id, "held_karp": hk, "nn_2opt": opt, "nn": nn})
    return bad


def main(argv: list[str] | None = None) -> int:
    # Console Windows mặc định cp1252: in tiếng Việt sẽ lỗi và thoát mã 1 (review #108, #109).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--graph", type=Path, default=Path("data/processed/hcm-benthanh-r2000-20261024.json"))
    ap.add_argument("--sizes", type=int, nargs="+", default=[4, 6, 8, 10])
    ap.add_argument("--sets", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-sep", type=float, default=150.0)
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)

    sys.path.insert(0, str(ROOT / "scripts"))
    from run_benchmarks import _get_git_info, collect_env

    graph_path = args.graph if args.graph.is_absolute() or args.graph.exists() else ROOT / args.graph
    graph, meta = load_graph(graph_path)
    snap = baseline_snapshot(graph)
    commit, _, dirty = _get_git_info()
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M')}-tour-{commit[:7]}"
    run_dir = Path(args.out) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if dirty:
        sys.stderr.write("Cảnh báo: repo đang có thay đổi chưa commit, run sẽ ghi git_dirty = true\n")

    rows: list[dict] = []
    set_id = 0
    infeasible = 0
    for n in args.sizes:
        for nodes in sample_sets(graph, meta, n, args.sets, args.seed, args.min_sep):
            res = plan_set(graph, snap, nodes)
            infeasible += 0 if res["feasible"] else 1
            for m in METHODS:
                r = res["methods"][m]
                rows.append({
                    "run_id": run_id, "suite": "tour", "dataset_id": graph.dataset_id, "set_id": set_id,
                    "n_stops": n, "seed": args.seed, "depot_node": nodes[0],
                    "stop_nodes": ";".join(map(str, nodes[1:])), "method": m,
                    "feasible": "true" if res["feasible"] else "false",
                    "cost_s": "" if r["cost_s"] is None else round(r["cost_s"], 6),
                    "order": ";".join(map(str, r["order"])), "matrix_ns": res["matrix_ns"],
                    "order_ns": r["order_ns"], "route_ns": r["route_ns"],
                })
            set_id += 1

    with (run_dir / "tour_measurements.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(TOUR_COLUMNS))
        w.writeheader()
        w.writerows(rows)
    (run_dir / "env.json").write_text(json.dumps(collect_env(_rel(graph_path)), indent=2, ensure_ascii=False),
                                      encoding="utf-8", newline="\n")
    config = {"run_id": run_id, "suite": "tour", "graph": str(_rel(graph_path)), "sizes": args.sizes,
              "sets": args.sets, "seed": args.seed, "min_sep_m": args.min_sep, "infeasible_sets": infeasible,
              "held_karp_max_points": HELD_KARP_MAX_POINTS}
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8",
                                         newline="\n")

    with (run_dir / "tour_measurements.csv").open(encoding="utf-8") as f:
        bad = check_order_costs(list(csv.DictReader(f)))
    if bad:
        (run_dir / "violations.json").write_text(json.dumps(bad, indent=2), encoding="utf-8", newline="\n")
        sys.stderr.write(f"Lỗi: {len(bad)} bộ vi phạm Held–Karp ≤ NN + 2-opt ≤ NN (xem violations.json)\n")
        return 1
    print(f"Xong: {run_dir} ({set_id} bộ, {infeasible} bộ không khả thi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
