"""Test các nhánh của `export_graph` (T31/T61) trên đồ thị giả kiểu OSMnx, chạy được trên CI (không cần OSMnx)."""

import json
import sys
from pathlib import Path

import pytest

nx = pytest.importorskip("networkx")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_data  # noqa: E402

SPEEDS = {"default_kmh": 20, "highway_kmh": {"primary": 35, "primary_link": 35, "residential": 22}}


class Line:
    """Thay cho shapely.LineString: export_graph chỉ đọc `.coords`."""

    def __init__(self, coords):
        self.coords = coords


def fake_osm_graph():
    """4 node quanh Bến Thành; osmid node cố ý không theo thứ tự thêm vào."""
    G = nx.MultiDiGraph()
    pts = {30: (106.6980, 10.7725), 10: (106.6990, 10.7725), 20: (106.6990, 10.7735), 40: (106.7100, 10.7800)}
    for n, (x, y) in pts.items():
        G.add_node(n, x=x, y=y)
    # Đường hai chiều 30 ↔ 10: hai cạnh; cạnh 10 → 30 có hình học bị lưu ngược (bắt đầu ở 30).
    G.add_edge(30, 10, key=0, osmid=[2, 1], highway=["residential", "primary"], oneway=False, length=109.4,
               geometry=Line([(106.6980, 10.7725), (106.6985, 10.7725), (106.6990, 10.7725)]))
    G.add_edge(10, 30, key=0, osmid=[2, 1], highway=["residential", "primary"], oneway=False, length=109.4,
               geometry=Line([(106.6980, 10.7725), (106.6985, 10.7725), (106.6990, 10.7725)]))
    # Một chiều 10 → 20 (không có cạnh ngược), hai cạnh song song 20 → 30, một self-loop ở 20.
    G.add_edge(10, 20, key=0, osmid=5, highway="primary_link", oneway=True, length=111.2)
    # Cạnh 20 → 30 key 0 cố ý ngắn hơn khoảng cách thẳng (~156 m) để kiểm cách đếm vi phạm và hệ số c.
    G.add_edge(20, 30, key=0, osmid=6, highway="residential", oneway=True, length=150.0)
    G.add_edge(20, 30, key=1, osmid=7, highway="unclassified", oneway=True, length=160.0)
    G.add_edge(20, 20, key=0, osmid=8, highway="residential", oneway=True, length=30.0)
    return G


@pytest.fixture()
def exported(tmp_path, monkeypatch):
    monkeypatch.setattr(prepare_data, "ROOT", tmp_path)
    monkeypatch.setattr(prepare_data, "PROCESSED", tmp_path / "processed")
    G = fake_osm_graph()
    scc = max(nx.strongly_connected_components(G), key=len)
    report = prepare_data.export_graph(G, scc, "fake", SPEEDS)
    graph = json.loads((tmp_path / report["file"]).read_text(encoding="utf-8"))
    return report, graph


def test_ids_follow_osmid_and_original_edge_key(exported):
    _, g = exported
    assert [x["osmid"] for x in g["nodes"]] == [10, 20, 30, 40]
    assert [x["id"] for x in g["nodes"]] == [0, 1, 2, 3]
    osmid = [x["osmid"] for x in g["nodes"]]
    keys = [(osmid[e["u"]], osmid[e["v"]], e["key"]) for e in g["edges"]]
    assert keys == sorted(keys)
    assert [e["id"] for e in g["edges"]] == list(range(len(g["edges"])))


def test_oneway_has_no_reverse_edge(exported):
    _, g = exported
    pairs = {(e["u"], e["v"]) for e in g["edges"]}
    oneway = [e for e in g["edges"] if e["oneway"] and e["u"] != e["v"]]
    assert oneway and all((e["v"], e["u"]) not in pairs for e in oneway)


def test_highway_list_takes_fastest_and_way_ids_are_sorted_lists(exported):
    _, g = exported
    two_way = [e for e in g["edges"] if not e["oneway"]]
    assert {e["highway"] for e in two_way} == {"primary"}
    assert all(e["way_ids"] == [1, 2] and e["speed_kmh"] == 35 for e in two_way)
    unknown = next(e for e in g["edges"] if e["highway"] == "unclassified")
    assert unknown["speed_kmh"] == SPEEDS["default_kmh"] and unknown["way_ids"] == [7]


def test_geometry_starts_at_u_and_reversed_count(exported):
    report, g = exported
    nodes = g["nodes"]
    for e in g["edges"]:
        u, v = nodes[e["u"]], nodes[e["v"]]
        assert e["geometry"][0] == [u["lon"], u["lat"]]
        assert e["geometry"][-1] == [v["lon"], v["lat"]]
    assert report["geometry_reversed"] == 1


def test_report_counts(exported):
    report, g = exported
    assert report["node_count"] == 4 and report["edge_count"] == 6
    assert report["parallel_edge_count"] == 1
    assert report["self_loop_count"] == 1
    assert report["oneway_edge_count"] == 4
    assert report["scc_node_count"] == 3 and report["nodes_outside_scc"] == 1
    assert [x["in_scc"] for x in g["nodes"]] == [True, True, True, False]
    assert report["edges_length_below_haversine_1mm"] == 1
    assert 0.95 < report["heuristic_c"] < 0.97  # 150 m / ~155,9 m
