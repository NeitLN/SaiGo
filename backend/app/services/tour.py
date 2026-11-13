"""Tour nhiều điểm trên đồ thị: ma trận chi phí từ đồ thị, chọn thứ tự, ghép tuyến (T72; TOPIC mục 10).

Ma trận xây bằng Dijkstra một nguồn tới các điểm còn lại cho từng hàng, trên **cùng** snapshot của
request. Tuyến cuối được ghép từ đúng các chặng đã dùng để tính ma trận, nên chi phí tour bằng tổng
trọng số các cạnh của tuyến (không dùng khoảng cách thẳng). Có chặng không đi được thì trả
`infeasible_under_model` kèm các cặp lỗi, không bịa tour và không âm thầm bỏ điểm.
"""

from __future__ import annotations

import math
import time

from app.algorithms.dijkstra import dijkstra_many
from app.algorithms.result import build_route
from app.algorithms.tour import (
    HELD_KARP_MAX_POINTS,
    choose_tour,
    held_karp,
    nearest_neighbor,
    or_opt,
    tour_cost,
    two_opt,
)
from app.api.schemas import (
    SnappedStop,
    TourCandidate,
    TourOptimal,
    TourRequest,
    TourResponse,
    UnreachablePair,
)
from app.graph.closures import reverse_twins
from app.graph.model import Graph, GraphMeta
from app.graph.scenario import Scenario, Snapshot
from app.services.routing import RouteInputError, _snap, build_geometry, edge_coords, request_snapshot


def cost_matrix(graph: Graph, snap: Snapshot, nodes: list[int]) -> tuple[list[list[float]], list[list[list[int]]]]:
    """`D[i][j]` và cạnh của chặng i → j giữa các node `nodes` (chỉ số 0 là kho)."""
    n = len(nodes)
    D = [[0.0] * n for _ in range(n)]
    legs: list[list[list[int]]] = [[[] for _ in range(n)] for _ in range(n)]
    for i, src in enumerate(nodes):
        dist, pred = dijkstra_many(graph, snap, src, nodes)
        for j, dst in enumerate(nodes):
            if i == j:
                continue
            D[i][j] = dist[dst]
            if dist[dst] < math.inf:
                legs[i][j], _ = build_route(graph, pred, src, dst)
    return D, legs


def plan_tour(graph: Graph, meta: GraphMeta, req: TourRequest, scenarios: dict[str, Scenario],
              twins: list[int | None] | None = None) -> TourResponse:
    """Xử lý `/api/tour`. Sai dữ liệu (điểm quá xa, trùng node, kịch bản/cạnh không có) → RouteInputError.

    `twins`: bảng cạnh đối dựng lúc khởi động (main.py); không truyền thì tự dựng (chậm hơn, chỉ cho script).
    """
    if twins is None:
        twins = reverse_twins(graph, meta)
    n = len(req.stops) + 1
    if req.include_optimal and n > HELD_KARP_MAX_POINTS:
        raise RouteInputError(f"Chỉ tính tour tối ưu (Held–Karp) khi có tối đa {HELD_KARP_MAX_POINTS} điểm "
                              f"kể cả kho; đang có {n}.")
    snap = request_snapshot(graph, meta, req.scenario_id, req.blocked_edge_ids, scenarios)

    ids = ["depot"] + [s.id for s in req.stops]
    points = [req.depot] + list(req.stops)
    nodes: list[int] = []
    snapped: dict[str, SnappedStop] = {}
    for pid, p in zip(ids, points):
        which = "Kho" if pid == "depot" else f"Điểm giao {pid!r}"
        node, dist_m = _snap(graph, meta, p.lat, p.lon, which)
        if node in nodes:
            other = ids[nodes.index(node)]
            raise RouteInputError(f"{which} trùng node {node} với {other!r}; hãy chọn hai điểm cách xa nhau hơn.")
        nodes.append(node)
        snapped[pid] = SnappedStop(id=pid, node_id=node, lat=graph.node_lat[node], lon=graph.node_lon[node],
                                   snap_distance_m=dist_m)

    t0 = time.perf_counter_ns()
    D, legs = cost_matrix(graph, snap, nodes)
    matrix_ms = round((time.perf_counter_ns() - t0) / 1e6, 3)

    base = dict(dataset_id=graph.dataset_id, snapshot_id=snap.snapshot_id, snapped=snapped,
                matrix_runtime_ms=matrix_ms)
    unreachable = [UnreachablePair(from_id=ids[i], to_id=ids[j])
                   for i in range(n) for j in range(n) if i != j and D[i][j] == math.inf]
    if unreachable:
        return TourResponse(status="infeasible_under_model", unreachable=unreachable,
                            warnings=["Có chặng không đi được trong kịch bản này nên không lập tour; "
                                      "xem danh sách 'unreachable'."], **base)

    t0 = time.perf_counter_ns()
    plan = choose_tour(D, list(range(n)))
    order_ms = round((time.perf_counter_ns() - t0) / 1e6, 3)
    # Cùng các hàm choose_tour đã dùng (tất định), để trả đủ ba phương án cho ba thẻ của UI.
    orders = {"input": list(range(n))}
    orders["nearest_neighbor"] = nearest_neighbor(D)
    orders["nearest_neighbor_2opt"] = two_opt(D, orders["nearest_neighbor"])
    if req.include_or_opt:
        orders["nearest_neighbor_2opt_oropt"] = or_opt(D, orders["nearest_neighbor_2opt"])
    if req.keep_order is not None:
        # R1 C2: thứ tự trước khi đóng đường, mỗi chặng lấy từ ma trận của snapshot mới. Không đưa vào
        # choose_tour, nên không được chọn và không tính vào gap: so sánh tách khỏi việc sắp lại.
        orders["kept_order"] = [0] + [ids.index(pid) for pid in req.keep_order]

    c_input = plan.candidates["input"]
    candidates = {}
    for name, order in orders.items():
        closed = order + [0]
        edges = [e for a, b in zip(closed, closed[1:]) for e in legs[a][b]]
        cost = sum(snap.weights[e] for e in edges)
        candidates[name] = TourCandidate(
            stop_order=[ids[k] for k in order[1:]],
            cost_s=cost,
            distance_m=sum(graph.edge_length_m[e] for e in edges),
            improvement_pct=100.0 * (c_input - cost) / c_input if c_input > 0 else 0.0,
            edge_ids=edges,
            geometry=build_geometry(graph, meta, nodes[0], edges, "ok"),
            edge_twin_ids=[twins[e] for e in edges],
            edge_geometries=[edge_coords(graph, meta, e) for e in edges],
        )

    optimal = None
    if req.include_optimal:
        best = held_karp(D)
        c_opt = tour_cost(D, best)
        or_opt_gap = None
        if req.include_or_opt:
            c_or = candidates["nearest_neighbor_2opt_oropt"].cost_s
            if c_opt > 0:
                raw_gap = 100.0 * (c_or - c_opt) / c_opt
                or_opt_gap = 0.0 if abs(raw_gap) < 1e-9 else raw_gap
            else:
                or_opt_gap = 0.0
        optimal = TourOptimal(
            stop_order=[ids[k] for k in best[1:]],
            cost_s=c_opt,
            gap_pct=100.0 * (plan.cost_s - c_opt) / c_opt if c_opt > 0 else 0.0,
            or_opt_gap_pct=or_opt_gap,
        )

    return TourResponse(status="ok", candidates=candidates, chosen=plan.method, optimal=optimal,
                        order_runtime_ms=order_ms, **base)
