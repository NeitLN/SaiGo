"""E4 — ùn tắc và đóng đường (EXPERIMENT_PLAN mục 7; docs/tasks/T63-congestion-closure.md).

Một lần chạy, ba phần, chung một `run_id` và một `measurements.csv`:

- `suite = scenario` (C1): cùng tập cặp chạy dưới **mọi** kịch bản trong file kịch bản.
- `suite = closure` (C3): cặp có tuyến cơ sở ≥ 3 cạnh; đóng cạnh ở vị trí ⌊k/2⌋ của tuyến cơ sở và cạnh đối.
- `suite = nopath` (C4): đóng mọi cạnh đi vào đích; hai thuật toán phải kết luận `no_path`.

Với `closure`/`nopath`, mỗi cặp dựng snapshot riêng; thời gian dựng ghi riêng ở cột `snapshot_ns` (C5).
Cuối run kiểm bất biến; vi phạm → `violations.csv` và mã thoát 1.

Ví dụ:
    python scripts/run_scenarios.py --graph data/processed/hcm-benthanh-r2000-20261024.json --seed 42
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.algorithms.dijkstra import dijkstra  # noqa: E402
from app.algorithms.heuristics import make_geo_heuristic  # noqa: E402
from app.algorithms.astar import astar  # noqa: E402
from app.graph.closures import reverse_twins  # noqa: E402
from app.graph.model import Graph, load_graph  # noqa: E402
from app.graph.scenario import build_snapshot, load_scenarios  # noqa: E402
from run_benchmarks import (  # noqa: E402
    MEASUREMENT_COLUMNS,
    QUERY_COLUMNS,
    _get_git_info,
    collect_env,
    generate_queries,
    measure_query,
    resolve_side_m,
)

BASELINE = "baseline"


def _rel(path: Path) -> Path:
    """Đường dẫn tương đối với gốc repo nếu nằm trong repo (giống run E2)."""
    try:
        return Path(path).resolve().relative_to(ROOT.resolve())
    except ValueError:
        return Path(path)


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() or path.exists() else ROOT / path


def closure_edges(route: list[int], twins) -> list[int]:
    """C3: cạnh ở vị trí ⌊k/2⌋ của tuyến và cạnh đối của nó (nếu có), như thao tác "đóng đoạn" trên UI."""
    e = route[len(route) // 2]
    t = twins[e]
    return [e] if t is None else [e, t]


def nopath_edges(graph: Graph, target: int) -> list[int]:
    """C4: mọi cạnh đi vào đích."""
    return [e for e, v in enumerate(graph.edge_v) if v == target]


def check_invariants(rows: list[dict], closure_routes: dict, nopath_ids: set) -> list[dict]:
    """Bất biến E4. Rỗng là đạt.

    - ùn tắc chỉ làm trọng số tăng (α ≥ 1) → chi phí dưới mọi kịch bản ≥ chi phí cơ sở, và không mất đường;
    - đóng đoạn: tuyến mới không đi qua cạnh đóng, chi phí ≥ cơ sở (hoặc `no_path`);
    - không còn đường: `no_path` ở cả hai thuật toán.
    """
    bad = []
    base = {(r["query_id"], r["algo"]): r for r in rows
            if r["suite"] == "scenario" and r["scenario_id"] == BASELINE}
    for r in rows:
        key = (r["query_id"], r["algo"])
        b = base.get(key)
        if r["suite"] == "scenario" and r["scenario_id"] != BASELINE and b and b["status"] == "ok":
            if r["status"] != "ok":
                bad.append({"suite": r["suite"], "query_id": r["query_id"], "algo": r["algo"],
                            "reason": f"mất đường dưới {r['scenario_id']}"})
            elif float(r["cost_s"]) < float(b["cost_s"]) - 1e-6 * max(1.0, float(b["cost_s"])):
                bad.append({"suite": r["suite"], "query_id": r["query_id"], "algo": r["algo"],
                            "reason": f"{r['scenario_id']} rẻ hơn cơ sở: {r['cost_s']} < {b['cost_s']}"})
        if r["suite"] == "closure" and r["status"] == "ok":
            blocked, route = closure_routes[(r["query_id"], r["algo"])]
            if set(blocked) & set(route):
                bad.append({"suite": "closure", "query_id": r["query_id"], "algo": r["algo"],
                            "reason": "tuyến mới đi qua cạnh đóng"})
            if b and b["status"] == "ok" and float(r["cost_s"]) < float(b["cost_s"]) - 1e-6 * max(1.0, float(b["cost_s"])):
                bad.append({"suite": "closure", "query_id": r["query_id"], "algo": r["algo"],
                            "reason": "đóng đường mà chi phí giảm"})
        if r["suite"] == "nopath" and r["status"] != "no_path":
            bad.append({"suite": "nopath", "query_id": r["query_id"], "algo": r["algo"],
                        "reason": f"phải no_path, ra {r['status']}"})
    return bad


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _timed_snapshot(graph, meta, scenario, blocked: set, repeats: int):
    """Dựng snapshot `repeats` lần, trả (snapshot, median ns) — C5."""
    times, snap = [], None
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter_ns()
        snap = build_snapshot(graph, meta, scenario, blocked=blocked)
        times.append(time.perf_counter_ns() - t0)
    return snap, int(statistics.median(times))


def main(argv: list[str] | None = None) -> int:
    # Console Windows mặc định cp1252: in tiếng Việt sẽ lỗi và thoát mã 1 (review #108).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--graph", type=Path, default=Path("data/processed/hcm-benthanh-r2000-20261024.json"))
    ap.add_argument("--scenario-file", type=Path, default=Path("data/config/scenarios.json"))
    ap.add_argument("--pairs", type=int, default=300)
    ap.add_argument("--closure", type=int, default=100)
    ap.add_argument("--nopath", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)

    graph_path = _resolve(args.graph)
    graph, meta = load_graph(graph_path)
    scenarios = load_scenarios(_resolve(args.scenario_file))
    if BASELINE not in scenarios:
        sys.stderr.write(f"Lỗi: file kịch bản thiếu {BASELINE!r}\n")
        return 2
    twins = reverse_twins(graph, meta)

    commit, _, dirty = _get_git_info()
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M')}-scenario-{commit[:7]}"
    run_dir = Path(args.out) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if dirty:
        sys.stderr.write("Cảnh báo: repo đang có thay đổi chưa commit, run sẽ ghi git_dirty = true\n")

    l_val, l_source = resolve_side_m(graph_path, graph)
    queries, sampling = generate_queries(graph, meta, args.pairs, args.seed, workload="demo",
                                         l_box_m=l_val, l_source=l_source)

    # Warm-up một lần cho cả run (mục 3.1 bước 3), trên kịch bản cơ sở.
    base_snap = build_snapshot(graph, meta, scenarios[BASELINE], blocked=set())
    for q in queries[: min(args.warmup, len(queries))]:
        dijkstra(graph, base_snap, q["source"], q["target"], trace_limit=0)
        astar(graph, base_snap, q["source"], q["target"], make_geo_heuristic(graph, q["target"]), trace_limit=0)

    rows: list[dict] = []
    query_rows: list[dict] = []
    common = dict(run_id=run_id, size_label=graph.dataset_id)

    # C1: mọi kịch bản, cùng tập cặp
    for sid, scen in scenarios.items():
        snap = build_snapshot(graph, meta, scen, blocked=set())
        for i, q in enumerate(queries):
            q_rows, _, _ = measure_query(graph, snap, q, i, args.repeats, suite="scenario", blocked_count=0, **common)
            rows.extend(q_rows)
    query_rows += [{**q, "suite": "scenario", "blocked_edges": ""} for q in queries]

    # Tuyến cơ sở (không đo giờ) để chọn cặp C3 và lấy cạnh giữa tuyến
    base_route = {q["query_id"]: dijkstra(graph, base_snap, q["source"], q["target"], trace_limit=0) for q in queries}

    # C3: đóng đoạn giữa tuyến
    closure_routes: dict = {}
    picked = [q for q in queries if base_route[q["query_id"]].status == "ok"
              and len(base_route[q["query_id"]].edge_ids) >= 3][: args.closure]
    for i, q in enumerate(picked):
        blocked = closure_edges(base_route[q["query_id"]].edge_ids, twins)
        snap, snap_ns = _timed_snapshot(graph, meta, scenarios[BASELINE], set(blocked), args.repeats)
        q_rows, res_d, res_a = measure_query(graph, snap, q, i, args.repeats, suite="closure",
                                             blocked_count=len(blocked), snapshot_ns=snap_ns, **common)
        rows.extend(q_rows)
        closure_routes[(str(q["query_id"]), "dijkstra")] = (blocked, res_d.edge_ids)
        closure_routes[(str(q["query_id"]), "astar")] = (blocked, res_a.edge_ids)
        query_rows.append({**q, "suite": "closure", "blocked_edges": ";".join(map(str, blocked))})

    # C4: không còn đường
    nopath_ids = set()
    for i, q in enumerate(queries[: args.nopath]):
        blocked = nopath_edges(graph, q["target"])
        snap, snap_ns = _timed_snapshot(graph, meta, scenarios[BASELINE], set(blocked), args.repeats)
        q_rows, _, _ = measure_query(graph, snap, q, i, args.repeats, suite="nopath",
                                     blocked_count=len(blocked), snapshot_ns=snap_ns, **common)
        rows.extend(q_rows)
        nopath_ids.add(str(q["query_id"]))
        query_rows.append({**q, "suite": "nopath", "blocked_edges": ";".join(map(str, blocked))})

    _write_csv(run_dir / "measurements.csv", MEASUREMENT_COLUMNS, rows)
    _write_csv(run_dir / "queries.csv", QUERY_COLUMNS + ["suite", "blocked_edges"], query_rows)
    (run_dir / "env.json").write_text(json.dumps(collect_env(_rel(graph_path)), indent=2, ensure_ascii=False),
                                      encoding="utf-8", newline="\n")
    config = {"run_id": run_id, "graph": _rel(graph_path).as_posix(),
              "scenario_file": _rel(_resolve(args.scenario_file)).as_posix(),
              "scenarios": list(scenarios), "pairs": args.pairs, "closure": args.closure, "nopath": args.nopath,
              "closure_picked": len(picked), "seed": args.seed, "repeats": args.repeats, "warmup": args.warmup,
              "sampling": sampling}
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8",
                                         newline="\n")

    # csv.DictReader đọc lại thành chuỗi: kiểm trên đúng dạng sẽ được phân tích
    with (run_dir / "measurements.csv").open(encoding="utf-8") as f:
        written = list(csv.DictReader(f))
    violations = check_invariants(written, closure_routes, nopath_ids)
    if violations:
        _write_csv(run_dir / "violations.csv", ["suite", "query_id", "algo", "reason"], violations)
        sys.stderr.write(f"Lỗi: {len(violations)} vi phạm bất biến E4 (xem violations.csv)\n")
        return 1
    print(f"Xong: {run_dir} ({len(rows)} dòng đo; closure {len(picked)} cặp, nopath {len(nopath_ids)} cặp)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
