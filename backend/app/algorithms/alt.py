"""ALT: A* với heuristic landmark (bất đẳng thức tam giác), docs/DATA_MODEL.md mục 5–6.

Chọn k landmark trên thành phần liên thông mạnh lớn nhất kiểu "farthest point" (seed cố định),
rồi chạy Dijkstra xuôi và ngược từ mỗi landmark trên **chi phí cơ sở** (baseline). Với đích t:

    h(v) = max(0, max_L d(L, t) − d(L, v), max_L d(v, L) − d(t, L))

Kịch bản ùn tắc chỉ nhân chi phí với alpha ≥ 1 và đóng đường = vô cực, nên chi phí trong snapshot
luôn ≥ chi phí cơ sở: các khoảng cách baseline là chặn dưới hợp lệ, h vừa admissible vừa consistent
với snapshot (mục 4.1 điểm 4). `ensure_alt_compatible` kiểm điều kiện "không cạnh nào rẻ hơn cơ sở"
trước mỗi truy vấn và báo lỗi rõ nếu vi phạm.

Tiền xử lý làm một lần cho mỗi đồ thị (cache theo `id(graph)`, giống `heuristics.geo_scale`), không
tính vào `runtime_ms` của truy vấn; thời gian và bộ nhớ bảng khoảng cách được ghi qua logger và
đọc lại được từ `AltIndex.preprocess_ms` / `AltIndex.memory_bytes`.

Vòng lặp tìm kiếm dùng lại đúng `astar`: ALT chỉ khác heuristic, nên mọi bộ đếm (expanded, pushes,
relaxations, reopened), `trace` và `SearchResult` giữ cùng nghĩa với Dijkstra/A*.
"""

from __future__ import annotations

import heapq
import logging
import math
import random
import time
from array import array
from dataclasses import dataclass

from app.algorithms.astar import astar
from app.algorithms.heuristics import Heuristic, zero_heuristic
from app.algorithms.result import SearchResult
from app.graph.model import Graph, GraphMeta
from app.graph.scenario import Snapshot

DEFAULT_LANDMARKS = 8
LANDMARK_SEED = 20261113     # cố định: cùng đồ thị → cùng bộ landmark
MEMORY_ITEM_BYTES = 8        # array('d') lưu mỗi khoảng cách trong 8 byte

log = logging.getLogger("saigo.alt")


@dataclass(frozen=True)
class AltIndex:
    """Bảng khoảng cách landmark → node (xuôi) và node → landmark (ngược), trên chi phí cơ sở."""

    landmarks: tuple[int, ...]
    dist_from: tuple[array, ...]   # dist_from[i][v] = d(L_i, v)
    dist_to: tuple[array, ...]     # dist_to[i][v]   = d(v, L_i)
    preprocess_ms: float
    memory_bytes: int

    @property
    def k(self) -> int:
        return len(self.landmarks)


