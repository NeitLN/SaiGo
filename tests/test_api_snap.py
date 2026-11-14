"""Review UI 14/11 đợt 2 (PM-7, U-2, U-3, QA-13): kiểm điểm ngay lúc người dùng bấm, và viền vùng dữ liệu.

`GET /api/snap?lat=&lon=` trả node gần nhất (trong SCC) và khoảng cách, kèm `ok` theo đúng ngưỡng 150 m mà
/api/route, /api/tour dùng, để UI từ chối điểm quá xa ngay khi đặt thay vì hỏng cả tour lúc lập.
`/api/dataset` thêm `bbox` của mọi node để UI vẽ viền vùng có dữ liệu.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.services.routing import SNAP_MAX_M
from mini_cases import load_mini

S = {"lat": 10.77251, "lon": 106.69801}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


def test_snap_near_point_is_ok_and_matches_route(client):
    r = client.get("/api/snap", params=S)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["max_m"] == SNAP_MAX_M
    route = client.post("/api/route", json={"source": S, "target": S}).json()
    assert body["node_id"] == route["snapped"]["source"]["node_id"]
    assert body["snap_distance_m"] == pytest.approx(route["snapped"]["source"]["snap_distance_m"])
    assert {"lat", "lon"} <= body.keys()


def test_snap_far_point_is_not_ok_but_still_answers(client):
    body = client.get("/api/snap", params={"lat": 10.79, "lon": 106.698}).json()
    assert body["ok"] is False
    assert body["snap_distance_m"] > SNAP_MAX_M
    # Cùng điểm, /api/route phải từ chối: hai đường dùng chung một ngưỡng.
    res = client.post("/api/route", json={"source": {"lat": 10.79, "lon": 106.698}, "target": S})
    assert res.status_code == 422


def test_snap_rejects_bad_coordinates(client):
    assert client.get("/api/snap", params={"lat": 95, "lon": 106.7}).status_code == 422
    assert client.get("/api/snap", params={"lat": 10.7}).status_code == 422


def test_dataset_bbox_covers_every_node(client):
    graph, _ = load_mini()
    box = client.get("/api/dataset").json()["bbox"]
    assert box["south"] == pytest.approx(min(graph.node_lat))
    assert box["north"] == pytest.approx(max(graph.node_lat))
    assert box["west"] == pytest.approx(min(graph.node_lon))
    assert box["east"] == pytest.approx(max(graph.node_lon))
