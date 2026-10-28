"""Dijkstra trên đồ thị có hướng, trọng số không âm (docs/DATA_MODEL.md mục 6.3).

Heap chứa (g, counter, node); counter tăng dần để phá hòa ổn định. Lazy deletion:
entry lỗi thời bị bỏ qua khi pop, trước khi kiểm tra đích. Dừng khi pop được đích.
"""

from __future__ import annotations

import heapq
import math

from app.algorithms.result import SearchResult, build_route, check_endpoints
from app.graph.model import Graph
from app.graph.scenario import Snapshot


def dijkstra(graph: Graph, snap: Snapshot, source: int, target: int, *, trace_limit: int = 0) -> SearchResult:
    check_endpoints(graph, source, target)
    if source == target:
        return SearchResult("ok", 0.0, [], [source], 0.0, 0, 0, 0, 0, 0, 0)

    weights, out_edges, edge_v = snap.weights, graph.out_edges, graph.edge_v
    g = [math.inf] * len(graph.node_lat)
    pred_edge = [-1] * len(graph.node_lat)
    g[source] = 0.0
    heap = [(0.0, 0, source)]
    counter = 1
    expanded = relaxations = 0
    pushes = max_frontier = 1
    trace: list[int] = []

    while heap:
        d, _, u = heapq.heappop(heap)
        if d > g[u]:
            continue                      # entry lỗi thời
        if u == target:
            edges, nodes = build_route(graph, pred_edge, source, target)
            return SearchResult("ok", d, edges, nodes, sum(graph.edge_length_m[e] for e in edges),
                                expanded, expanded, 0, relaxations, pushes, max_frontier,
                                trace, trace_limit > 0 and expanded > trace_limit)
        expanded += 1
        if len(trace) < trace_limit:
            trace.append(u)
        for e in out_edges[u]:
            w = weights[e]
            if w == math.inf:
                continue                  # cạnh bị đóng trong snapshot này
            v = edge_v[e]
            nd = d + w
            if nd < g[v]:
                g[v] = nd
                pred_edge[v] = e
                relaxations += 1
                heapq.heappush(heap, (nd, counter, v))
                counter += 1
                pushes += 1
                max_frontier = max(max_frontier, len(heap))

    return SearchResult("no_path", None, [], [], None, expanded, expanded, 0, relaxations, pushes,
                        max_frontier, trace, trace_limit > 0 and expanded > trace_limit)


def dijkstra_many(graph: Graph, snap: Snapshot, source: int, targets: list[int]) -> tuple[dict[int, float], list[int]]:
    """Dijkstra một nguồn tới nhiều đích, dừng khi đã pop đủ các đích (dùng để xây ma trận tour, T72).

    Cùng quy tắc heap và lazy deletion như `dijkstra`. Trả `dist[t]` cho từng đích (`math.inf` nếu
    không tới được) và `pred_edge` để dựng lại đúng các chặng đã dùng trong ma trận (`build_route`).
    """
    for t in targets:
        check_endpoints(graph, source, t)
    weights, out_edges, edge_v = snap.weights, graph.out_edges, graph.edge_v
    g = [math.inf] * len(graph.node_lat)
    pred_edge = [-1] * len(graph.node_lat)
    g[source] = 0.0
    remaining = set(targets)
    heap = [(0.0, 0, source)]
    counter = 1
    while heap and remaining:
        d, _, u = heapq.heappop(heap)
        if d > g[u]:
            continue                      # entry lỗi thời
        remaining.discard(u)
        for e in out_edges[u]:
            w = weights[e]
            if w == math.inf:
                continue                  # cạnh bị đóng trong snapshot này
            v = edge_v[e]
            nd = d + w
            if nd < g[v]:
                g[v] = nd
                pred_edge[v] = e
                heapq.heappush(heap, (nd, counter, v))
                counter += 1
    return {t: g[t] for t in targets}, pred_edge
