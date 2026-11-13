"""T56 R8: `GET /api/network` trả mạng đường của đồ thị đang nạp, để UI vẽ nền khi không tải được tile OSM."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.graph.closures import reverse_twins
from app.main import app
from app.services.routing import edge_coords
from mini_cases import load_mini


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SAIGO_SCENARIOS", "tests/fixtures/scenarios_mini.json")
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def mini():
    return load_mini()


def test_network_returns_one_line_per_road_piece(client, mini):
    graph, meta = mini
    twins = reverse_twins(graph, meta)
    body = client.get("/api/network").json()
    assert body["dataset_id"] == graph.dataset_id
    expected = [edge_coords(graph, meta, e) for e in range(len(graph.edge_u))
                if twins[e] is None or e < twins[e]]          # đoạn hai chiều chỉ vẽ một lần
    assert body["lines"] == expected


def test_network_drops_reverse_twin_of_two_way_roads(client, mini):
    graph, meta = mini
    twins = reverse_twins(graph, meta)
    pairs = [(e, t) for e, t in enumerate(twins) if t is not None and e < t]
    assert pairs, "mini.json cần có ít nhất một đoạn hai chiều để test có nghĩa"
    lines = client.get("/api/network").json()["lines"]
    one_way = sum(1 for t in twins if t is None)
    assert len(lines) == one_way + len(pairs)


def test_network_coordinates_are_lon_lat(client, mini):
    graph, meta = mini
    first = client.get("/api/network").json()["lines"][0]
    u = graph.edge_u[0]
    assert first[0] == [graph.node_lon[u], graph.node_lat[u]]   # [lon, lat] như GeoJSON
