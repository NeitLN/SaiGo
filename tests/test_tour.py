"""T70: tour trên ma trận chi phí có hướng — chi phí, Nearest Neighbor, 2-opt (docs/TOPIC.md mục 10)."""

from __future__ import annotations

import itertools
import math
import random
import time

import pytest

from app.algorithms.tour import choose_tour, held_karp, nearest_neighbor, tour_cost, two_opt


def is_tour(order: list[int], n: int) -> bool:
    """Tour hợp lệ: đủ n điểm, không trùng, kho ở đầu."""
    return len(order) == n and order[0] == 0 and sorted(order) == list(range(n))


def brute_force_cost(D: list[list[float]]) -> float:
    """Chi phí tour tối ưu bằng duyệt mọi hoán vị điểm giao (chỉ dùng cho n ≤ 7 trong test)."""
    best = math.inf
    for perm in itertools.permutations(range(1, len(D))):
        best = min(best, tour_cost(D, [0, *perm]))
    return best


def seed_matrix(seed: int, n: int = 5) -> list[list[float]]:
    rng = random.Random(seed)
    return [[0 if i == j else rng.randint(1, 100) for j in range(n)] for i in range(n)]


# --- tour_cost ---

def test_single_point_tour_is_zero():
    D = [[0.0]]
    assert tour_cost(D, [0]) == 0.0
    assert nearest_neighbor(D) == [0]
    assert two_opt(D, [0]) == [0]
    plan = choose_tour(D, [0])
    assert plan.order == [0] and plan.cost_s == 0.0 and plan.method == "input"
    assert plan.candidates == {"input": 0.0, "nearest_neighbor": 0.0, "nearest_neighbor_2opt": 0.0}


def test_cost_follows_edge_direction_and_returns_to_depot():
    D = [[0, 1, 10], [10, 0, 1], [1, 10, 0]]
    assert tour_cost(D, [0, 1, 2]) == pytest.approx(3.0)      # 1 + 1 + 1
    assert tour_cost(D, [0, 2, 1]) == pytest.approx(30.0)     # 10 + 10 + 10
    D2 = [[0, 5], [7, 0]]
    assert tour_cost(D2, [0, 1]) == pytest.approx(12.0)       # 0→1 rồi 1→0, không phải 5 hay 5×2


# --- Công thức delta đối xứng sai với ma trận có hướng ---

def symmetric_delta(D, order, i, j) -> float:
    """Delta của 2-opt **đối xứng**: chỉ hai cạnh bị cắt, giả định các chặng bên trong không đổi."""
    n = len(order)
    return (D[order[i - 1]][order[j]] + D[order[i]][order[(j + 1) % n]]
            - D[order[i - 1]][order[i]] - D[order[j]][order[(j + 1) % n]])


def test_symmetric_delta_would_pick_a_worse_tour():
    # Chu trình rẻ đúng chiều 0→1→2→3→0 (10 mỗi chặng = 40), nhưng có "đường tắt" rẻ
    # 0→2 và 1→3 (1 mỗi chặng) để đánh lừa công thức đối xứng.
    D = [
        [0, 10, 1, 100],
        [100, 0, 10, 1],
        [100, 100, 0, 10],
        [10, 100, 100, 0],
    ]
    order = [0, 1, 2, 3]
    candidate = [0, 2, 1, 3]                       # đảo đoạn [1..2]
    assert symmetric_delta(D, order, 1, 2) == pytest.approx(-18.0)   # đối xứng "dự đoán" rẻ hơn 18
    assert tour_cost(D, candidate) == pytest.approx(112.0)           # tính lại toàn bộ: đắt hơn 72
    assert tour_cost(D, order) == pytest.approx(40.0)
    assert tour_cost(D, order) == pytest.approx(brute_force_cost(D))
    # 2-opt đúng (tính lại toàn bộ) không nhận nước đi mà công thức đối xứng tưởng là tốt.
    assert two_opt(D, order) == order


# --- 2-opt ---

@pytest.mark.parametrize("seed", range(10))
def test_two_opt_never_increases_cost_and_keeps_all_stops(seed):
    D = seed_matrix(seed, n=5 + seed % 4)
    nn = nearest_neighbor(D)
    before = list(nn)
    improved = two_opt(D, nn)
    assert nn == before                                  # không sửa tour truyền vào
    assert is_tour(improved, len(D))                     # giữ đủ điểm, kho vẫn ở đầu
    assert tour_cost(D, improved) <= tour_cost(D, nn) + 1e-12


def test_two_opt_reaches_optimum_on_small_case():
    # NN đi vòng 0→1→2→3→4→0 tốn 104; đảo cả đoạn cho 0→4→3→2→1→0 tốn 7.
    D = [[50] * 5 for _ in range(5)]
    for i in range(5):
        D[i][i] = 0
    D[0][1], D[1][2], D[2][3], D[3][4], D[4][0] = 1, 1, 1, 1, 100
    D[0][4], D[4][3], D[3][2], D[2][1], D[1][0] = 2, 1, 1, 1, 2
    nn = nearest_neighbor(D)
    assert nn == [0, 1, 2, 3, 4] and tour_cost(D, nn) == pytest.approx(104.0)
    improved = two_opt(D, nn)
    assert improved == [0, 4, 3, 2, 1]
    assert tour_cost(D, improved) == pytest.approx(7.0)
    assert tour_cost(D, improved) == pytest.approx(brute_force_cost(D))


