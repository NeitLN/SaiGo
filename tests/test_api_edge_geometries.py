"""T54: `edge_geometries` trong /api/route, để UI biết người dùng bấm vào cạnh nào trên tuyến."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.main import app

NEAR_S = {"lat": 10.77251, "lon": 106.69801}
NEAR_T = {"lat": 10.77252, "lon": 106.70532}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


def post(client, **kw):
    body = {"source": NEAR_S, "target": NEAR_T, "algorithms": ["dijkstra", "astar"]}
    body.update(kw)
    res = client.post("/api/route", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_one_geometry_per_edge_in_route_order(client):
    for r in post(client)["results"].values():
        assert len(r["edge_geometries"]) == len(r["edge_ids"]) > 0
        # Nối hình học từng cạnh (bỏ điểm trùng ở chỗ nối) phải ra đúng hình học gộp của tuyến.
        joined = list(r["edge_geometries"][0])
        for g in r["edge_geometries"][1:]:
            joined.extend(g[1:] if joined[-1] == g[0] else g)
        assert joined == r["geometry"]["coordinates"]


def test_edge_geometries_connect(client):
    for r in post(client)["results"].values():
        geoms = r["edge_geometries"]
        for a, b in zip(geoms, geoms[1:]):
            assert a[-1] == b[0]  # cạnh sau bắt đầu ở nơi cạnh trước kết thúc


def test_closing_an_edge_and_its_twin_avoids_it(client):
    first = post(client)["results"]["dijkstra"]
    e, twin = first["edge_ids"][0], first["edge_twin_ids"][0]
    blocked = [x for x in (e, twin) if x is not None]
    second = post(client, blocked_edge_ids=blocked)["results"]["dijkstra"]
    assert not set(blocked) & set(second["edge_ids"])
    assert len(second["edge_geometries"]) == len(second["edge_ids"])


def test_no_path_has_no_edge_geometries(client):
    first = post(client)["results"]["dijkstra"]
    # Đóng mọi cạnh của tuyến (cả chiều đối) cho tới khi không còn đường.
    blocked: set[int] = set()
    for _ in range(10):
        r = post(client, blocked_edge_ids=sorted(blocked))["results"]["dijkstra"]
        if r["status"] == "no_path":
            assert r["edge_ids"] == [] and r["edge_geometries"] == []
            return
        blocked |= {x for x in r["edge_ids"] + r["edge_twin_ids"] if x is not None}
    pytest.fail(f"không ra no_path sau khi đóng {sorted(blocked)} (tuyến đầu {first['edge_ids']})")
