"""CLI tìm đường: chạy Dijkstra/A* từ dòng lệnh để kiểm tra và giải thích (docs/tasks/T12-cli.md).

    python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo both
    python -m app.cli route --graph <file> --from-latlon 10.7725,106.6980 --to-latlon 10.7730,106.7050

Thời gian chạy đo bằng perf_counter_ns chỉ quanh lời gọi thuật toán (dùng chung `_run_algorithm`
với API), không tính phần nạp đồ thị hay snap tọa độ.
"""

from __future__ import annotations

import argparse
import sys

from app.algorithms.heuristics import geo_scale
from app.algorithms.result import SearchResult
from app.graph.model import Graph, GraphMeta, load_graph, node_by_name
from app.graph.scenario import baseline_snapshot
from app.graph.snap import nearest_node
from app.services.routing import _run_algorithm

ALGOS = {"dijkstra": ["dijkstra"], "astar": ["astar"], "both": ["dijkstra", "astar"]}
LABEL = {"dijkstra": "Dijkstra", "astar": "A*"}


def _latlon(text: str) -> tuple[float, float]:
    try:
        lat, lon = (float(x) for x in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"tọa độ {text!r} phải có dạng lat,lon") from None
    return lat, lon


def _endpoint(graph: Graph, meta: GraphMeta, name: str | None,
              latlon: tuple[float, float] | None) -> tuple[int, str]:
    """Trả (node id, mô tả) từ tên node hoặc tọa độ đã snap."""
    if name is not None:
        return node_by_name(meta, name), name
    snap = nearest_node(graph, meta, *latlon)
    return snap.node_id, f"{latlon[0]},{latlon[1]} → node {snap.node_id} (snap {snap.snap_distance_m:.1f} m)"


def _node_label(meta: GraphMeta, node: int) -> str:
    name = meta.node_name[node]
    return name if name else str(node)


def _print_result(meta: GraphMeta, algo: str, res: SearchResult, runtime_ms: float) -> None:
    print(f"[{LABEL[algo]}]")
    if res.status != "ok":
        print("  Tuyến: không có đường đi")
    else:
        print("  Tuyến: " + " → ".join(_node_label(meta, v) for v in res.node_ids))
        print(f"  Chi phí: {res.cost_s:.1f} s")
        print(f"  Quãng đường: {res.distance_m:.1f} m")
    print(f"  expanded: {res.expanded}")
    print(f"  Thời gian chạy: {runtime_ms:.3f} ms")


def costs_match(a: SearchResult, b: SearchResult) -> bool:
    """Cùng quy tắc so chi phí với API (services/routing.py)."""
    if a.status == "ok" and b.status == "ok":
        return abs(a.cost_s - b.cost_s) <= 1e-6 * max(1.0, a.cost_s)
    return a.status == b.status


def cmd_route(args: argparse.Namespace) -> int:
    try:
        graph, meta = load_graph(args.graph)
    except (OSError, ValueError) as exc:
        print(f"Lỗi: không nạp được đồ thị {args.graph}: {exc}", file=sys.stderr)
        return 2
    # Tính sẵn c (duyệt mọi cạnh, có cache) để thời gian đo của A* không tính bước này.
    geo_scale(graph)
    try:
        s, s_desc = _endpoint(graph, meta, args.source, args.from_latlon)
        t, t_desc = _endpoint(graph, meta, args.target, args.to_latlon)
    except (KeyError, ValueError) as exc:
        print(f"Lỗi: {exc.args[0] if exc.args else exc}", file=sys.stderr)
        return 2

    print(f"Đồ thị: {graph.dataset_id} ({len(graph.node_lat)} node, {len(graph.edge_u)} cạnh)")
    print(f"Từ: {s_desc}")
    print(f"Đến: {t_desc}")

    snap = baseline_snapshot(graph)
    results = {}
    for algo in ALGOS[args.algo]:
        res, runtime_ms = _run_algorithm(algo, graph, snap, s, t, trace_limit=0)
        results[algo] = res
        _print_result(meta, algo, res, runtime_ms)

    if args.algo == "both":
        match = costs_match(results["dijkstra"], results["astar"])
        print(f"Chi phí trùng khớp: {'có' if match else 'không'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Tìm đường SaiGo từ dòng lệnh.")
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route", help="tìm đường ngắn nhất (theo thời gian) giữa hai điểm")
    route.add_argument("--graph", required=True, help="file đồ thị JSON (ví dụ tests/fixtures/mini.json)")
    src = route.add_mutually_exclusive_group(required=True)
    src.add_argument("--from", dest="source", help="tên node điểm đi")
    src.add_argument("--from-latlon", type=_latlon, help="tọa độ điểm đi, dạng lat,lon")
    dst = route.add_mutually_exclusive_group(required=True)
    dst.add_argument("--to", dest="target", help="tên node điểm đến")
    dst.add_argument("--to-latlon", type=_latlon, help="tọa độ điểm đến, dạng lat,lon")
    route.add_argument("--algo", choices=list(ALGOS), default="both", help="thuật toán (mặc định: both)")
    route.set_defaults(func=cmd_route)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")   # Windows: tránh lỗi in tiếng Việt khi chuyển hướng ra file
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
