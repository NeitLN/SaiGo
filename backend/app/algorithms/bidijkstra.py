"""Dijkstra hai chiều trên đồ thị có hướng, trọng số không âm (docs/DATA_MODEL.md mục 6.2–6.3).

Tìm kiếm xuôi từ `source` trên `out_edges` và ngược từ `target` trên `in_edges`, xen kẽ mở rộng
phía có đỉnh heap nhỏ hơn. Mỗi lần quét một cạnh nối hai phía, cập nhật μ = chi phí tốt nhất đã
gặp (`g_f[u] + w + g_b[v]`); dừng khi `top_f + top_b ≥ μ` (điều kiện dừng chuẩn của Dijkstra hai
chiều). Tuyến dựng lại từ predecessor hai phía quanh cạnh nối tốt nhất.

Bộ đếm giữ đúng nghĩa của Dijkstra một chiều: `expanded` là **tổng** số node đã mở rộng ở hai phía
(không tính lần pop đích của mỗi phía), `trace` ghi đúng thứ tự mở rộng xen kẽ thực tế, `pushes`
đếm cả hai entry khởi tạo, `max_frontier` là đỉnh của **tổng** số entry trong hai heap.
`in_edges` là cấu trúc của đồ thị (không phụ thuộc kịch bản), dựng một lần cho mỗi đồ thị rồi cache,
ngang hàng với `out_edges` mà Dijkstra một chiều đã có sẵn trong `Graph`; nhờ vậy so thời gian công bằng.
"""

from __future__ import annotations

import heapq
import math

from app.algorithms.result import SearchResult, check_endpoints
from app.graph.model import Graph
from app.graph.scenario import Snapshot


_in_edges_cache: dict[int, tuple[Graph, list[list[int]]]] = {}   # Graph không hash được: key id(graph)


def _in_edges(graph: Graph) -> list[list[int]]:
    """in_edges[v] = các edge id đi vào v, tăng dần theo edge id (duyệt ngược từ target); cache theo đồ thị."""
    hit = _in_edges_cache.get(id(graph))
    if hit is not None and hit[0] is graph:
        return hit[1]
    in_edges: list[list[int]] = [[] for _ in graph.node_lat]
    for e, v in enumerate(graph.edge_v):
        in_edges[v].append(e)
    _in_edges_cache[id(graph)] = (graph, in_edges)
    return in_edges


def _clean_top(heap: list[tuple[float, int, int]], dist: list[float]) -> float:
    """Bỏ entry lỗi thời ở đỉnh heap; trả khóa nhỏ nhất còn hợp lệ (inf nếu heap rỗng)."""
    while heap and heap[0][0] > dist[heap[0][2]]:
        heapq.heappop(heap)
    return heap[0][0] if heap else math.inf


def _reconstruct(graph: Graph, pred_f: list[int], pred_b: list[int], source: int, target: int,
                 meet_f: int, meet_b: int, meet_edge: int) -> list[int]:
    """Ghép tuyến source → meet_f → meet_b → target quanh cạnh nối tốt nhất."""
    forward: list[int] = []
    node = meet_f
    while node != source:
        e = pred_f[node]
        forward.append(e)
        node = graph.edge_u[e]
    forward.reverse()

    backward: list[int] = []
    node = meet_b
    while node != target:
        e = pred_b[node]
        backward.append(e)
        node = graph.edge_v[e]
    return forward + [meet_edge] + backward


