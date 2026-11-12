"""Kiểm tra endpoint /api/route trên đồ thị mini.json theo contract v1 (T13, issue #49)."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.main import app

# Tọa độ gần node S (id 0) và node T (id 2) trong mini.json
# S: lat = 10.7725, lon = 106.6980
# T: lat = 10.7725, lon = 106.7053154
NEAR_S = {"lat": 10.77251, "lon": 106.69801}
NEAR_T = {"lat": 10.77252, "lon": 106.70532}


@pytest.fixture
def client():
    """Khởi tạo TestClient với lifespan nạp đồ thị mini.json."""
    with TestClient(app) as c:
        yield c


def test_route_s_to_t_dijkstra(client: TestClient):
    """Bấm gần S và gần T: cost_s = 80, geometry bắt đầu ở S và kết thúc ở T."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_T,
        "algorithms": ["dijkstra"],
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 200, res.text
    data = res.json()

    # Kiểm tra các trường cơ bản của contract v1
    assert data["dataset_id"] == "mini"
    assert "snapshot_id" in data
    assert data["snapped"]["source"]["node_id"] == 0
    assert data["snapped"]["target"]["node_id"] == 2
    assert data["snapped"]["source"]["snap_distance_m"] >= 0
    assert data["snapped"]["target"]["snap_distance_m"] >= 0

    # Kiểm tra kết quả Dijkstra
    assert "dijkstra" in data["results"]
    d_res = data["results"]["dijkstra"]
    assert d_res["status"] == "ok"
    assert d_res["cost_s"] == pytest.approx(80.0)
    assert d_res["distance_m"] > 0
    assert d_res["expanded"] == 5
    assert d_res["runtime_ms"] >= 0

    # Tuyến S -> A -> T có edge_ids [0, 4]
    assert d_res["edge_ids"] == [0, 4]

    # Kiểm tra geometry GeoJSON LineString
    geom = d_res["geometry"]
    assert geom["type"] == "LineString"
    coords = geom["coordinates"]
    assert len(coords) >= 3

    # Geometry bắt đầu ở S ([106.698, 10.7725]) và kết thúc ở T ([106.7053154, 10.7725])
    assert coords[0][0] == pytest.approx(106.698, rel=1e-5)
    assert coords[0][1] == pytest.approx(10.7725, rel=1e-5)
    assert coords[-1][0] == pytest.approx(106.7053154, rel=1e-5)
    assert coords[-1][1] == pytest.approx(10.7725, rel=1e-5)


