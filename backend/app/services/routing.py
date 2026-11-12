"""Dịch vụ định tuyến, snap tọa độ và ghép hình học tuyến đường (docs/ARCHITECTURE.md mục 4.1, 5)."""

from __future__ import annotations

import time

from app.algorithms.astar import astar
from app.algorithms.dijkstra import dijkstra
from app.algorithms.heuristics import make_geo_heuristic
from app.algorithms.result import SearchResult
from app.api.schemas import (
    AlgorithmRouteResult,
    GeometryLineString,
    RouteRequest,
    RouteResponse,
    SnappedPoint,
    SnappedResponse,
)
from app.graph.closures import validate_blocked
from app.graph.model import Graph, GraphMeta
from app.graph.scenario import Scenario, Snapshot, build_snapshot
from app.graph.snap import SnapError, nearest_node

SNAP_MAX_M = 150.0   # PROJECT_BRIEF A6, DATA_MODEL 8.5


class RouteInputError(ValueError):
    """Request hợp lệ về kiểu nhưng sai với dữ liệu đang nạp (điểm quá xa, kịch bản/cạnh không có) → 422."""


def _snap(graph: Graph, meta: GraphMeta, lat: float, lon: float, which: str) -> tuple[int, float]:
    try:
        s = nearest_node(graph, meta, lat, lon, max_m=SNAP_MAX_M)
    except SnapError as err:
        raise RouteInputError(
            f"{which} cách mạng đường {err.distance_m:.0f} m, quá ngưỡng {SNAP_MAX_M:.0f} m. "
            "Hãy chọn điểm gần đường hơn.") from None
    return s.node_id, s.snap_distance_m


def request_snapshot(graph: Graph, meta: GraphMeta, scenario_id: str | None, blocked_edge_ids: list[int],
                     scenarios: dict[str, Scenario]) -> Snapshot:
    """Snapshot cho riêng một request: hệ số ùn tắc của kịch bản + cạnh đóng (D4: không cache)."""
    if scenario_id is None:              # chỉ null mới là baseline; chuỗi rỗng là id không có → 422
        scenario_id = "baseline"
    if scenario_id not in scenarios:
        raise RouteInputError(f"Không có kịch bản {scenario_id!r}; các kịch bản đang có: {', '.join(scenarios)}")
    try:
        blocked = validate_blocked(graph, blocked_edge_ids)
    except ValueError as err:
        raise RouteInputError(f"Cạnh đóng không hợp lệ: {err}") from None
    return build_snapshot(graph, meta, scenarios[scenario_id], blocked)


def edge_coords(graph: Graph, meta: GraphMeta, e: int) -> list[list[float]]:
    """Hình học [lon, lat] của một cạnh; thiếu thì dùng đoạn thẳng nối hai đầu."""
    geom = meta.edge_geometry[e]
    if geom:
        return geom
    u, v = graph.edge_u[e], graph.edge_v[e]
    return [[graph.node_lon[u], graph.node_lat[u]], [graph.node_lon[v], graph.node_lat[v]]]


def network_lines(graph: Graph, meta: GraphMeta, twins: list[int | None]) -> list[list[list[float]]]:
    """Hình học mọi đoạn đường để vẽ nền (T56 R8); cạnh có cạnh đối chỉ lấy cạnh id nhỏ hơn."""
    return [edge_coords(graph, meta, e) for e in range(len(graph.edge_u)) if twins[e] is None or e < twins[e]]


def build_geometry(
    graph: Graph,
    meta: GraphMeta,
    source_node: int,
    edge_ids: list[int],
    status: str,
) -> GeometryLineString:
    """Tạo GeoJSON LineString từ danh sách cạnh đã đi, tọa độ [lon, lat]."""
    if status != "ok":
        return GeometryLineString(type="LineString", coordinates=[])

    if not edge_ids:
        # Trường hợp source == target (không qua cạnh nào)
        return GeometryLineString(
            type="LineString",
            coordinates=[[graph.node_lon[source_node], graph.node_lat[source_node]]],
        )

    coords: list[list[float]] = []
    for idx, e in enumerate(edge_ids):
        geom = edge_coords(graph, meta, e)
        if idx == 0:
            coords.extend(geom)
        else:
            if coords and geom and coords[-1] == geom[0]:
                coords.extend(geom[1:])
            else:
                coords.extend(geom)

    return GeometryLineString(type="LineString", coordinates=coords)


