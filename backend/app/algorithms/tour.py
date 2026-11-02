"""Tour trên ma trận chi phí có hướng (docs/TOPIC.md mục 10, docs/TASKS.md T70).

Kho là chỉ số 0 và cố định ở đầu/cuối tour; `order = [0, …]` liệt kê kho một lần, hàm tự cộng
chặng quay về kho. Ma trận **bất đối xứng**: `D[i][j]` là chi phí có hướng, không dùng công thức
delta của 2-opt đối xứng vì đảo một đoạn còn đảo chiều các chặng bên trong (mục 10.5).
NN và 2-opt là heuristic: kết quả là "lộ trình được cải thiện", không phải tối ưu toàn cục;
`held_karp` là đối chứng chính xác cho n ≤ 11 (O(2^n · n²)), chỉ dùng khi đo gap.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

Matrix = Sequence[Sequence[float]]

COST_EPS = 1e-9   # giây; chênh lệch nhỏ hơn mức này coi như bằng nhau (sai số số thực)
HELD_KARP_MAX_POINTS = 11   # gồm cả kho, tức tối đa 10 điểm giao — EXPERIMENT_PLAN mục 8 (O(2^n · n²))


@dataclass(frozen=True)
class TourPlan:
    order: list[int]                # tour được chọn, khép kín: 0 → … → 0
    cost_s: float
    method: str                     # "input" | "nearest_neighbor" | "nearest_neighbor_2opt"
    candidates: dict[str, float]    # chi phí từng ứng viên, để phân tích improvement


def _check_matrix(D: Matrix) -> int:
    """Kiểm ma trận vuông, chi phí không âm (math.inf = không tới được); trả số điểm n."""
    n = len(D)
    if n == 0:
        raise ValueError("ma trận chi phí phải có ít nhất 1 hàng (kho)")
    for i, row in enumerate(D):
        if len(row) != n:
            raise ValueError(f"ma trận chi phí phải vuông: hàng {i} có {len(row)} phần tử, cần {n}")
        for j, w in enumerate(row):
            if not (isinstance(w, (int, float)) and not isinstance(w, bool) and w >= 0):
                raise ValueError(f"D[{i}][{j}] = {w!r} phải là chi phí không âm "
                                 "(math.inf nếu không đi được)")
    return n


def _check_order(n: int, order: Sequence[int]) -> list[int]:
    """Kiểm tour là hoán vị của 0..n−1, kho ở đầu; trả bản sao để không sửa đầu vào."""
    seq = list(order)
    if len(seq) != n:
        raise ValueError(f"tour phải có đúng {n} điểm (kể cả kho), nhận {len(seq)}")
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in seq):
        raise ValueError("tour phải là dãy chỉ số nguyên")
    if sorted(seq) != list(range(n)):
        raise ValueError(f"tour phải là hoán vị của 0..{n - 1}, nhận {seq}")
    if seq[0] != 0:
        raise ValueError("kho (chỉ số 0) phải ở đầu tour")
    return seq


def _closed_cost(D: Matrix, seq: Sequence[int]) -> float:
    """Tổng chi phí tour khép kín, đã kiểm dữ liệu (dùng trong vòng lặp)."""
    return float(sum(D[a][b] for a, b in zip(seq, seq[1:] + seq[:1])))


def tour_cost(D: Matrix, order: Sequence[int]) -> float:
    """Chi phí tour khép kín `0 → order[1] → … → order[-1] → 0`, đơn vị của `D` (giây)."""
    n = _check_matrix(D)
    return _closed_cost(D, _check_order(n, order))


def nearest_neighbor(D: Matrix) -> list[int]:
    """Tham lam từ kho: mỗi bước chọn điểm chưa phục vụ có `D[vị trí hiện tại][j]` nhỏ nhất.

    Hòa chi phí thì chọn chỉ số nhỏ hơn để tái lập được. Ma trận có `math.inf` vẫn trả một
    hoán vị; chi phí tour khi đó là `math.inf` (kiểm khả thi là việc của tầng dựng ma trận).
    """
    n = _check_matrix(D)
    order = [0]
    remaining = set(range(1, n))
    while remaining:
        cur = order[-1]
        nxt = min(remaining, key=lambda j: (D[cur][j], j))
        order.append(nxt)
        remaining.remove(nxt)
    return order


def two_opt(D: Matrix, order: Sequence[int]) -> list[int]:
    """2-opt cho ma trận có hướng: đảo một đoạn điểm giao, **tính lại toàn bộ** chi phí tour.

    Kho giữ ở đầu/cuối. Chỉ nhận khi chi phí giảm hơn `COST_EPS`, dừng khi không còn cải thiện
    (mỗi nước đi được nhận làm chi phí giảm thật, số tour hữu hạn nên vòng lặp luôn dừng).
    Không sửa `order` truyền vào. Không bảo đảm tối ưu toàn cục (chỉ là cực trị địa phương).
    """
    n = _check_matrix(D)
    best = _check_order(n, order)
    best_cost = _closed_cost(D, best)
    while True:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                cost = _closed_cost(D, candidate)   # đảo đoạn đổi chiều cả các chặng bên trong
                if cost < best_cost - COST_EPS:
                    best, best_cost = candidate, cost
                    improved = True
                    break
            if improved:
                break
        if not improved:
            return best


def choose_tour(D: Matrix, order: Sequence[int]) -> TourPlan:
    """Chọn tour rẻ nhất trong {thứ tự nhập, Nearest Neighbor, Nearest Neighbor + 2-opt}.

    Hòa chi phí thì giữ ứng viên đứng trước trong danh sách trên, nên không bao giờ thay thứ tự
    nhập bằng một lời giải tệ hơn (TOPIC 10.6). Lưu chi phí từng ứng viên để tính improvement.
    """
    n = _check_matrix(D)
    initial = _check_order(n, order)
    nn = nearest_neighbor(D)
    nn_opt = two_opt(D, nn)
    options = (
        ("input", initial),
        ("nearest_neighbor", nn),
        ("nearest_neighbor_2opt", nn_opt),
    )
    costs = {name: _closed_cost(D, seq) for name, seq in options}
    method, best = options[0]
    for name, seq in options[1:]:
        if costs[name] < costs[method]:        # hòa thì giữ ứng viên đứng trước
            method, best = name, seq
    return TourPlan(best, costs[method], method, costs)


def held_karp(D: Matrix) -> list[int]:
    """Tour tối ưu toàn cục bằng quy hoạch động Held–Karp cho n ≤ `HELD_KARP_MAX_POINTS` (gồm cả kho, tức tối đa 10 điểm giao).

    `dp[S][j]` = chi phí nhỏ nhất đi từ kho (0), thăm đúng tập điểm giao `S` (bit của 1..n−1),
    kết thúc ở `j`; khởi tạo `dp[{j}][j] = D[0][j]`, truy hồi
    `dp[S][j] = min(dp[S\\{j}][i] + D[i][j])`, kết thúc bằng chặng `j → 0`.
    Dùng làm đối chứng cho NN + 2-opt trên bộ nhỏ, không dùng trong vòng lặp UI.
    Trả `order = [0, …]` khép kín như các hàm khác; ma trận có `math.inf` vẫn trả một hoán vị
    (chi phí khi đó là `math.inf`).
    """
    n = _check_matrix(D)
    if n > HELD_KARP_MAX_POINTS:
        raise ValueError(f"held_karp chỉ dùng cho tối đa {HELD_KARP_MAX_POINTS} điểm "
                         f"(2^n · n²), nhận {n}; dùng choose_tour cho dữ liệu lớn")
    if n == 1:
        return [0]

    k = n - 1                                  # số điểm giao, đánh số 1..n−1
    size = 1 << k
    dp = [[math.inf] * k for _ in range(size)]
    parent = [[-1] * k for _ in range(size)]
    for j in range(k):
        dp[1 << j][j] = D[0][j + 1]

    for mask in range(1, size):
        for j in range(k):
            if not (mask >> j) & 1:
                continue
            prev = mask ^ (1 << j)
            if prev == 0:
                continue                       # tập chỉ có j: đã khởi tạo
            best, best_i = math.inf, -1
            for i in range(k):
                if not (prev >> i) & 1:
                    continue
                if best_i == -1:
                    best_i = i                 # dự phòng khi mọi chặng đều math.inf: vẫn truy vết được
                cand = dp[prev][i] + D[i + 1][j + 1]
                if cand < best:                # hòa thì giữ i nhỏ hơn (tất định)
                    best, best_i = cand, i
            dp[mask][j] = best
            parent[mask][j] = best_i

    full = size - 1
    best_cost, last = math.inf, 0              # last = 0 để ma trận toàn math.inf vẫn truy vết được
    for j in range(k):
        cand = dp[full][j] + D[j + 1][0]
        if cand < best_cost:
            best_cost, last = cand, j

    stops: list[int] = []
    mask, j = full, last
    while j != -1:
        stops.append(j + 1)
        prev = parent[mask][j]
        mask ^= 1 << j
        j = prev
    stops.reverse()
    return [0] + stops
