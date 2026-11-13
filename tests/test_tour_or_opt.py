"""Kiểm tra cải tiến tour: thuật toán Or-opt và tích hợp API (O21).

Tiêu chuẩn:
- Kết quả or_opt là hoán vị hợp lệ của n điểm, giữ kho ở vị trí 0, không đổi list truyền vào;
- Chi phí Or-opt <= 2-opt trên mọi bộ thử;
- >= 200 ma trận bất đối xứng ngẫu nhiên n <= 9 so với Held-Karp (không bao giờ thấp hơn tối ưu);
- Thoát cực tiểu địa phương của 2-opt trên ma trận bất đối xứng xác định;
- Response mặc định không đổi (include_or_opt=False cho đúng 3 candidates);
- Tùy chọn include_or_opt=True thêm candidate 'nearest_neighbor_2opt_oropt';
- chosen vẫn chỉ chọn trong 3 phương án cũ;
- include_optimal=True kèm include_or_opt=True trả or_opt_gap_pct hợp lệ;
- Case demo 'Kho + 5 điểm giao' (data/demo/cases.json) trên đồ thị thật đạt tối ưu toàn cục.
"""

from __future__ import annotations

import json
from pathlib import Path
import random

from fastapi.testclient import TestClient
import pytest

from app.algorithms.tour import (
    choose_tour,
    held_karp,
    nearest_neighbor,
    or_opt,
    tour_cost,
    two_opt,
)
from app.graph.model import load_graph
from app.main import app
from mini_cases import load_mini


ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "data" / "demo" / "cases.json"
MANIFEST_PATH = ROOT / "data" / "processed" / "manifest.json"


def is_tour(order: list[int], n: int) -> bool:
    """Tour hợp lệ: đủ n điểm, không trùng, kho ở đầu."""
    return len(order) == n and order[0] == 0 and sorted(order) == list(range(n))


def seed_matrix(seed: int, n: int = 5) -> list[list[float]]:
    """Tạo ma trận chi phí có hướng ngẫu nhiên (bất đối xứng)."""
    rng = random.Random(seed)
    return [[0.0 if i == j else float(rng.randint(1, 100)) for j in range(n)] for i in range(n)]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


# --- 1. Ràng buộc đầu vào và các trường hợp suy biến ---

def test_or_opt_input_validation():
    with pytest.raises(ValueError, match="ít nhất 1 hàng"):
        or_opt([], [0])

    with pytest.raises(ValueError, match="vuông"):
        or_opt([[0.0, 1.0]], [0, 1])

    with pytest.raises(ValueError, match="không âm"):
        or_opt([[0.0, -1.0], [1.0, 0.0]], [0, 1])

    with pytest.raises(ValueError, match="đúng 2 điểm"):
        or_opt([[0.0, 1.0], [1.0, 0.0]], [0])

    with pytest.raises(ValueError, match="hoán vị"):
        or_opt([[0.0, 1.0, 2.0], [1.0, 0.0, 2.0], [2.0, 1.0, 0.0]], [0, 1, 1])

    with pytest.raises(ValueError, match="kho"):
        or_opt([[0.0, 1.0], [1.0, 0.0]], [1, 0])


def test_or_opt_degenerate_sizes():
    # n = 1
    D1 = [[0.0]]
    assert or_opt(D1, [0]) == [0]

    # n = 2
    D2 = [[0.0, 5.0], [7.0, 0.0]]
    assert or_opt(D2, [0, 1]) == [0, 1]

    # n = 3 (chỉ có duy nhất một hoán vị điểm giao [0, 1, 2] vs [0, 2, 1])
    D3 = [[0.0, 1.0, 10.0], [10.0, 0.0, 1.0], [1.0, 10.0, 0.0]]
    res = or_opt(D3, [0, 2, 1])
    assert is_tour(res, 3)
    assert tour_cost(D3, res) <= tour_cost(D3, [0, 2, 1])


def test_or_opt_does_not_mutate_input():
    D = seed_matrix(42, n=6)
    order = [0, 3, 1, 5, 2, 4]
    before = list(order)
    improved = or_opt(D, order)
    assert order == before
    assert is_tour(improved, 6)