def _dijkstra_costs(weights: list[float], out_edges: list[list[int]], edge_to: list[int],
                    source: int) -> array:
    """Khoảng cách ngắn nhất từ `source` tới mọi node; `inf` nếu không tới được.

    `out_edges` + `edge_to` mô tả chiều duyệt: (out_edges, edge_v) là đồ thị xuôi,
    (in_edges, edge_u) là đồ thị ngược. Cạnh có trọng số vô cực bị bỏ qua.
    """
    n = len(out_edges)
    dist = array("d", [math.inf]) * n
    dist[source] = 0.0
    heap = [(0.0, source)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue                          # entry lỗi thời
        for e in out_edges[u]:
            w = weights[e]
            if w == math.inf:
                continue
            v = edge_to[e]
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist


def _in_edges(graph: Graph) -> list[list[int]]:
    """in_edges[v] = các edge id đi vào v, tăng dần theo edge id."""
    in_edges: list[list[int]] = [[] for _ in graph.node_lat]
    for e, v in enumerate(graph.edge_v):
        in_edges[v].append(e)
    return in_edges


def choose_landmarks(graph: Graph, meta: GraphMeta | None, k: int, seed: int,
                     weights: list[float]) -> tuple[int, ...]:
    """k landmark kiểu farthest point trên SCC lớn nhất: mỗi bước chọn node xa bộ đã chọn nhất.

    Điểm đầu do `random.Random(seed)` chọn nên kết quả cố định với cùng đồ thị và seed. Node không
    tới được từ mọi landmark đã chọn không bao giờ được chọn (tránh landmark vô dụng ngoài SCC).
    """
    n = len(graph.node_lat)
    if n == 0 or k <= 0:
        return ()
    in_scc = meta.node_in_scc if meta is not None else [True] * n
    candidates = [v for v in range(n) if in_scc[v] and graph.out_edges[v]]
    if not candidates:
        candidates = [v for v in range(n) if graph.out_edges[v]] or list(range(n))
    k = min(k, len(candidates))

    rng = random.Random(seed)
    chosen = [candidates[rng.randrange(len(candidates))]]
    score = _dijkstra_costs(weights, graph.out_edges, graph.edge_v, chosen[0])
    picked = set(chosen)
    while len(chosen) < k:
        best, best_score = -1, -1.0
        for v in candidates:
            s = score[v]
            if v in picked or math.isinf(s):
                continue
            if s > best_score:                # hòa giữ node id nhỏ vì duyệt theo thứ tự tăng
                best, best_score = v, s
        if best < 0:
            break
        chosen.append(best)
        picked.add(best)
        nxt = _dijkstra_costs(weights, graph.out_edges, graph.edge_v, best)
        for v in range(n):
            if nxt[v] < score[v]:
                score[v] = nxt[v]
    return tuple(chosen)


def build_alt_index(graph: Graph, meta: GraphMeta | None = None, *, k: int = DEFAULT_LANDMARKS,
                    seed: int = LANDMARK_SEED) -> AltIndex:
    """Tiền xử lý ALT trên chi phí cơ sở: chọn landmark + 2·k lần Dijkstra (xuôi, ngược)."""
    t0 = time.perf_counter_ns()
    weights = graph.edge_base_time_s
    reverse = _in_edges(graph)
    landmarks = choose_landmarks(graph, meta, k, seed, weights)
    dist_from = tuple(_dijkstra_costs(weights, graph.out_edges, graph.edge_v, L) for L in landmarks)
    dist_to = tuple(_dijkstra_costs(weights, reverse, graph.edge_u, L) for L in landmarks)
    preprocess_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
    memory_bytes = MEMORY_ITEM_BYTES * len(graph.node_lat) * (len(dist_from) + len(dist_to))
    return AltIndex(landmarks, dist_from, dist_to, round(preprocess_ms, 3), memory_bytes)


_index_cache: dict[tuple[int, int], tuple[Graph, AltIndex]] = {}   # Graph không hash được


def get_alt_index(graph: Graph, meta: GraphMeta | None = None, *, k: int = DEFAULT_LANDMARKS,
                  seed: int = LANDMARK_SEED) -> AltIndex:
    """ALT index của đồ thị, dựng một lần rồi dùng lại (key: id(graph) + k, giống geo_scale cache)."""
    key = (id(graph), k)
    hit = _index_cache.get(key)
    if hit is not None and hit[0] is graph:
        return hit[1]
    index = build_alt_index(graph, meta, k=k, seed=seed)
    _index_cache[key] = (graph, index)
    log.info(
        "ALT: %d landmark (seed %d) trên %d node, tiền xử lý %.1f ms, bảng khoảng cách %.1f KiB "
        "(không tính vào runtime_ms của truy vấn)",
        index.k, seed, len(graph.node_lat), index.preprocess_ms, index.memory_bytes / 1024.0)
    return index


def ensure_alt_compatible(graph: Graph, snap: Snapshot) -> None:
    """Chặn snapshot có cạnh rẻ hơn chi phí cơ sở: khi đó bảng landmark không còn là chặn dưới."""
    base = graph.edge_base_time_s
    for e, w in enumerate(snap.weights):
        if w < base[e]:
            raise ValueError(
                f"ALT chỉ hợp lệ khi kịch bản không làm cạnh nào rẻ hơn chi phí cơ sở: "
                f"snapshot {snap.snapshot_id!r} có cạnh {e} = {w!r} s < baseline {base[e]!r} s. "
                "Hãy dùng baseline hoặc kịch bản chỉ tăng chi phí (alpha ≥ 1) / đóng đường.")


def make_alt_heuristic(index: AltIndex, target: int) -> Heuristic:
    """h(v) theo bất đẳng thức tam giác với các landmark; h(target) = 0."""
    rows = [(d_from, d_to, d_from[target], d_to[target])
            for d_from, d_to in zip(index.dist_from, index.dist_to)]
    rows = [row for row in rows if not (math.isinf(row[2]) and math.isinf(row[3]))]
    if not rows:
        return zero_heuristic

    def h(v: int) -> float:
        best = 0.0
        for d_from, d_to, d_lt, d_tl in rows:
            x = d_from[v]                     # d(L, v)
            if d_lt < math.inf and x < math.inf:
                val = d_lt - x                # d(L,t) − d(L,v) ≤ d(v,t)
                if val > best:
                    best = val
            y = d_to[v]                       # d(v, L)
            if y < math.inf and d_tl < math.inf:
                val = y - d_tl                # d(v,L) − d(t,L) ≤ d(v,t)
                if val > best:
                    best = val
        return best

    return h


def alt(graph: Graph, snap: Snapshot, source: int, target: int, index: AltIndex,
        *, trace_limit: int = 0) -> SearchResult:
    """ALT = A* với heuristic landmark; cùng quy tắc heap, bộ đếm và `trace` như A*."""
    ensure_alt_compatible(graph, snap)
    return astar(graph, snap, source, target, make_alt_heuristic(index, target),
                 trace_limit=trace_limit)
