"""T72: ma trận chi phí từ đồ thị và /api/tour (docs/TOPIC.md mục 10, 15.3–15.4, 17.3).

Đáp án trên mini.json (10 m/s): S→A 40 s, A→T 40 s, T→B 50 s, B→S 50 s, S→B 50 s; C và D không
có cạnh ra nên không quay về kho được. Tour S→A→T→B→S = 180 s là tối ưu trong cả 6 hoán vị;
thứ tự nhập B, A, T cho 50 + 90 + 40 + 100 = 280 s.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.algorithms.dijkstra import dijkstra, dijkstra_many
from app.algorithms.tour import HELD_KARP_MAX_POINTS
from app.graph.scenario import baseline_snapshot, build_snapshot, load_scenarios
from app.main import app
from mini_cases import MINI, edge_id, load_mini

LON_A = 106.7016577
P = {
    "S": {"lat": 10.77251, "lon": 106.69801},
    "A": {"lat": 10.77251, "lon": LON_A},
    "T": {"lat": 10.77251, "lon": 106.70532},
    "B": {"lat": 10.77519, "lon": LON_A},
    "C": {"lat": 10.77251, "lon": 106.69526},
}


def stop(name):
    return {"id": name.lower(), **P[name]}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def mini():
    return load_mini()


def tour(client, names, **kw):
    body = {"depot": P["S"], "stops": [stop(n) for n in names]}
    body.update(kw)
    return client.post("/api/tour", json=body)


# --- R1: Dijkstra một nguồn tới nhiều đích ---

def test_dijkstra_many_matches_single_target(mini):
    graph, _ = mini
    snap = baseline_snapshot(graph)
    n = len(graph.node_lat)
    for s in range(n):
        dist, _ = dijkstra_many(graph, snap, s, list(range(n)))
        for t in range(n):
            want = dijkstra(graph, snap, s, t).cost_s
            assert dist[t] == (pytest.approx(want) if want is not None else math.inf), (s, t)


# --- R3, R4: ba phương án, chi phí = tổng các cạnh đã dựng ---

def check_closed_route(graph, weights, cand, depot):
    edges = cand["edge_ids"]
    assert graph.edge_u[edges[0]] == depot and graph.edge_v[edges[-1]] == depot
    for e1, e2 in zip(edges, edges[1:]):
        assert graph.edge_v[e1] == graph.edge_u[e2]      # nối tiếp, đúng chiều
    assert cand["cost_s"] == pytest.approx(sum(weights[e] for e in edges))
    assert cand["distance_m"] == pytest.approx(sum(graph.edge_length_m[e] for e in edges))


def test_tour_returns_three_candidates_with_exact_costs(client, mini):
    graph, _ = mini
    r = tour(client, ["B", "A", "T"]).json()
    assert r["status"] == "ok"
    c = r["candidates"]
    assert set(c) == {"input", "nearest_neighbor", "nearest_neighbor_2opt"}
    assert c["input"]["stop_order"] == ["b", "a", "t"]
    assert c["input"]["cost_s"] == pytest.approx(280.0)
    assert c["nearest_neighbor"]["stop_order"] == ["a", "t", "b"]
    assert c["nearest_neighbor"]["cost_s"] == pytest.approx(180.0)
    assert c["nearest_neighbor"]["improvement_pct"] == pytest.approx(100 * 100 / 280)
    assert r["chosen"] == "nearest_neighbor"
    weights = baseline_snapshot(graph).weights
    for cand in c.values():
        check_closed_route(graph, weights, cand, depot=0)
    assert r["candidates"]["input"]["geometry"]["coordinates"][0] == [graph.node_lon[0], graph.node_lat[0]]


def test_input_order_kept_when_already_best(client):
    r = tour(client, ["A", "T", "B"]).json()
    assert r["chosen"] == "input" and r["candidates"]["input"]["improvement_pct"] == 0


def test_include_optimal_reports_gap(client):
    r = tour(client, ["B", "A", "T"], include_optimal=True).json()
    assert r["optimal"]["cost_s"] == pytest.approx(180.0)
    assert r["optimal"]["gap_pct"] == pytest.approx(0.0)    # gap của phương án được chọn


def test_optimal_candidate_drawable_never_chosen(client, mini):
    """Review UI 14/11 đợt 2: thẻ Held–Karp xem được trên bản đồ → `candidates.optimal` có đủ hình học,
    cùng chi phí và thứ tự với `optimal`, không bao giờ là `chosen`; không xin thì không có."""
    graph, _ = mini
    r = tour(client, ["B", "A", "T"], include_optimal=True).json()
    opt = r["candidates"]["optimal"]
    assert opt["cost_s"] == pytest.approx(r["optimal"]["cost_s"]) == pytest.approx(180.0)
    assert opt["stop_order"] == r["optimal"]["stop_order"]
    assert len(opt["edge_geometries"]) == len(opt["edge_ids"]) > 0
    check_closed_route(graph, baseline_snapshot(graph).weights, opt, depot=0)
    assert r["chosen"] != "optimal"
    assert "optimal" not in tour(client, ["B", "A", "T"]).json()["candidates"]


def test_single_stop(client):
    r = tour(client, ["A"]).json()
    assert r["candidates"]["input"]["stop_order"] == ["a"]
    assert r["candidates"]["input"]["cost_s"] == pytest.approx(40 + 40 + 100)   # S→A→T→B→S


# --- R2: chặng không hữu hạn ---

def test_unreachable_stop_gives_infeasible(client):
    r = tour(client, ["A", "C"]).json()
    assert r["status"] == "infeasible_under_model"
    assert r["candidates"] == {} and r["chosen"] is None
    assert {"from_id": "c", "to_id": "depot"} in r["unreachable"]


# --- R5: kịch bản, đóng đường, snap ---

def test_scenario_and_blocked_edges_use_new_snapshot(client, mini):
    graph, meta = mini
    scen = load_scenarios("tests/fixtures/scenarios_mini.json")["un-tac-tam-a"]
    r = tour(client, ["B", "A", "T"], scenario_id="un-tac-tam-a").json()
    weights = build_snapshot(graph, meta, scen).weights
    for cand in r["candidates"].values():
        check_closed_route(graph, weights, cand, depot=0)
    assert r["candidates"]["nearest_neighbor"]["cost_s"] > 180.0
    blocked = tour(client, ["A", "T", "B"], blocked_edge_ids=[edge_id(graph, meta, "A->T")]).json()
    assert blocked["status"] == "infeasible_under_model"      # A chỉ có cạnh ra A→T


def test_duplicate_points_rejected(client):
    res = client.post("/api/tour", json={"depot": P["S"], "stops": [stop("A"), {"id": "a2", **P["A"]}]})
    assert res.status_code == 422
    assert "trùng" in res.json()["detail"]


def test_far_stop_names_the_stop(client):
    res = client.post("/api/tour", json={"depot": P["S"], "stops": [{"id": "xa", "lat": 10.79, "lon": 106.698}]})
    assert res.status_code == 422
    assert "xa" in res.json()["detail"] and "150" in res.json()["detail"]


def test_stop_count_limits(client):
    assert client.post("/api/tour", json={"depot": P["S"], "stops": []}).status_code == 422
    too_many = client.post("/api/tour", json={"depot": P["S"], "stops": [{"id": f"s{i}", **P["A"]} for i in range(15)]})
    assert too_many.status_code == 422 and too_many.json()["detail"][0]["type"] == "too_long"
    # 14 điểm qua được giới hạn số lượng; ở mini.json chúng trùng node nên mới bị 422 vì trùng.
    fourteen = client.post("/api/tour", json={"depot": P["S"], "stops": [{"id": f"s{i}", **P["A"]} for i in range(14)]})
    assert fourteen.status_code == 422 and "trùng" in fourteen.json()["detail"]


def test_optimal_limited_by_held_karp_size(client):
    over = [{"id": f"s{i}", **P["A"]} for i in range(HELD_KARP_MAX_POINTS)]      # + kho = vượt 1 điểm
    res = client.post("/api/tour", json={"depot": P["S"], "stops": over, "include_optimal": True})
    assert res.status_code == 422 and "Held–Karp" in res.json()["detail"]
    at_limit = over[:HELD_KARP_MAX_POINTS - 1]                                   # vừa đúng giới hạn
    res = client.post("/api/tour", json={"depot": P["S"], "stops": at_limit, "include_optimal": True})
    assert res.status_code == 422 and "trùng" in res.json()["detail"]           # qua giới hạn Held–Karp


def test_open_tour_not_supported(client):
    res = tour(client, ["A"], return_to_depot=False)
    assert res.status_code == 422


@pytest.mark.parametrize("path", ["/api/route", "/api/tour"])
def test_boolean_is_not_an_edge_id(client, path):
    body = ({"source": P["S"], "target": P["T"]} if path == "/api/route"
            else {"depot": P["S"], "stops": [stop("A")]})
    assert client.post(path, json={**body, "blocked_edge_ids": [False]}).status_code == 422


@pytest.mark.parametrize("path", ["/api/route", "/api/tour"])
def test_empty_scenario_id_rejected(client, path):
    body = ({"source": P["S"], "target": P["T"]} if path == "/api/route"
            else {"depot": P["S"], "stops": [stop("A")]})
    res = client.post(path, json={**body, "scenario_id": ""})
    assert res.status_code == 422


# --- R1 (docs/tasks/R1-tour-closure.md): lập lại tour sau khi đóng đường ---

def test_kept_order_absent_without_keep_order(client):
    """Không gửi trường mới thì response như trước: đúng ba ứng viên (phải giữ nguyên)."""
    r = tour(client, ["B", "A", "T"], blocked_edge_ids=[1]).json()
    assert set(r["candidates"]) == {"input", "nearest_neighbor", "nearest_neighbor_2opt"}


def test_keep_order_recomputed_on_new_snapshot(client, mini):
    """C2: đóng S→B (một chiều). Thứ tự cũ B, A, T: S→B đi vòng S→A→T→B 130 s, B→A = B→S→A 90 s,
    A→T 40 s, T→S = T→B→S 100 s → 360 s (trước khi đóng 280 s). NN vẫn 180 s và vẫn được chọn."""
    graph, meta = mini
    s_b = edge_id(graph, meta, "S->B")
    r = tour(client, ["B", "A", "T"], blocked_edge_ids=[s_b], keep_order=["b", "a", "t"]).json()
    assert r["status"] == "ok"
    kept = r["candidates"]["kept_order"]
    assert kept["stop_order"] == ["b", "a", "t"]
    assert kept["cost_s"] == pytest.approx(360.0)
    assert kept["improvement_pct"] == pytest.approx(0.0)      # cùng thứ tự với thứ tự nhập ở ví dụ này
    assert r["chosen"] == "nearest_neighbor" and r["candidates"]["nearest_neighbor"]["cost_s"] == pytest.approx(180.0)
    weights = build_snapshot(graph, meta, load_scenarios("tests/fixtures/scenarios_mini.json")["baseline"],
                             blocked={s_b}).weights
    for cand in r["candidates"].values():
        check_closed_route(graph, weights, cand, depot=0)
        assert s_b not in cand["edge_ids"]


def test_kept_order_not_counted_in_chosen_or_gap(client, mini):
    """C2: phương án giữ thứ tự cũ không được chọn và không tính vào gap, kể cả khi nó rẻ nhất."""
    graph, meta = mini
    r = tour(client, ["B", "A", "T"], blocked_edge_ids=[edge_id(graph, meta, "S->B")],
             keep_order=["a", "t", "b"], include_optimal=True).json()
    assert r["candidates"]["kept_order"]["cost_s"] == pytest.approx(180.0)
    assert r["chosen"] in {"input", "nearest_neighbor", "nearest_neighbor_2opt"}
    chosen_cost = r["candidates"][r["chosen"]]["cost_s"]
    assert r["optimal"]["gap_pct"] == pytest.approx(100 * (chosen_cost - 180.0) / 180.0)


@pytest.mark.parametrize("keep", [["a", "t"], ["a", "t", "b", "b"], ["a", "t", "x"], ["a", "a", "t"], []])
def test_keep_order_must_be_permutation_of_stops(client, keep):
    """C1: thiếu, thừa, trùng, id lạ → 422 tiếng Việt."""
    res = tour(client, ["B", "A", "T"], keep_order=keep)
    assert res.status_code == 422
    assert "keep_order" in str(res.json()["detail"])


def test_keep_order_on_infeasible_tour(client, mini):
    """C4: không khả thi thì vẫn infeasible, không có ứng viên nào (kể cả giữ thứ tự cũ)."""
    graph, meta = mini
    r = tour(client, ["A", "T", "B"], blocked_edge_ids=[edge_id(graph, meta, "A->T")],
             keep_order=["a", "t", "b"]).json()
    assert r["status"] == "infeasible_under_model" and r["candidates"] == {}


def test_candidate_edge_geometries_and_twins(client, mini):
    """C3: hình học từng cạnh nối lại ra đúng geometry; cạnh đối như /api/route."""
    graph, meta = mini
    r = tour(client, ["B", "A", "T"]).json()
    s_b, b_s = edge_id(graph, meta, "S->B"), edge_id(graph, meta, "B->S")
    for cand in r["candidates"].values():
        assert len(cand["edge_geometries"]) == len(cand["edge_ids"]) == len(cand["edge_twin_ids"])
        joined = []
        for g in cand["edge_geometries"]:
            joined.extend(g if not joined or joined[-1] != g[0] else g[1:])
        assert joined == cand["geometry"]["coordinates"]
    inp = r["candidates"]["input"]                               # S→B là cạnh đầu của thứ tự B, A, T
    assert inp["edge_ids"][0] == s_b and inp["edge_twin_ids"][0] == b_s


# --- R1 trên đồ thị thật vùng demo (tự bỏ qua nếu chưa dựng dữ liệu) ---

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def demo_client(monkeypatch):
    manifest = ROOT / "data" / "processed" / "manifest.json"
    if not manifest.exists():
        pytest.skip("Chưa có data/processed/manifest.json")
    graph_path = ROOT / json.loads(manifest.read_text(encoding="utf-8"))["file"]
    if not graph_path.exists():
        pytest.skip(f"Chưa có file đồ thị {graph_path}")
    monkeypatch.setenv("SAIGO_GRAPH", str(graph_path))
    monkeypatch.setenv("SAIGO_SCENARIOS", str(ROOT / "data" / "config" / "scenarios.json"))
    with TestClient(app) as c:
        yield c


def demo_case(case_id):
    cases = json.loads((ROOT / "data" / "demo" / "cases.json").read_text(encoding="utf-8"))["cases"]
    c = next(x for x in cases if x["id"] == case_id)
    body = {"depot": {"lat": c["depot"]["lat"], "lon": c["depot"]["lon"]},
            "stops": [{"id": f"p{i + 1}", "lat": s["lat"], "lon": s["lon"]} for i, s in enumerate(c["stops"])],
            "scenario_id": c.get("scenario_id", "baseline"), "blocked_edge_ids": c.get("blocked_edge_ids", [])}
    if "keep_order" in c:                     # case dựng sẵn bước 10: UI gửi đúng trường này (review 14/11, PM-3)
        body["keep_order"] = c["keep_order"]
    return body, c


def test_real_close_mid_edge_of_tour_keeps_and_reorders(demo_client):
    """Ví dụ chấp nhận R1: đóng cạnh giữa của tour NN + 2-opt (kèm cạnh đối), giữ thứ tự cũ và sắp lại."""
    body, _ = demo_case("kho-5-diem")
    before = demo_client.post("/api/tour", json=body).json()
    old = before["candidates"]["nearest_neighbor_2opt"]
    assert old["cost_s"] == pytest.approx(898.07, abs=0.1)          # số đã kiểm ở T72/T56
    k = len(old["edge_ids"]) // 2
    blocked = [e for e in (old["edge_ids"][k], old["edge_twin_ids"][k]) if e is not None]
    after = demo_client.post("/api/tour", json={**body, "blocked_edge_ids": blocked,
                                                "keep_order": old["stop_order"]}).json()
    assert after["status"] == "ok"
    kept = after["candidates"]["kept_order"]
    assert kept["stop_order"] == old["stop_order"]
    assert kept["cost_s"] >= old["cost_s"] - 1e-6                    # đóng cạnh chỉ làm đường dài ra
    assert after["chosen"] in {"input", "nearest_neighbor", "nearest_neighbor_2opt"}
    for cand in after["candidates"].values():
        assert not set(blocked) & set(cand["edge_ids"])


def test_real_demo_closure_edge_1666_matches_case(demo_client):
    """Bước 10 của demo: số ghi trong cases.json (expected.close_edge_1666) đúng với API."""
    body, case = demo_case("kho-5-diem")
    exp = case["expected"]["close_edge_1666"]
    r = demo_client.post("/api/tour", json={**body, "blocked_edge_ids": exp["blocked_edge_ids"],
                                            "keep_order": case["expected"]["baseline"]["nn_2opt_order"]}).json()
    c = r["candidates"]
    assert c["kept_order"]["cost_s"] == pytest.approx(exp["kept_order"], abs=0.05)
    assert r["chosen"] == exp["chosen"]
    assert c["nearest_neighbor_2opt"]["cost_s"] == pytest.approx(exp["nearest_neighbor_2opt"], abs=0.05)
    assert c["nearest_neighbor_2opt"]["stop_order"] == exp["nn_2opt_order"]


def test_preset_step10_case_matches_closure_numbers(demo_client):
    """PM-3: case dựng sẵn cho bước 10 phải ra đúng số của expected.close_edge_1666, không cần bấm trúng cạnh."""
    body, case = demo_case("kho-5-diem-dong-ben-bach-dang")
    _, base = demo_case("kho-5-diem")
    exp = base["expected"]["close_edge_1666"]
    assert case["stops"] == base["stops"] and case["depot"] == base["depot"]
    assert body["blocked_edge_ids"] == exp["blocked_edge_ids"]
    assert body["keep_order"] == base["expected"]["baseline"]["nn_2opt_order"]   # thứ tự tour trước khi đóng
    r = demo_client.post("/api/tour", json=body).json()
    c = r["candidates"]
    assert c["kept_order"]["cost_s"] == pytest.approx(exp["kept_order"], abs=0.05)
    assert c["nearest_neighbor_2opt"]["cost_s"] == pytest.approx(exp["nearest_neighbor_2opt"], abs=0.05)
    assert r["chosen"] == exp["chosen"]
    assert c["kept_order"]["cost_s"] == pytest.approx(case["expected"]["kept_order"], abs=0.05)
    assert c["nearest_neighbor_2opt"]["cost_s"] == pytest.approx(case["expected"]["nearest_neighbor_2opt"], abs=0.05)


def test_real_infeasible_case_names_unreachable_stop(demo_client):
    """C7: case 'tour-khong-kha-thi' đóng cạnh duy nhất vào Nhà hát Thành phố (p2)."""
    body, case = demo_case("tour-khong-kha-thi")
    r = demo_client.post("/api/tour", json=body).json()
    assert r["status"] == case["expected"]["status"] == "infeasible_under_model"
    assert r["candidates"] == {}
    assert {p["to_id"] for p in r["unreachable"]} == set(case["expected"]["unreachable_to"])