def test_route_t_to_s_reverse(client: TestClient):
    """Đảo chiều: bấm gần T đến gần S: cost_s = 100."""
    req_data = {
        "source": NEAR_T,
        "target": NEAR_S,
        "algorithms": ["dijkstra"],
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 200
    data = res.json()

    assert data["snapped"]["source"]["node_id"] == 2
    assert data["snapped"]["target"]["node_id"] == 0

    d_res = data["results"]["dijkstra"]
    assert d_res["status"] == "ok"
    assert d_res["cost_s"] == pytest.approx(100.0)

    # Geometry bắt đầu ở T và kết thúc ở S
    coords = d_res["geometry"]["coordinates"]
    assert coords[0][0] == pytest.approx(106.7053154, rel=1e-5)
    assert coords[0][1] == pytest.approx(10.7725, rel=1e-5)
    assert coords[-1][0] == pytest.approx(106.698, rel=1e-5)
    assert coords[-1][1] == pytest.approx(10.7725, rel=1e-5)


def test_route_both_algorithms_costs_match(client: TestClient):
    """Chạy cả Dijkstra và A*: cả hai trả cùng chi phí, costs_match = True."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_T,
        "algorithms": ["dijkstra", "astar"],
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 200
    data = res.json()

    assert data["costs_match"] is True
    assert "dijkstra" in data["results"]
    assert "astar" in data["results"]

    d_res = data["results"]["dijkstra"]
    a_res = data["results"]["astar"]

    assert d_res["status"] == "ok"
    assert a_res["status"] == "ok"
    assert d_res["cost_s"] == pytest.approx(80.0)
    assert a_res["cost_s"] == pytest.approx(80.0)
    assert d_res["geometry"]["coordinates"] == a_res["geometry"]["coordinates"]


def test_route_unknown_scenario_returns_422(client: TestClient):
    """Kịch bản không có trong file kịch bản đang nạp → 422 (T51)."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_T,
        "scenario_id": "khong-co-kich-ban-nay",
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 422
    assert "Không có kịch bản" in res.text


def test_route_blocked_edge_is_avoided(client: TestClient):
    """T51: đóng cạnh 4 (A→T) thì S→T đi vòng qua B, 100 s, không dùng cạnh đóng."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_T,
        "blocked_edge_ids": [4],
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 200
    d = res.json()["results"]["dijkstra"]
    assert d["cost_s"] == pytest.approx(100.0)
    assert 4 not in d["edge_ids"]


def test_route_negative_trace_limit_returns_422(client: TestClient):
    """trace_limit < 0 phải trả về 422 (Review mục 3)."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_T,
        "trace_limit": -1,
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 422


def test_route_excessive_trace_limit_returns_422(client: TestClient):
    """trace_limit > 5000 phải trả về 422 (Review mục 3)."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_T,
        "trace_limit": 5001,
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 422


def test_route_valid_trace_limit(client: TestClient):
    """trace_limit hợp lệ trả về trace coordinates."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_T,
        "trace_limit": 5,
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 200
    data = res.json()
    trace = data["results"]["dijkstra"]["trace"]
    assert len(trace) > 0
    assert len(trace[0]) == 2  # [lon, lat]


def test_route_missing_source_returns_422(client: TestClient):
    """Thiếu trường source trả về lỗi 422 Unprocessable Entity."""
    req_data = {
        "target": NEAR_T,
        "algorithms": ["dijkstra"],
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 422


def test_route_missing_target_returns_422(client: TestClient):
    """Thiếu trường target trả về lỗi 422."""
    req_data = {
        "source": NEAR_S,
        "algorithms": ["dijkstra"],
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 422


def test_route_unknown_algorithm_returns_422(client: TestClient):
    """Yêu cầu thuật toán không hỗ trợ trả về mã lỗi 422."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_T,
        "algorithms": ["dijkstra", "floyd_warshall"],
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 422


def test_route_invalid_coordinates_returns_422(client: TestClient):
    """Tọa độ vượt ngoài phạm vi [-90, 90] hoặc [-180, 180] trả về lỗi 422."""
    req_data = {
        "source": {"lat": 1000.0, "lon": 106.698},
        "target": NEAR_T,
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 422


def test_route_source_equals_target(client: TestClient):
    """Khi source và target snap về cùng một node: cost_s = 0, distance_m = 0."""
    req_data = {
        "source": NEAR_S,
        "target": NEAR_S,
    }
    res = client.post("/api/route", json=req_data)
    assert res.status_code == 200
    data = res.json()

    d_res = data["results"]["dijkstra"]
    assert d_res["status"] == "ok"
    assert d_res["cost_s"] == pytest.approx(0.0)
    assert d_res["distance_m"] == pytest.approx(0.0)
    assert d_res["edge_ids"] == []
    assert len(d_res["geometry"]["coordinates"]) == 1


def test_route_dataset_not_loaded_returns_503(client: TestClient):
    """Khi app.state không có graph, gọi /api/route trả về lỗi 503."""
    orig_graph = app.state.graph
    try:
        app.state.graph = None
        req_data = {
            "source": NEAR_S,
            "target": NEAR_T,
        }
        res = client.post("/api/route", json=req_data)
        assert res.status_code == 503
        assert "Chưa nạp đồ thị" in res.json()["detail"]
    finally:
        app.state.graph = orig_graph