def _run_algorithm(
    algo: str,
    graph: Graph,
    snap: Snapshot,
    s_node: int,
    t_node: int,
    trace_limit: int,
) -> tuple[SearchResult, float]:
    """Chạy thuật toán và đo thời gian thực thi (ms) bằng perf_counter_ns."""
    if algo == "dijkstra":
        t0 = time.perf_counter_ns()
        res = dijkstra(graph, snap, s_node, t_node, trace_limit=trace_limit)
        t1 = time.perf_counter_ns()
    else:  # astar (RouteRequest schema đã đảm bảo chỉ có "dijkstra" hoặc "astar")
        t0 = time.perf_counter_ns()
        # Dựng heuristic tính vào thời gian A*, cùng định nghĩa với benchmark (EXPERIMENT_PLAN 3.1 bước 5).
        # Chỉ tốn O(1) vì geo_scale đã tính sẵn lúc khởi động (main.py).
        h = make_geo_heuristic(graph, t_node)
        res = astar(graph, snap, s_node, t_node, h, trace_limit=trace_limit)
        t1 = time.perf_counter_ns()

    runtime_ms = (t1 - t0) / 1_000_000.0
    return res, round(runtime_ms, 3)


def route(
    graph: Graph,
    meta: GraphMeta,
    req: RouteRequest,
    scenarios: dict[str, Scenario],
    twins: list[int | None],
) -> RouteResponse:
    """Xử lý yêu cầu tìm đường theo contract v1 (ARCHITECTURE mục 4). Sai dữ liệu → RouteInputError."""
    snap = request_snapshot(graph, meta, req.scenario_id, req.blocked_edge_ids, scenarios)

    # 1. Snap điểm đầu và điểm cuối về node gần nhất trong SCC, tối đa 150 m
    s_node, s_dist = _snap(graph, meta, req.source.lat, req.source.lon, "Điểm đi")
    t_node, t_dist = _snap(graph, meta, req.target.lat, req.target.lon, "Điểm đến")

    snapped = SnappedResponse(
        source=SnappedPoint(
            node_id=s_node,
            lat=graph.node_lat[s_node],
            lon=graph.node_lon[s_node],
            snap_distance_m=s_dist,
        ),
        target=SnappedPoint(
            node_id=t_node,
            lat=graph.node_lat[t_node],
            lon=graph.node_lon[t_node],
            snap_distance_m=t_dist,
        ),
    )

    # 3. Đo lường và chạy các thuật toán được yêu cầu
    results: dict[str, AlgorithmRouteResult] = {}

    for algo in req.algorithms:
        res, runtime_ms = _run_algorithm(algo, graph, snap, s_node, t_node, req.trace_limit)
        geom = build_geometry(graph, meta, s_node, res.edge_ids, res.status)
        trace_coords = [[graph.node_lon[nid], graph.node_lat[nid]] for nid in res.trace]

        results[algo] = AlgorithmRouteResult(
            status=res.status,
            cost_s=res.cost_s,
            distance_m=res.distance_m,
            edge_ids=res.edge_ids,
            edge_twin_ids=[twins[e] for e in res.edge_ids],
            edge_geometries=[edge_coords(graph, meta, e) for e in res.edge_ids],
            geometry=geom,
            expanded=res.expanded,
            runtime_ms=runtime_ms,
            trace=trace_coords,
            trace_truncated=res.trace_truncated,
        )

    # 4. Kiểm tra costs_match khi có cả Dijkstra và A*
    costs_match = None
    if "dijkstra" in results and "astar" in results:
        res_d = results["dijkstra"]
        res_a = results["astar"]
        if res_d.status == "ok" and res_a.status == "ok":
            cd = res_d.cost_s
            ca = res_a.cost_s
            if cd is not None and ca is not None:
                costs_match = abs(cd - ca) <= 1e-6 * max(1.0, cd)
        elif res_d.status == "no_path" and res_a.status == "no_path":
            costs_match = True
        else:
            costs_match = False

    return RouteResponse(
        dataset_id=graph.dataset_id,
        snapshot_id=snap.snapshot_id,
        snapped=snapped,
        results=results,
        costs_match=costs_match,
        warnings=[],
    )
