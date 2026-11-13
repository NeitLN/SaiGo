"""CLI tìm đường và lập tour: chạy Dijkstra, A*, ALT, Dijkstra hai chiều và tour từ dòng lệnh (T12, A18).

    python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo all
    python -m app.cli route --graph <file> --from-latlon 10.7725,106.6980 --to-latlon 10.7730,106.7050
    python -m app.cli route --graph <file> --from S --to T --scenario peak-center --block 12 13
    python -m app.cli check-heuristic --graph data/processed/<file>.json
    python -m app.cli tour --graph <file> --case kho-5-diem --optimal --or-opt
    python -m app.cli tour --graph <file> --depot 10.7722,106.6976 --stop 10.7796,106.6988 10.7764,106.7027

`route` hỗ trợ 4 thuật toán (`dijkstra`, `astar`, `alt`, `bidijkstra`, `both`, `all`); `check-heuristic`
kiểm điều kiện độ dài heuristic A*; `tour` lập tour nhiều điểm khép kín về kho qua `plan_tour`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.algorithms.heuristics import geo_scale, heuristic_report
from app.algorithms.result import SearchResult
from app.api.schemas import LatLon, TourRequest, TourStop
from app.graph.closures import validate_blocked
from app.graph.model import Graph, GraphMeta, load_graph, node_by_name
from app.graph.scenario import build_snapshot, load_scenarios
from app.graph.snap import nearest_node
from app.services.routing import RouteInputError, _run_algorithm, _snap
from app.services.tour import plan_tour

ALGOS = {
    "dijkstra": ["dijkstra"],
    "astar": ["astar"],
    "alt": ["alt"],
    "bidijkstra": ["bidijkstra"],
    "both": ["dijkstra", "astar"],
    "all": ["dijkstra", "astar", "alt", "bidijkstra"],
}
LABEL = {
    "dijkstra": "Dijkstra",
    "astar": "A*",
    "alt": "ALT",
    "bidijkstra": "Dijkstra hai chiều",
}
# Gốc repo tính từ backend/app/cli.py; mặc định đọc đúng file kịch bản và case demo đã commit.
DEFAULT_SCENARIO_FILE = Path(__file__).resolve().parents[2] / "data" / "config" / "scenarios.json"
DEFAULT_CASES_FILE = Path(__file__).resolve().parents[2] / "data" / "demo" / "cases.json"


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


def cmd_check_heuristic(args: argparse.Namespace) -> int:
    """In báo cáo điều kiện độ dài heuristic (DATA_MODEL 5.1): v_max, c, vi phạm, cạnh tệ nhất."""
    try:
        graph, _ = load_graph(args.graph)
    except (OSError, ValueError) as exc:
        print(f"Lỗi: không nạp được đồ thị {args.graph}: {exc}", file=sys.stderr)
        return 2
    report = heuristic_report(graph)
    print(f"Đồ thị: {graph.dataset_id} ({len(graph.node_lat)} node, {len(graph.edge_u)} cạnh)")
    print(f"v_max: {report.v_max_mps:.6f} m/s ({report.v_max_mps * 3.6:.1f} km/h)")
    print(f"c: {report.c:.10f}")
    print(f"Số cạnh vi phạm (length < haversine − 1 mm): {report.n_violations}")
    if report.worst:
        print("Cạnh tệ nhất (tối đa 5, tỉ lệ length/haversine nhỏ nhất):")
        for v in report.worst:
            print(f"  cạnh {v.edge_id}: length {v.length_m:.3f} m · "
                  f"haversine {v.haversine_m:.3f} m · tỉ lệ {v.ratio:.6f}")
    if report.c < 0.999:
        print(f"Cảnh báo: c = {report.c:.6f} < 0.999 — điều tra cạnh vi phạm (DATA_MODEL 5.1).")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    cases_data = None
    case = None
    if args.case:
        cases_path = Path(args.cases_file)
        try:
            cases_data = json.loads(cases_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"Lỗi: không nạp được file case demo {args.cases_file}: {exc}", file=sys.stderr)
            return 2
        case = next((c for c in cases_data.get("cases", []) if c.get("id") == args.case), None)
        if case is None:
            print(f"Lỗi: không tìm thấy case demo {args.case!r} trong {args.cases_file}", file=sys.stderr)
            return 2
        if case.get("mode") != "route":
            print(f"Lỗi: case {args.case!r} có mode {case.get('mode')!r}, không phải route (cần mode 'route')",
                  file=sys.stderr)
            return 2

    graph_path = args.graph
    if not graph_path:
        if case and cases_data:
            ds_id = cases_data.get("dataset_id")
            candidate = Path("data/processed") / f"{ds_id}.json"
            if not candidate.exists():
                candidate = Path(__file__).resolve().parents[2] / "data" / "processed" / f"{ds_id}.json"
            if candidate.exists():
                graph_path = str(candidate)
        if not graph_path:
            print("Lỗi: cần truyền file đồ thị qua --graph", file=sys.stderr)
            return 2

    try:
        graph, meta = load_graph(graph_path)
    except (OSError, ValueError) as exc:
        print(f"Lỗi: không nạp được đồ thị {graph_path}: {exc}", file=sys.stderr)
        return 2

    try:
        scenarios = load_scenarios(args.scenario_file)
    except (OSError, ValueError) as exc:
        print(f"Lỗi: không nạp được file kịch bản {args.scenario_file}: {exc}", file=sys.stderr)
        return 2

    if case:
        scenario_name = args.scenario if args.scenario is not None else case.get("scenario_id", "baseline")
        block_list = args.block if args.block is not None else case.get("blocked_edge_ids", [])
    else:
        if not args.source and not args.from_latlon:
            print("Lỗi: cần truyền điểm đi qua --from hoặc --from-latlon (hoặc dùng --case)", file=sys.stderr)
            return 2
        if not args.target and not args.to_latlon:
            print("Lỗi: cần truyền điểm đến qua --to hoặc --to-latlon (hoặc dùng --case)", file=sys.stderr)
            return 2
        scenario_name = args.scenario if args.scenario is not None else "baseline"
        block_list = args.block if args.block is not None else []

    scenario = scenarios.get(scenario_name)
    if scenario is None:
        print(f"Lỗi: không có kịch bản {scenario_name!r}; các kịch bản đang có: "
              f"{', '.join(scenarios)}", file=sys.stderr)
        return 2

    try:
        blocked = validate_blocked(graph, block_list)
    except ValueError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2

    # Tính sẵn c (duyệt mọi cạnh, có cache) để thời gian đo của A* không tính bước này.
    geo_scale(graph)

    try:
        if case:
            src_pt = case["source"]
            dst_pt = case["target"]
            s_name = src_pt.get("name")
            s_node, s_dist = _snap(graph, meta, src_pt["lat"], src_pt["lon"],
                                   f"Điểm đi {s_name!r}" if s_name else "Điểm đi")
            s = s_node
            s_desc = (f"{s_name} ({src_pt['lat']},{src_pt['lon']}) → node {s_node} (snap {s_dist:.1f} m)"
                      if s_name else f"{src_pt['lat']},{src_pt['lon']} → node {s_node} (snap {s_dist:.1f} m)")

            t_name = dst_pt.get("name")
            t_node, t_dist = _snap(graph, meta, dst_pt["lat"], dst_pt["lon"],
                                   f"Điểm đến {t_name!r}" if t_name else "Điểm đến")
            t = t_node
            t_desc = (f"{t_name} ({dst_pt['lat']},{dst_pt['lon']}) → node {t_node} (snap {t_dist:.1f} m)"
                      if t_name else f"{dst_pt['lat']},{dst_pt['lon']} → node {t_node} (snap {t_dist:.1f} m)")
        else:
            s, s_desc = _endpoint(graph, meta, args.source, args.from_latlon)
            t, t_desc = _endpoint(graph, meta, args.target, args.to_latlon)
    except (RouteInputError, KeyError, ValueError) as exc:
        print(f"Lỗi: {exc.args[0] if exc.args else exc}", file=sys.stderr)
        return 2

    print(f"Đồ thị: {graph.dataset_id} ({len(graph.node_lat)} node, {len(graph.edge_u)} cạnh)")
    print(f"Từ: {s_desc}")
    print(f"Đến: {t_desc}")
    print(f"Kịch bản: {scenario.id} · đóng: {', '.join(map(str, sorted(blocked))) or 'không'}")

    snap = build_snapshot(graph, meta, scenario, blocked)
    results = {}
    for algo in ALGOS[args.algo]:
        res, runtime_ms = _run_algorithm(algo, graph, snap, s, t, trace_limit=0, meta=meta)
        results[algo] = res
        _print_result(meta, algo, res, runtime_ms)

    if "dijkstra" in results and "astar" in results:
        match = costs_match(results["dijkstra"], results["astar"])
        print(f"Chi phí trùng khớp: {'có' if match else 'không'}")
    if "dijkstra" in results and "alt" in results:
        match_alt = costs_match(results["dijkstra"], results["alt"])
        print(f"Chi phí ALT khớp Dijkstra: {'có' if match_alt else 'không'}")
    if "dijkstra" in results and "bidijkstra" in results:
        match_bi = costs_match(results["dijkstra"], results["bidijkstra"])
        print(f"Chi phí hai chiều khớp Dijkstra: {'có' if match_bi else 'không'}")
    return 0


def format_tour_table(res: TourResponse) -> str:
    method_names = {
        "input": "Thứ tự nhập",
        "nearest_neighbor": "Nearest Neighbor",
        "nearest_neighbor_2opt": "NN + 2-opt",
        "nearest_neighbor_2opt_oropt": "NN + 2-opt + Or-opt",
        "optimal": "Held–Karp (tối ưu)",
    }

    c_input = res.candidates["input"].cost_s
    c_opt = res.optimal.cost_s if res.optimal else None

    rows: list[list[str]] = []
    for key in ["input", "nearest_neighbor", "nearest_neighbor_2opt", "nearest_neighbor_2opt_oropt"]:
        if key not in res.candidates:
            continue
        cand = res.candidates[key]
        method_label = method_names[key] + (" *" if key == res.chosen else "")
        order_str = " → ".join(cand.stop_order)
        cost_str = f"{cand.cost_s:.1f} s ({cand.cost_s / 60:.1f} phút)"
        dist_str = f"{cand.distance_m:.1f} m"
        imp_str = f"{cand.improvement_pct:+.2f}%" if abs(cand.improvement_pct) > 1e-4 else "0.00%"
        row = [method_label, order_str, cost_str, dist_str, imp_str]
        if res.optimal:
            gap = 100.0 * (cand.cost_s - c_opt) / c_opt if c_opt > 0 else 0.0
            gap_str = "0.00%" if abs(gap) < 1e-4 else f"{gap:+.2f}%"
            row.append(gap_str)
        rows.append(row)

    if res.optimal:
        opt = res.optimal
        opt_label = method_names["optimal"]
        order_str = " → ".join(opt.stop_order)
        cost_str = f"{opt.cost_s:.1f} s ({opt.cost_s / 60:.1f} phút)"
        dist_val = next((cand.distance_m for cand in res.candidates.values()
                         if cand.stop_order == opt.stop_order), None)
        dist_str = f"{dist_val:.1f} m" if dist_val is not None else "-"
        imp_val = 100.0 * (c_input - opt.cost_s) / c_input if c_input > 0 else 0.0
        imp_str = f"{imp_val:+.2f}%" if abs(imp_val) > 1e-4 else "0.00%"
        rows.append([opt_label, order_str, cost_str, dist_str, imp_str, "0.00%"])

    headers = ["Phương án", "Thứ tự điểm", "Chi phí", "Quãng đường", "Cải thiện"]
    if res.optimal:
        headers.append("Gap tối ưu")

    widths = [len(h) for h in headers]
    for r in rows:
        for i, val in enumerate(r):
            widths[i] = max(widths[i], len(str(val)))

    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "  ".join("-" * widths[i] for i in range(len(headers)))
    data_lines = [
        "  ".join(str(val).ljust(widths[i]) if i < 2 else str(val).rjust(widths[i])
                  for i, val in enumerate(r))
        for r in rows
    ]
    return "\n".join([header_line, sep_line] + data_lines)


def cmd_tour(args: argparse.Namespace) -> int:
    case = None
    cases_data = None
    if args.case:
        cases_path = Path(args.cases_file)
        try:
            cases_data = json.loads(cases_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"Lỗi: không nạp được file case demo {args.cases_file}: {exc}", file=sys.stderr)
            return 2
        case = next((c for c in cases_data.get("cases", []) if c.get("id") == args.case), None)
        if case is None:
            print(f"Lỗi: không tìm thấy case demo {args.case!r} trong {args.cases_file}", file=sys.stderr)
            return 2
        if case.get("mode") != "tour":
            print(f"Lỗi: case {args.case!r} có mode {case.get('mode')!r}, không phải tour (cần mode 'tour')",
                  file=sys.stderr)
            return 2

        depot_info = case.get("depot")
        stops_info = case.get("stops", [])
        if not depot_info or not stops_info:
            print(f"Lỗi: case {args.case!r} thiếu thông tin kho hoặc điểm giao", file=sys.stderr)
            return 2

        depot = LatLon(lat=depot_info["lat"], lon=depot_info["lon"])
        depot_name = depot_info.get("name", "Kho")
        stops = [
            TourStop(id=s.get("name") or f"stop_{i+1}", lat=s["lat"], lon=s["lon"])
            for i, s in enumerate(stops_info)
        ]
        scenario_id = args.scenario if args.scenario is not None else case.get("scenario_id", "baseline")
        block_edges = args.block if args.block is not None else case.get("blocked_edge_ids", [])

        graph_path = args.graph
        if not graph_path:
            ds_id = cases_data.get("dataset_id")
            candidate = Path("data/processed") / f"{ds_id}.json"
            if not candidate.exists():
                candidate = Path(__file__).resolve().parents[2] / "data" / "processed" / f"{ds_id}.json"
            if candidate.exists():
                graph_path = str(candidate)
            else:
                print("Lỗi: chưa có file đồ thị. Hãy truyền --graph <đường_dẫn>", file=sys.stderr)
                return 2
    else:
        if not args.depot:
            print("Lỗi: cần truyền --case <id> hoặc tọa độ kho qua --depot lat,lon", file=sys.stderr)
            return 2
        if not args.stops:
            print("Lỗi: cần ít nhất một điểm giao qua --stop lat,lon", file=sys.stderr)
            return 2
        if not args.graph:
            print("Lỗi: cần truyền file đồ thị qua --graph", file=sys.stderr)
            return 2

        graph_path = args.graph
        depot = LatLon(lat=args.depot[0], lon=args.depot[1])
        depot_name = "Kho"
        stops = [
            TourStop(id=f"stop_{i+1}", lat=lat, lon=lon)
            for i, (lat, lon) in enumerate(args.stops)
        ]
        scenario_id = args.scenario if args.scenario is not None else "baseline"
        block_edges = args.block if args.block is not None else []

    try:
        graph, meta = load_graph(graph_path)
    except (OSError, ValueError) as exc:
        print(f"Lỗi: không nạp được đồ thị {graph_path}: {exc}", file=sys.stderr)
        return 2

    try:
        scenarios = load_scenarios(args.scenario_file)
    except (OSError, ValueError) as exc:
        print(f"Lỗi: không nạp được file kịch bản {args.scenario_file}: {exc}", file=sys.stderr)
        return 2

    try:
        req = TourRequest(
            depot=depot,
            stops=stops,
            scenario_id=scenario_id,
            blocked_edge_ids=block_edges,
            include_optimal=args.optimal,
            include_or_opt=args.or_opt,
        )
        res = plan_tour(graph, meta, req, scenarios)
    except (RouteInputError, ValueError) as exc:
        print(f"Lỗi: {exc.args[0] if exc.args else exc}", file=sys.stderr)
        return 2

    print(f"Đồ thị: {graph.dataset_id} ({len(graph.node_lat)} node, {len(graph.edge_u)} cạnh)")
    depot_snap = res.snapped.get("depot")
    if depot_snap:
        desc_name = f"{depot_name} " if depot_name != "Kho" else ""
        print(f"Kho: {desc_name}({depot.lat:.6f}, {depot.lon:.6f}) → node {depot_snap.node_id} "
              f"(snap {depot_snap.snap_distance_m:.1f} m)")
    print(f"Số điểm giao: {len(req.stops)}")
    print(f"Kịch bản: {scenario_id} · đóng: {', '.join(map(str, sorted(block_edges))) or 'không'}")

    if res.status == "infeasible_under_model":
        print()
        print("Trạng thái: Không thể lập tour (infeasible_under_model)")
        if res.unreachable:
            print("Các chặng không thể đi được:")
            for pair in res.unreachable:
                print(f"  {pair.from_id} → {pair.to_id}")
        for w in res.warnings:
            print(f"Cảnh báo: {w}")
        return 1

    print()
    print(format_tour_table(res))
    print()
    method_names = {
        "input": "Thứ tự nhập",
        "nearest_neighbor": "Nearest Neighbor",
        "nearest_neighbor_2opt": "NN + 2-opt",
        "nearest_neighbor_2opt_oropt": "NN + 2-opt + Or-opt",
    }
    chosen_label = method_names.get(res.chosen, res.chosen or "")
    print(f"* Phương án được chọn: {chosen_label}")
    print(f"Thời gian tính ma trận: {res.matrix_runtime_ms:.3f} ms · "
          f"Sắp thứ tự: {res.order_runtime_ms:.3f} ms")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Tìm đường và lập tour SaiGo từ dòng lệnh.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ví dụ sử dụng:
  # Tìm đường ngắn nhất giữa hai điểm (mặc định so sánh Dijkstra và A*):
  python -m app.cli route --graph tests/fixtures/mini.json --from S --to T

  # Tìm đường với cả 4 thuật toán (Dijkstra, A*, ALT, Dijkstra hai chiều):
  python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo all

  # Kiểm tra điều kiện độ dài heuristic A* trên đồ thị:
  python -m app.cli check-heuristic --graph tests/fixtures/mini.json

  # Lập tour theo case demo có sẵn kèm tối ưu Held–Karp và Or-opt:
  python -m app.cli tour --graph data/processed/hcm-benthanh-r2000-20261024.json --case kho-5-diem --optimal --or-opt

  # Lập tour với tọa độ kho và các điểm giao tự chọn:
  python -m app.cli tour --graph tests/fixtures/mini.json --depot 10.77251,106.69801 --stop 10.77519,106.70166 --stop 10.77251,106.70532
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser(
        "route",
        help="tìm đường ngắn nhất (theo thời gian) giữa hai điểm",
        description="Tìm đường ngắn nhất giữa hai điểm bằng Dijkstra, A*, ALT, hoặc Dijkstra hai chiều.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ví dụ sử dụng lệnh route:
  python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo both
  python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo all
  python -m app.cli route --graph data/processed/hcm-benthanh-r2000-20261024.json --from-latlon 10.77871,106.69593 --to-latlon 10.77186,106.70391 --algo all
  python -m app.cli route --graph data/processed/hcm-benthanh-r2000-20261024.json --case hai-diem-qua-trung-tam --algo all
  python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --scenario un-tac-tam-a --block 1 2
""",
    )
    route.add_argument("--graph", help="file đồ thị JSON (ví dụ tests/fixtures/mini.json)")
    route.add_argument("--case", help="id case demo từ data/demo/cases.json (mode route, ví dụ hai-diem-qua-trung-tam)")
    route.add_argument("--cases-file", default=str(DEFAULT_CASES_FILE),
                       help="file case demo JSON (mặc định: data/demo/cases.json)")
    src = route.add_mutually_exclusive_group(required=False)
    src.add_argument("--from", dest="source", help="tên node điểm đi")
    src.add_argument("--from-latlon", type=_latlon, help="tọa độ điểm đi, dạng lat,lon")
    dst = route.add_mutually_exclusive_group(required=False)
    dst.add_argument("--to", dest="target", help="tên node điểm đến")
    dst.add_argument("--to-latlon", type=_latlon, help="tọa độ điểm đến, dạng lat,lon")
    route.add_argument("--algo", choices=list(ALGOS), default="both", help="thuật toán (mặc định: both)")
    route.add_argument("--scenario", default=None,
                       help="id kịch bản ùn tắc trong file kịch bản (mặc định: baseline)")
    route.add_argument("--scenario-file", default=str(DEFAULT_SCENARIO_FILE),
                       help="file kịch bản JSON (mặc định: data/config/scenarios.json ở gốc repo)")
    route.add_argument("--block", type=int, nargs="+", default=None, metavar="EDGE_ID",
                       help="id cạnh có hướng bị đóng (có thể truyền nhiều id)")
    route.set_defaults(func=cmd_route)

    check = sub.add_parser(
        "check-heuristic",
        help="kiểm tra điều kiện độ dài của heuristic A* trên đồ thị",
        description="Kiểm tra hệ số co c, vận tốc cực đại v_max và các cạnh vi phạm tam giác (DATA_MODEL 5.1).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ví dụ sử dụng lệnh check-heuristic:
  python -m app.cli check-heuristic --graph tests/fixtures/mini.json
  python -m app.cli check-heuristic --graph data/processed/hcm-benthanh-r2000-20261024.json
""",
    )
    check.add_argument("--graph", required=True,
                       help="file đồ thị JSON (ví dụ data/processed/<file>.json)")
    check.set_defaults(func=cmd_check_heuristic)

    tour = sub.add_parser(
        "tour",
        help="lập tour qua nhiều điểm giao khép kín về kho",
        description="Lập lộ trình giao hàng qua nhiều điểm (TSP khép kín về kho) từ dòng lệnh qua dịch vụ plan_tour.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Ví dụ sử dụng lệnh tour:
  # Lập tour theo case demo có sẵn kèm tối ưu Held–Karp và Or-opt:
  python -m app.cli tour --graph data/processed/hcm-benthanh-r2000-20261024.json --case kho-5-diem --optimal --or-opt

  # Lập tour với tọa độ kho và các điểm giao tự chọn:
  python -m app.cli tour --graph tests/fixtures/mini.json --depot 10.77251,106.69801 --stop 10.77519,106.70166 --stop 10.77251,106.70532

  # Lập tour có kịch bản ùn tắc và cạnh đóng:
  python -m app.cli tour --graph data/processed/hcm-benthanh-r2000-20261024.json --case kho-5-diem --scenario peak-center --block 100 101
""",
    )
    tour.add_argument("--graph", help="file đồ thị JSON (ví dụ tests/fixtures/mini.json)")
    tour.add_argument("--case", help="id case demo từ data/demo/cases.json (mode tour, ví dụ kho-5-diem)")
    tour.add_argument("--cases-file", default=str(DEFAULT_CASES_FILE),
                      help="file case demo JSON (mặc định: data/demo/cases.json)")
    tour.add_argument("--depot", type=_latlon, help="tọa độ kho (lat,lon), ví dụ 10.772193,106.697556")
    tour.add_argument("--stop", dest="stops", action="extend", nargs="+", type=_latlon,
                      help="tọa độ điểm giao (lat,lon), có thể truyền nhiều lần hoặc nhiều điểm")
    tour.add_argument("--scenario", default=None,
                      help="id kịch bản ùn tắc trong file kịch bản (mặc định: baseline)")
    tour.add_argument("--scenario-file", default=str(DEFAULT_SCENARIO_FILE),
                      help="file kịch bản JSON (mặc định: data/config/scenarios.json ở gốc repo)")
    tour.add_argument("--block", type=int, nargs="+", default=None, metavar="EDGE_ID",
                      help="id cạnh có hướng bị đóng")
    tour.add_argument("--optimal", action="store_true",
                      help="tìm tour tối ưu bằng quy hoạch động Held–Karp (tối đa 11 điểm cả kho)")
    tour.add_argument("--or-opt", action="store_true",
                      help="áp dụng cải tiến Or-opt xen kẽ 2-opt cho ma trận có hướng")
    tour.set_defaults(func=cmd_tour)

    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")   # Windows: tránh lỗi in tiếng Việt khi chuyển hướng ra file
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
