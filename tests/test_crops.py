"""Kiểm tra các vùng cắt lồng nhau do `make_crops.py` xuất ra (T61).

File JSON không có trong Git, nên test tự bỏ qua khi chưa chạy:
    python scripts/make_crops.py
    pytest -m realdata -q
"""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "processed" / "crop_manifest.json"

pytestmark = pytest.mark.realdata


@pytest.fixture(scope="module")
def manifest() -> dict:
    if not MANIFEST.exists():
        pytest.skip("chưa có data/processed/crop_manifest.json")
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing = [s["file"] for s in m["sizes"] if not (ROOT / s["file"]).exists()]
    if missing:
        pytest.skip(f"chưa có {missing}; chạy scripts/make_crops.py trước")
    return m


@pytest.fixture(scope="module")
def graphs(manifest) -> list[dict]:
    return [json.loads((ROOT / s["file"]).read_text(encoding="utf-8")) for s in manifest["sizes"]]


def test_files_match_manifest(manifest, graphs):
    for s, g in zip(manifest["sizes"], graphs):
        assert hashlib.sha256((ROOT / s["file"]).read_bytes()).hexdigest() == s["sha256"]
        assert g["dataset_id"] == s["dataset_id"]
        assert len(g["nodes"]) == s["node_count"] and len(g["edges"]) == s["edge_count"]


def test_sizes_grow(manifest):
    halves = [s["half_side_m"] for s in manifest["sizes"]]
    assert halves == sorted(halves)
    counts = [s["node_count"] for s in manifest["sizes"]]
    assert counts == sorted(counts) and len(set(counts)) == len(counts)


def test_crops_and_sccs_are_nested(graphs):
    """Vùng nhỏ nằm trong vùng lớn, và SCC nhỏ nằm trong SCC lớn (so theo osmid)."""
    nodes = [{x["osmid"] for x in g["nodes"]} for g in graphs]
    sccs = [{x["osmid"] for x in g["nodes"] if x["in_scc"]} for g in graphs]
    for small, big in zip(nodes, nodes[1:]):
        assert small <= big
    for small, big in zip(sccs, sccs[1:]):
        assert small <= big


def test_in_scc_is_exactly_one_scc(graphs):
    """`in_scc` đúng bằng một thành phần liên thông mạnh: không sót node, không lẫn node ngoài."""
    nx = pytest.importorskip("networkx")
    for g in graphs:
        G = nx.DiGraph()
        G.add_nodes_from(x["id"] for x in g["nodes"])
        G.add_edges_from((e["u"], e["v"]) for e in g["edges"])
        marked = {x["id"] for x in g["nodes"] if x["in_scc"]}
        component = next(c for c in nx.strongly_connected_components(G) if next(iter(marked)) in c)
        assert marked == component


def test_crop_2km_equals_demo_graph(manifest):
    """Vùng 2 km phải trùng đồ thị demo của T31 (chỉ khác dataset_id)."""
    crop = next((s for s in manifest["sizes"] if s["half_side_m"] == 2000), None)
    demo = ROOT / "data" / "processed" / "hcm-benthanh-r2000-20261024.json"
    if crop is None or not demo.exists():
        pytest.skip("cần crop_r2000 và đồ thị demo (prepare_data.py build --area demo)")
    a = json.loads((ROOT / crop["file"]).read_text(encoding="utf-8"))
    b = json.loads(demo.read_text(encoding="utf-8"))
    assert a["nodes"] == b["nodes"]
    assert a["edges"] == b["edges"]


def test_load_graph_reads_every_crop(manifest):
    model = pytest.importorskip("app.graph.model", reason="chưa có load_graph (T01)")
    for s in manifest["sizes"]:
        g, _ = model.load_graph(ROOT / s["file"])
        assert len(g.node_lat) == s["node_count"]
        assert len(g.edge_u) == s["edge_count"]