# --- 2. Thoát cực tiểu địa phương của 2-opt ---

def test_or_opt_escapes_2opt_local_minimum():
    # Ma trận hạt giống 8: 2-opt dừng ở cực tiểu địa phương 157.0; Or-opt tìm được 104.0 (-33.8%)
    D = seed_matrix(seed=8, n=5)
    nn = nearest_neighbor(D)
    opt2 = two_opt(D, nn)
    c_2opt = tour_cost(D, opt2)

    or_res = or_opt(D, opt2)
    c_or = tour_cost(D, or_res)

    assert is_tour(or_res, 5)
    assert c_2opt == pytest.approx(157.0)
    assert c_or == pytest.approx(104.0)
    assert c_or < c_2opt - 1e-9


# --- 3. Đánh giá trên >= 200 ma trận bất đối xứng ngẫu nhiên ---

def test_or_opt_200_random_asymmetric_matrices_vs_held_karp():
    """Kiểm tra >= 200 ma trận ngẫu nhiên n in [4, 9]:
    - or_opt luôn là hoán vị hợp lệ với kho tại 0;
    - cost(or_opt) <= cost(2-opt);
    - cost(or_opt) >= cost(held_karp) - 1e-9 (không thể thấp hơn tối ưu toàn cục).
    """
    total = 200
    improved_over_2opt_count = 0
    match_optimal_count = 0

    for seed in range(total):
        n = 4 + (seed % 6)  # n in [4, 5, 6, 7, 8, 9]
        D = seed_matrix(seed=seed, n=n)

        nn = nearest_neighbor(D)
        opt2 = two_opt(D, nn)
        c_2opt = tour_cost(D, opt2)

        opt_or = or_opt(D, opt2)
        c_or = tour_cost(D, opt_or)

        hk = held_karp(D)
        c_hk = tour_cost(D, hk)

        assert is_tour(opt_or, n), f"Seed {seed}: invalid tour"
        assert c_or <= c_2opt + 1e-12, f"Seed {seed}: or_opt ({c_or}) > 2-opt ({c_2opt})"
        assert c_or >= c_hk - 1e-9, f"Seed {seed}: or_opt ({c_or}) < held_karp ({c_hk})"

        if c_or < c_2opt - 1e-6:
            improved_over_2opt_count += 1
        if abs(c_or - c_hk) < 1e-6:
            match_optimal_count += 1

    # Tỷ lệ cải thiện và tỷ lệ chạm tối ưu đạt mức cao
    assert improved_over_2opt_count > 100
    assert match_optimal_count > 120


# --- 4. Tích hợp API /api/tour ---

def test_api_tour_default_remains_unchanged(client):
    """Khi không truyền include_or_opt hoặc truyền False, candidates chỉ gồm 3 phương án cũ."""
    body = {
        "depot": {"lat": 10.77251, "lon": 106.69801},
        "stops": [
            {"id": "b", "lat": 10.77519, "lon": 106.7016577},
            {"id": "a", "lat": 10.77251, "lon": 106.7016577},
            {"id": "t", "lat": 10.77251, "lon": 106.70532},
        ],
    }
    r_default = client.post("/api/tour", json=body).json()
    assert r_default["status"] == "ok"
    assert set(r_default["candidates"]) == {"input", "nearest_neighbor", "nearest_neighbor_2opt"}
    assert r_default["chosen"] == "nearest_neighbor"

    r_false = client.post("/api/tour", json={**body, "include_or_opt": False}).json()

    def strip_runtime(d: dict) -> dict:
        return {k: v for k, v in d.items() if not k.endswith("_runtime_ms")}

    assert strip_runtime(r_false) == strip_runtime(r_default)