# --- Nearest Neighbor ---

def test_nearest_neighbor_tie_breaks_on_smallest_index():
    # Từ kho, điểm 1 và 2 cùng chi phí 5: phải chọn 1; sau đó chỉ còn 2 rồi 3.
    D = [[0, 5, 5, 9], [9, 0, 9, 9], [9, 9, 0, 9], [1, 9, 9, 0]]
    assert nearest_neighbor(D) == [0, 1, 2, 3]


# --- choose_tour ---

def test_plan_improves_bad_input_with_nearest_neighbor():
    pos = [0, 10, 20, 30, 40]                    # 1D, đối xứng
    D = [[abs(a - b) for b in pos] for a in pos]
    plan = choose_tour(D, [0, 3, 1, 4, 2])       # thứ tự nhập đi vòng: 120
    assert plan.candidates["input"] == pytest.approx(120.0)
    assert plan.candidates["nearest_neighbor"] == pytest.approx(80.0)
    assert plan.method == "nearest_neighbor"
    assert plan.cost_s == pytest.approx(80.0)
    assert plan.order == [0, 1, 2, 3, 4]


def test_plan_uses_two_opt_after_nearest_neighbor():
    D = [[50] * 5 for _ in range(5)]
    for i in range(5):
        D[i][i] = 0
    D[0][1], D[1][2], D[2][3], D[3][4], D[4][0] = 1, 1, 1, 1, 100
    D[0][4], D[4][3], D[3][2], D[2][1], D[1][0] = 2, 1, 1, 1, 2
    plan = choose_tour(D, [0, 1, 2, 3, 4])
    assert plan.candidates["nearest_neighbor"] == pytest.approx(104.0)
    assert plan.candidates["nearest_neighbor_2opt"] == pytest.approx(7.0)
    assert plan.method == "nearest_neighbor_2opt"
    assert plan.cost_s == pytest.approx(7.0)


def test_plan_keeps_input_when_it_is_cheapest():
    D = [
        [0, 10, 1, 100],
        [100, 0, 10, 1],
        [100, 100, 0, 10],
        [10, 100, 100, 0],
    ]
    order = [0, 1, 2, 3]
    plan = choose_tour(D, order)
    assert plan.candidates["input"] == pytest.approx(40.0)
    assert plan.cost_s == pytest.approx(40.0)
    assert plan.method == "input"                     # hòa với NN+2-opt: giữ thứ tự nhập
    assert plan.order == order


def test_plan_records_candidates_and_does_not_mutate_inputs():
    D = seed_matrix(3)
    order = [0, 2, 4, 1, 3]
    D_before = [row[:] for row in D]
    plan = choose_tour(D, order)
    assert order == [0, 2, 4, 1, 3] and D == D_before
    assert list(plan.candidates) == ["input", "nearest_neighbor", "nearest_neighbor_2opt"]
    assert plan.cost_s == min(plan.candidates.values())
    assert plan.candidates[plan.method] == plan.cost_s
    assert tour_cost(D, plan.order) == pytest.approx(plan.cost_s)   # chi phí lưu khớp tính lại


@pytest.mark.parametrize("seed", range(5))
def test_plan_is_not_below_optimum_and_not_worse_than_candidates(seed):
    D = seed_matrix(seed)
    plan = choose_tour(D, [0, 1, 2, 3, 4])
    assert plan.cost_s >= brute_force_cost(D) - 1e-9
    assert plan.cost_s <= plan.candidates["input"] + 1e-9
    assert plan.cost_s <= plan.candidates["nearest_neighbor"] + 1e-9
    assert is_tour(plan.order, 5)


def test_infinite_legs_are_not_hidden():
    # Mọi tour đều dùng ít nhất một chặng math.inf (1→2 hoặc 2→1/1→0).
    D = [[0, 4, 9], [math.inf, 0, math.inf], [math.inf, math.inf, 0]]
    assert math.isinf(tour_cost(D, [0, 1, 2])) and math.isinf(tour_cost(D, [0, 2, 1]))
    assert two_opt(D, [0, 1, 2]) == [0, 1, 2]          # không có ứng viên hữu hạn nào rẻ hơn
    plan = choose_tour(D, [0, 1, 2])
    assert math.isinf(plan.cost_s) and plan.order == [0, 1, 2] and plan.method == "input"


# --- Dữ liệu sai ---

@pytest.mark.parametrize("D, match", [
    ([], "ít nhất 1 hàng"),
    ([[0, 1], [1]], "vuông"),
    ([[0, -1], [1, 0]], r"D\[0\]\[1\]"),
    ([[0, math.nan], [1, 0]], r"D\[0\]\[1\]"),
    ([[0, -math.inf], [1, 0]], r"D\[0\]\[1\]"),
    ([[0, "1"], [1, 0]], r"D\[0\]\[1\]"),
    ([[0, True], [1, 0]], r"D\[0\]\[1\]"),
])
def test_bad_matrix_rejected(D, match):
    with pytest.raises(ValueError, match=match):
        nearest_neighbor(D)


