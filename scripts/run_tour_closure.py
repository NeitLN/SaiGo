"""R2 — tour sau khi đóng đường: giữ thứ tự cũ so với sắp lại (proposal slide 12; ROADMAP mục 7, R2).

Với mỗi bộ điểm (cùng cách sinh với E5: `run_tour.sample_sets`, cùng seed thì cùng bộ):
1. Trên kịch bản cơ sở, dựng ma trận và chọn tour như `/api/tour` (`choose_tour`: thứ tự nhập, NN, NN + 2-opt);
   đây là **tour cũ**.
2. Đóng cạnh ở giữa tuyến của tour cũ (vị trí ⌊k/2⌋ trong k cạnh) và cạnh đối nếu có, như "đóng đoạn" trên UI.
3. Trên snapshot mới: **giữ thứ tự cũ** = đúng thứ tự đó, mỗi chặng tìm lại; **sắp lại** = `choose_tour` lại.
   Có chặng không đi được thì bộ đó không khả thi sau khi đóng (đếm, không tính phần trăm).

Ghi `tour_closure.csv`, `env.json`, `config.json`. Bất biến kiểm khi chạy: giữ thứ tự cũ không rẻ hơn tour cũ
(đóng cạnh chỉ làm đường dài ra) và không tuyến nào đi qua cạnh đóng; vi phạm thì ghi `violations.json`, mã 1.

Ví dụ:
    python scripts/run_tour_closure.py --graph data/processed/hcm-benthanh-r2000-20261024.json --sizes 5 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.algorithms.tour import choose_tour, tour_cost  # noqa: E402
from app.graph.closures import reverse_twins  # noqa: E402
from app.graph.model import Graph, GraphMeta, load_graph  # noqa: E402
from app.graph.scenario import baseline_snapshot, make_snapshot  # noqa: E402
from app.services.tour import cost_matrix  # noqa: E402
from run_tour import _rel, sample_sets  # noqa: E402

CLOSURE_COLUMNS = (
    "run_id", "dataset_id", "set_id", "n_stops", "seed", "depot_node", "stop_nodes", "blocked_edges",
    "feasible_after", "old_method", "old_order", "old_cost_s", "kept_cost_s", "reordered_method", "reordered_order",
    "reordered_cost_s", "order_changed",
)


def _route_edges(legs: list[list[list[int]]], order: list[int]) -> list[int]:
    closed = list(order) + [order[0]]
    return [e for a, b in zip(closed, closed[1:]) for e in legs[a][b]]


def close_and_replan(graph: Graph, meta: GraphMeta, twins: list[int | None], nodes: list[int],
                     edge_index: int | None = None) -> dict:
    """Một bộ `nodes` (chỉ số 0 là kho). `edge_index`: vị trí cạnh đóng trên tuyến cũ (mặc định ⌊k/2⌋)."""
    D0, legs0 = cost_matrix(graph, baseline_snapshot(graph), nodes)
    n = len(nodes)
    if any(D0[i][j] == math.inf for i in range(n) for j in range(n) if i != j):
        return {"feasible_before": False}
    before = choose_tour(D0, list(range(n)))
    old = before.order
    edges = _route_edges(legs0, old)
    k = len(edges) // 2 if edge_index is None else edge_index
    e = edges[k]
    blocked = [e] + ([twins[e]] if twins[e] is not None else [])
    snap1 = make_snapshot(graph, graph.edge_base_time_s, frozenset(blocked), scenario_id="baseline")
    D1, legs1 = cost_matrix(graph, snap1, nodes)
    out = {"feasible_before": True, "blocked": blocked, "old_method": before.method, "old_order": old,
           "old_cost": before.cost_s}
    if any(D1[i][j] == math.inf for i in range(n) for j in range(n) if i != j):
        return {**out, "feasible_after": False}
    after = choose_tour(D1, list(range(n)))
    return {**out, "feasible_after": True, "kept_cost": tour_cost(D1, old),
            "kept_edges": _route_edges(legs1, old), "reordered_method": after.method,
            "reordered_order": after.order, "reordered_cost": after.cost_s,
            "reordered_edges": _route_edges(legs1, after.order)}


def check_invariants(results: list[dict]) -> list[dict]:
    """Giữ thứ tự cũ ≥ tour cũ; không tuyến nào đi qua cạnh đóng. Rỗng là đạt."""
    bad = []
    for set_id, r in enumerate(results):
        if not r.get("feasible_after"):
            continue
        if r["kept_cost"] < r["old_cost"] - 1e-6 * max(1.0, r["old_cost"]):
            bad.append({"set_id": set_id, "reason": "giữ thứ tự cũ rẻ hơn tour cũ"})
        if set(r["blocked"]) & (set(r["kept_edges"]) | set(r["reordered_edges"])):
            bad.append({"set_id": set_id, "reason": "tuyến đi qua cạnh đóng"})
    return bad


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--graph", type=Path, default=Path("data/processed/hcm-benthanh-r2000-20261024.json"))
    ap.add_argument("--sizes", type=int, nargs="+", default=[5])
    ap.add_argument("--sets", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-sep", type=float, default=150.0)
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)

    from run_benchmarks import _get_git_info, collect_env

    graph_path = args.graph if args.graph.is_absolute() or args.graph.exists() else ROOT / args.graph
    graph, meta = load_graph(graph_path)
    twins = reverse_twins(graph, meta)
    try:
        all_sets = [(n, sample_sets(graph, meta, n, args.sets, args.seed, args.min_sep)) for n in args.sizes]
    except ValueError as err:
        sys.stderr.write(f"Lỗi: {err}\n")
        return 2

    commit, _, dirty = _get_git_info()
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M')}-tourclosure-{commit[:7]}"
    if dirty:
        sys.stderr.write("Cảnh báo: repo đang có thay đổi chưa commit, run sẽ ghi git_dirty = true\n")

    results, rows = [], []
    for n, sets in all_sets:
        for nodes in sets:
            r = close_and_replan(graph, meta, twins, nodes)
            results.append(r)
            if not r["feasible_before"]:
                continue
            ok = r["feasible_after"]
            rows.append({
                "run_id": run_id, "dataset_id": graph.dataset_id, "set_id": len(results) - 1, "n_stops": n,
                "seed": args.seed, "depot_node": nodes[0], "stop_nodes": ";".join(map(str, nodes[1:])),
                "blocked_edges": ";".join(map(str, r["blocked"])), "feasible_after": "true" if ok else "false",
                "old_method": r["old_method"], "old_order": ";".join(map(str, r["old_order"][1:])),
                "old_cost_s": round(r["old_cost"], 6),
                "kept_cost_s": round(r["kept_cost"], 6) if ok else "",
                "reordered_method": r["reordered_method"] if ok else "",
                "reordered_order": ";".join(map(str, r["reordered_order"][1:])) if ok else "",
                "reordered_cost_s": round(r["reordered_cost"], 6) if ok else "",
                "order_changed": ("true" if r["reordered_order"] != r["old_order"] else "false") if ok else "",
            })

    # Tạo thư mục khi đã tính xong: lỗi giữa chừng không để lại run dở dang.
    run_dir = Path(args.out) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "tour_closure.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(CLOSURE_COLUMNS))
        w.writeheader()
        w.writerows(rows)
    (run_dir / "env.json").write_text(json.dumps(collect_env(_rel(graph_path)), indent=2, ensure_ascii=False),
                                      encoding="utf-8", newline="\n")
    skipped = sum(1 for r in results if not r["feasible_before"])
    config = {"run_id": run_id, "suite": "tourclosure", "graph": _rel(graph_path).as_posix(), "sizes": args.sizes,
              "sets": args.sets, "seed": args.seed, "min_sep_m": args.min_sep,
              "closure_rule": "cạnh ở vị trí floor(k/2) trên tuyến của tour cũ (choose_tour) + cạnh đối nếu có",
              "skipped_infeasible_before": skipped}
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8",
                                         newline="\n")
    bad = check_invariants(results)
    if bad:
        (run_dir / "violations.json").write_text(json.dumps(bad, indent=2, ensure_ascii=False), encoding="utf-8",
                                                 newline="\n")
        sys.stderr.write(f"Lỗi: {len(bad)} vi phạm bất biến (xem violations.json)\n")
        return 1
    infeasible = sum(1 for r in rows if r["feasible_after"] == "false")
    print(f"Xong: {run_dir} ({len(rows)} bộ, {infeasible} bộ không khả thi sau khi đóng, bỏ {skipped} bộ "
          "không khả thi từ đầu)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