def bidijkstra(graph: Graph, snap: Snapshot, source: int, target: int,
               *, trace_limit: int = 0) -> SearchResult:
    """Dijkstra hai chiều; cùng quy tắc lazy deletion và cùng bộ đếm với `dijkstra`."""
    check_endpoints(graph, source, target)
    if source == target:
        return SearchResult("ok", 0.0, [], [source], 0.0, 0, 0, 0, 0, 0, 0)

    n = len(graph.node_lat)
    weights, out_edges, edge_u, edge_v = snap.weights, graph.out_edges, graph.edge_u, graph.edge_v
    in_edges = _in_edges(graph)

    g_f = [math.inf] * n                  # chi phí tốt nhất từ source
    g_b = [math.inf] * n                  # chi phí tốt nhất tới target (tìm ngược)
    pred_f = [-1] * n                     # cạnh vào node trên tuyến xuôi
    pred_b = [-1] * n                     # cạnh ra khỏi node trên tuyến ngược (node → … → target)
    expanded_nodes = bytearray(n)
    g_f[source] = 0.0
    g_b[target] = 0.0
    heap_f = [(0.0, 0, source)]
    heap_b = [(0.0, 0, target)]
    counter = 1
    expanded = unique_expanded = relaxations = 0
    pushes = max_frontier = 2             # hai entry khởi tạo, mỗi phía một
    trace: list[int] = []

    mu = math.inf                         # chi phí tuyến tốt nhất đã gặp
    meet_edge = meet_f = meet_b = -1

    while heap_f and heap_b:
        top_f = _clean_top(heap_f, g_f)
        top_b = _clean_top(heap_b, g_b)
        if not heap_f or not heap_b or top_f + top_b >= mu:
            break

        if top_f <= top_b:                # mở rộng phía có đỉnh heap nhỏ hơn
            d, _, u = heapq.heappop(heap_f)
            if u == target:
                continue                  # không mở rộng đích phía xuôi
            expanded += 1
            if not expanded_nodes[u]:
                expanded_nodes[u] = 1
                unique_expanded += 1
            if len(trace) < trace_limit:
                trace.append(u)
            for e in out_edges[u]:
                w = weights[e]
                if w == math.inf:
                    continue              # cạnh bị đóng trong snapshot này
                v = edge_v[e]
                if g_b[v] < math.inf:     # cạnh nối: u (phía xuôi) → v (phía ngược)
                    cand = d + w + g_b[v]
                    if cand < mu:
                        mu, meet_edge, meet_f, meet_b = cand, e, u, v
                nd = d + w
                if nd < g_f[v]:
                    g_f[v] = nd
                    pred_f[v] = e
                    relaxations += 1
                    heapq.heappush(heap_f, (nd, counter, v))
                    counter += 1
                    pushes += 1
        else:
            d, _, u = heapq.heappop(heap_b)
            if u == source:
                continue                  # không mở rộng nguồn phía ngược
            expanded += 1
            if not expanded_nodes[u]:
                expanded_nodes[u] = 1
                unique_expanded += 1
            if len(trace) < trace_limit:
                trace.append(u)
            # Đi ngược: cạnh e = (v → u), chi phí từ v tới target = w + chi phí từ u tới target.
            for e in in_edges[u]:
                w = weights[e]
                if w == math.inf:
                    continue
                v = edge_u[e]
                if g_f[v] < math.inf:     # cạnh nối: v (phía xuôi) → u (phía ngược)
                    cand = g_f[v] + w + d
                    if cand < mu:
                        mu, meet_edge, meet_f, meet_b = cand, e, v, u
                nd = d + w
                if nd < g_b[v]:
                    g_b[v] = nd
                    pred_b[v] = e
                    relaxations += 1
                    heapq.heappush(heap_b, (nd, counter, v))
                    counter += 1
                    pushes += 1
        max_frontier = max(max_frontier, len(heap_f) + len(heap_b))

    truncated = trace_limit > 0 and expanded > trace_limit
    if mu == math.inf:
        return SearchResult("no_path", None, [], [], None, expanded, unique_expanded, 0,
                            relaxations, pushes, max_frontier, trace, truncated)

    edges = _reconstruct(graph, pred_f, pred_b, source, target, meet_f, meet_b, meet_edge)
    return SearchResult(
        "ok",
        sum(weights[e] for e in edges),   # đúng định nghĩa cost_s: tổng trọng số các cạnh của tuyến
        edges,
        [source] + [edge_v[e] for e in edges],
        sum(graph.edge_length_m[e] for e in edges),
        expanded, unique_expanded, 0, relaxations, pushes, max_frontier, trace, truncated)