@pytest.mark.parametrize("order, match", [
    ([0, 1], "đúng 3 điểm"),
    ([0, 1, 1], "hoán vị"),
    ([1, 0, 2], "kho"),
    ([0, 1, "2"], "chỉ số nguyên"),
    ([0, 1, True], "chỉ số nguyên"),
])
def test_bad_order_rejected(order, match):
    D = [[0, 1, 2], [2, 0, 1], [1, 2, 0]]
    with pytest.raises(ValueError, match=match):
        tour_cost(D, order)


# --- Held–Karp: đối chứng chính xác cho bộ nhỏ ---

def test_held_karp_single_and_two_points():
    assert held_karp([[0.0]]) == [0]
    D = [[0, 5], [7, 0]]
    order = held_karp(D)
    assert order == [0, 1]
    assert tour_cost(D, order) == pytest.approx(12.0)          # cả hai chiều, không phải 5 hay 10


def test_held_karp_follows_direction():
    # Đi xuôi 10+10+10 = 30; đi ngược 1+1+1 = 3: tour tối ưu phải là chiều ngược.
    D = [[0, 10, 1], [1, 0, 10], [10, 1, 0]]
    order = held_karp(D)
    assert order == [0, 2, 1]
    assert tour_cost(D, order) == pytest.approx(3.0)


@pytest.mark.parametrize("n", range(2, 8))
@pytest.mark.parametrize("seed", [0, 7])
def test_held_karp_matches_brute_force(n, seed):
    D = seed_matrix(seed, n=n)
    order = held_karp(D)
    assert is_tour(order, n)
    assert tour_cost(D, order) == pytest.approx(brute_force_cost(D))


def test_held_karp_finds_optimum_hidden_from_nearest_neighbor():
    # Cùng ma trận với T70: NN đi 0→1→2→3→4→0 tốn 104, tối ưu 0→4→3→2→1→0 tốn 7.
    D = [[50] * 5 for _ in range(5)]
    for i in range(5):
        D[i][i] = 0
    D[0][1], D[1][2], D[2][3], D[3][4], D[4][0] = 1, 1, 1, 1, 100
    D[0][4], D[4][3], D[3][2], D[2][1], D[1][0] = 2, 1, 1, 1, 2
    order = held_karp(D)
    assert order == [0, 4, 3, 2, 1]
    assert tour_cost(D, order) == pytest.approx(7.0)
    assert tour_cost(D, nearest_neighbor(D)) == pytest.approx(104.0)


@pytest.mark.parametrize("seed", range(5))
def test_held_karp_not_worse_than_heuristics(seed):
    D = seed_matrix(seed, n=7)
    D_before = [row[:] for row in D]
    plan = choose_tour(D, [0, 1, 2, 3, 4, 5, 6])
    best = tour_cost(D, held_karp(D))
    assert best <= plan.cost_s + 1e-9
    assert D == D_before                                   # không sửa ma trận đầu vào


def test_held_karp_all_legs_infinite_still_returns_a_tour():
    D = [[0 if i == j else math.inf for j in range(3)] for i in range(3)]
    order = held_karp(D)
    assert is_tour(order, 3)
    assert math.isinf(tour_cost(D, order))


def test_held_karp_rejects_more_than_eleven_points():
    with pytest.raises(ValueError, match="tối đa 11 điểm"):
        held_karp(seed_matrix(1, n=12))


def test_held_karp_accepts_ten_points():
    D = seed_matrix(2, n=10)
    order = held_karp(D)
    assert is_tour(order, 10)
    assert tour_cost(D, order) <= tour_cost(D, nearest_neighbor(D)) + 1e-9


def test_held_karp_accepts_eleven_points():
    D = seed_matrix(2, n=11)
    order = held_karp(D)
    assert is_tour(order, 11)
    assert tour_cost(D, order) <= tour_cost(D, nearest_neighbor(D)) + 1e-9


def test_held_karp_eleven_points_known_optimum_and_runtime():
    # Ma trận 11 điểm (kho + 10 điểm giao) với chu trình có hướng 0→1→...→10→0 có chi phí 1.0 mỗi chặng.
    # Mọi chặng khác có chi phí 100.0, do đó tour tối ưu duy nhất là [0, 1, 2, ..., 10] với chi phí 11.0.
    n = 11
    D = [[100.0 if i != j else 0.0 for j in range(n)] for i in range(n)]
    for i in range(n):
        D[i][(i + 1) % n] = 1.0

    t0 = time.perf_counter()
    order = held_karp(D)
    elapsed = time.perf_counter() - t0

    assert elapsed < 2.0, f"Thời gian chạy n=11 ({elapsed:.3f}s) vượt quá ngưỡng 2s"
    assert is_tour(order, n)
    assert order == list(range(n))
    assert tour_cost(D, order) == pytest.approx(float(n))
