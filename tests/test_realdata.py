"""Kiểm tra đồ thị thật do `prepare_data.py build` xuất ra (T31).

File JSON không có trong Git (đã gitignore), nên test tự bỏ qua khi chưa build:
    python scripts/prepare_data.py build --area demo
    pytest -m realdata -q
"""

import hashlib
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "processed" / "manifest.json"

pytestmark = pytest.mark.realdata


@pytest.fixture(scope="module")
def manifest() -> dict:
    if not MANIFEST.exists():
        pytest.skip("chưa có data/processed/manifest.json")
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not (ROOT / m["file"]).exists():
        pytest.skip(f"chưa có {m['file']}; chạy prepare_data.py build trước")
    return m


@pytest.fixture(scope="module")
def graph(manifest) -> dict:
    return json.loads((ROOT / manifest["file"]).read_text(encoding="utf-8"))


def test_file_matches_manifest(manifest, graph):
    assert hashlib.sha256((ROOT / manifest["file"]).read_bytes()).hexdigest() == manifest["sha256"]
    assert graph["format"] == "saigo-graph/1"
    assert graph["dataset_id"] == manifest["dataset_id"]
    assert len(graph["nodes"]) == manifest["node_count"]
    assert len(graph["edges"]) == manifest["edge_count"]


def test_ids_and_values_valid(graph):
    """DATA_MODEL mục 2.3."""
    nodes, edges = graph["nodes"], graph["edges"]
    n = len(nodes)
    assert [x["id"] for x in nodes] == list(range(n))
    assert [e["id"] for e in edges] == list(range(len(edges)))
    for x in nodes:
        assert -90 <= x["lat"] <= 90 and -180 <= x["lon"] <= 180
    for e in edges:
        assert 0 <= e["u"] < n and 0 <= e["v"] < n
        assert math.isfinite(e["length_m"]) and e["length_m"] >= 0
        assert math.isfinite(e["speed_kmh"]) and e["speed_kmh"] > 0
        assert isinstance(e["way_ids"], list) and e["way_ids"]


def test_edges_sorted_by_original_key(graph):
    osmid = [x["osmid"] for x in graph["nodes"]]
    keys = [(osmid[e["u"]], osmid[e["v"]], e["key"]) for e in graph["edges"]]
    assert keys == sorted(keys)


def test_geometry_runs_from_u_to_v(graph):
    """Polyline là [lon, lat] và đi đúng chiều cạnh có hướng."""
    nodes = graph["nodes"]
    for e in graph["edges"]:
        (x0, y0), (x1, y1) = e["geometry"][0], e["geometry"][-1]
        u, v = nodes[e["u"]], nodes[e["v"]]
        assert abs(x0 - u["lon"]) < 1e-6 and abs(y0 - u["lat"]) < 1e-6, e["id"]
        assert abs(x1 - v["lon"]) < 1e-6 and abs(y1 - v["lat"]) < 1e-6, e["id"]


def test_in_scc_is_largest_strongly_connected_component(manifest, graph):
    nx = pytest.importorskip("networkx")
    G = nx.MultiDiGraph()
    G.add_nodes_from(x["id"] for x in graph["nodes"])
    G.add_edges_from((e["u"], e["v"]) for e in graph["edges"])
    largest = max(nx.strongly_connected_components(G), key=len)
    assert {x["id"] for x in graph["nodes"] if x["in_scc"]} == largest
    assert len(largest) == manifest["scc_node_count"]


def test_load_graph_reads_file(manifest):
    model = pytest.importorskip("app.graph.model", reason="chưa có load_graph (T01)")
    g, _ = model.load_graph(ROOT / manifest["file"])
    assert len(g.node_lat) == manifest["node_count"]
    assert len(g.edge_u) == manifest["edge_count"]