def test_api_tour_with_include_or_opt(client):
    """Khi include_or_opt=True, candidates có thêm 'nearest_neighbor_2opt_oropt',
    chosen vẫn chỉ nằm trong 3 phương án cũ."""
    body = {
        "depot": {"lat": 10.77251, "lon": 106.69801},
        "stops": [
            {"id": "b", "lat": 10.77519, "lon": 106.7016577},
            {"id": "a", "lat": 10.77251, "lon": 106.7016577},
            {"id": "t", "lat": 10.77251, "lon": 106.70532},
        ],
        "include_or_opt": True,
    }
    r = client.post("/api/tour", json=body).json()
    assert r["status"] == "ok"
    c = r["candidates"]
    assert set(c) == {"input", "nearest_neighbor", "nearest_neighbor_2opt", "nearest_neighbor_2opt_oropt"}
    assert r["chosen"] in {"input", "nearest_neighbor", "nearest_neighbor_2opt"}

    cand_or = c["nearest_neighbor_2opt_oropt"]
    cand_2opt = c["nearest_neighbor_2opt"]
    assert cand_or["cost_s"] <= cand_2opt["cost_s"] + 1e-9
    assert cand_or["stop_order"] == ["a", "t", "b"]
    assert cand_or["cost_s"] == pytest.approx(180.0)


def test_api_tour_with_include_optimal_and_or_opt(client):
    """Khi bật cả include_optimal và include_or_opt, optimal có thêm or_opt_gap_pct."""
    body = {
        "depot": {"lat": 10.77251, "lon": 106.69801},
        "stops": [
            {"id": "b", "lat": 10.77519, "lon": 106.7016577},
            {"id": "a", "lat": 10.77251, "lon": 106.7016577},
            {"id": "t", "lat": 10.77251, "lon": 106.70532},
        ],
        "include_or_opt": True,
        "include_optimal": True,
    }
    r = client.post("/api/tour", json=body).json()
    assert r["status"] == "ok"
    assert r["optimal"] is not None
    assert r["optimal"]["cost_s"] == pytest.approx(180.0)
    assert r["optimal"]["gap_pct"] == pytest.approx(0.0)
    assert r["optimal"]["or_opt_gap_pct"] == pytest.approx(0.0)


# --- 5. Case demo 'Kho + 5 điểm giao' trên đồ thị thật ---

def test_demo_case_kho_5_diem_real_graph(client, monkeypatch):
    """Case demo 'Kho + 5 điểm giao' (data/demo/cases.json) trên đồ thị thật:
    Đối chiếu chi phí input / NN / 2-opt / Or-opt / Held-Karp.
    """
    if not MANIFEST_PATH.exists() or not CASES_PATH.exists():
        pytest.skip("Thiếu manifest hoặc cases.json")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    graph_path = ROOT / manifest["file"]
    if not graph_path.exists():
        pytest.skip(f"Chưa có file đồ thị {graph_path}")

    monkeypatch.setenv("SAIGO_GRAPH", str(graph_path))
    monkeypatch.setenv("SAIGO_SCENARIOS", str(ROOT / "data" / "config" / "scenarios.json"))

    cases_data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    demo_tour = next((c for c in cases_data["cases"] if c["id"] == "kho-5-diem"), None)
    assert demo_tour is not None

    depot = {"lat": demo_tour["depot"]["lat"], "lon": demo_tour["depot"]["lon"]}
    stops = [{"id": f"p{i+1}", "lat": s["lat"], "lon": s["lon"]} for i, s in enumerate(demo_tour["stops"])]

    body = {
        "depot": depot,
        "stops": stops,
        "scenario_id": "baseline",
        "include_or_opt": True,
        "include_optimal": True,
    }
    with TestClient(app) as real_client:
        res = real_client.post("/api/tour", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"

    c = data["candidates"]
    c_input = c["input"]["cost_s"]
    c_nn = c["nearest_neighbor"]["cost_s"]
    c_2opt = c["nearest_neighbor_2opt"]["cost_s"]
    c_or = c["nearest_neighbor_2opt_oropt"]["cost_s"]
    c_opt = data["optimal"]["cost_s"]
    or_gap = data["optimal"]["or_opt_gap_pct"]

    # Số đo thật trên đồ thị r2000
    assert c_input == pytest.approx(1065.96, abs=0.1)
    assert c_nn == pytest.approx(1003.26, abs=0.1)
    assert c_2opt == pytest.approx(898.07, abs=0.1)
    assert c_or == pytest.approx(627.82, abs=0.1)
    assert c_opt == pytest.approx(627.82, abs=0.1)
    assert or_gap == pytest.approx(0.0, abs=1e-3)
    assert data["chosen"] == "nearest_neighbor_2opt"
