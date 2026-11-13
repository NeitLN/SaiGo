"""T62 (E3, fixed trips): cùng một tập cặp chạy trên nhiều vùng lồng nhau (docs/tasks/T62-scaling.md).

Dùng hai đồ thị lưới tự dựng: lưới 3×3 nằm trong lưới 4×4, cùng `osmid` cho node chung nhưng **đánh số node
khác nhau** (giống các vùng cắt thật, mỗi vùng đánh số lại), để kiểm việc đổi cặp qua `osmid`.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from app.graph.model import load_graph  # noqa: E402
from run_scaling import check_monotone, load_sizes, main, map_queries  # noqa: E402


def _grid(path: Path, k: int, dataset_id: str, reverse_ids: bool, drop: int | None = None) -> Path:
    """Lưới k×k, cạnh hai chiều giữa ô kề nhau. `osmid` = 1000 + 10·hàng + cột (chung cho mọi lưới)."""
    cells = [(r, c) for r in range(k) for c in range(k) if (r * 10 + c) != drop]
    if reverse_ids:
        cells = cells[::-1]
    index = {cell: i for i, cell in enumerate(cells)}
    nodes = [{"id": i, "osmid": 1000 + 10 * r + c, "lat": 10.77 + 0.001 * r, "lon": 106.69 + 0.001 * c, "in_scc": True}
             for i, (r, c) in enumerate(cells)]
    raw = []
    for (r, c), u in index.items():
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            v = index.get((r + dr, c + dc))
            if v is not None:
                # Cạnh ngang dài hơn cạnh dọc một chút để có tuyến duy nhất, không hòa chi phí.
                raw.append((u, v, 130.0 if dr == 0 else 120.0))
    raw.sort()
    edges = [{"id": j, "u": u, "v": v, "key": 0, "way_ids": [], "highway": "residential", "oneway": False,
              "length_m": length, "speed_kmh": 30,
              "geometry": [[nodes[u]["lon"], nodes[u]["lat"]], [nodes[v]["lon"], nodes[v]["lat"]]]}
             for j, (u, v, length) in enumerate(raw)]
    path.write_text(json.dumps({"format": "saigo-graph/1", "dataset_id": dataset_id, "crs": "EPSG:4326",
                                "nodes": nodes, "edges": edges}), encoding="utf-8")
    return path


def _manifest(tmp: Path, graphs: list[tuple[int, Path]]) -> Path:
    sizes = [{"half_side_m": half, "dataset_id": p.stem, "file": str(p),
              "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for half, p in graphs]
    m = tmp / "crop_manifest.json"
    m.write_text(json.dumps({"sizes": sizes}), encoding="utf-8")
    return m


@pytest.fixture
def nested(tmp_path):
    small = _grid(tmp_path / "grid_r1.json", 3, "grid_r1", reverse_ids=False)
    large = _grid(tmp_path / "grid_r2.json", 4, "grid_r2", reverse_ids=True)
    return tmp_path, small, large


def test_map_queries_keeps_same_osm_nodes(nested):
    _, small, large = nested
    g1, m1 = load_graph(small)
    g2, m2 = load_graph(large)
    queries = [{"query_id": 0, "workload": "fixed_trips", "stratum": "dai", "source": 0, "target": 8,
                "hav_m": 300.0, "delta": 0.9}]
    mapped = map_queries(queries, m1, g2, m2)
    q = mapped[0]
    assert (q["source_osmid"], q["target_osmid"]) == (m1.node_osmid[0], m1.node_osmid[8])
    assert m2.node_osmid[q["source"]] == q["source_osmid"]          # id node khác, cùng điểm OSM
    assert m2.node_osmid[q["target"]] == q["target_osmid"]
    assert q["source"] != 0                                           # lưới lớn đánh số ngược nên id đổi thật


def test_map_queries_missing_osmid_is_an_error(nested):
    tmp, small, _ = nested
    holed = _grid(tmp / "grid_hole.json", 4, "grid_hole", reverse_ids=True, drop=22)   # bỏ ô (2, 2) = osmid 1022
    g1, m1 = load_graph(small)
    g2, m2 = load_graph(holed)
    q = [{"query_id": 3, "workload": "fixed_trips", "stratum": "dai", "source": 0,
          "target": m1.node_osmid.index(1022), "hav_m": 300.0, "delta": 0.9}]
    with pytest.raises(ValueError, match="1022"):
        map_queries(q, m1, g2, m2)


def test_load_sizes_rejects_sha256_mismatch(nested):
    tmp, small, large = nested
    manifest = _manifest(tmp, [(1000, small), (2000, large)])
    large.write_text(large.read_text(encoding="utf-8").replace("grid_r2", "grid_rX"), encoding="utf-8")
    with pytest.raises(ValueError, match="sha256"):
        load_sizes(manifest)


def test_check_monotone_flags_cost_increase():
    rows = [
        {"query_id": "0", "algo": "dijkstra", "size_label": "r1000", "status": "ok", "cost_s": "100.0"},
        {"query_id": "0", "algo": "dijkstra", "size_label": "r2000", "status": "ok", "cost_s": "90.0"},
        {"query_id": "1", "algo": "dijkstra", "size_label": "r1000", "status": "ok", "cost_s": "50.0"},
        {"query_id": "1", "algo": "dijkstra", "size_label": "r2000", "status": "ok", "cost_s": "51.0"},
    ]
    bad = check_monotone(rows, ["r1000", "r2000"])
    assert [v["query_id"] for v in bad] == ["1"]


def test_run_scaling_end_to_end(nested):
    tmp, small, large = nested
    manifest = _manifest(tmp, [(2000, large), (1000, small)])          # thứ tự trong manifest không quan trọng
    out = tmp / "results"
    assert main(["--manifest", str(manifest), "--pairs", "6", "--seed", "42", "--repeats", "1", "--warmup", "0",
                 "--out", str(out), "--run-id", "test-scaling"]) == 0
    run = out / "test-scaling"
    with (run / "measurements.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with (run / "queries.csv").open(encoding="utf-8") as f:
        queries = list(csv.DictReader(f))
    n = len(queries)
    assert n > 0
    assert len(rows) == n * 2 * 2                                       # cặp × 2 vùng × 2 thuật toán
    assert {r["suite"] for r in rows} == {"scaling"}
    assert {r["workload"] for r in rows} == {"fixed_trips"}
    assert {r["size_label"] for r in rows} == {"r1000", "r2000"}
    assert {r["run_id"] for r in rows} == {"test-scaling"}
    assert all(r["status"] == "ok" for r in rows)
    assert "source_osmid" in queries[0] and "target_osmid" in queries[0]
    # Cùng cặp ở mọi vùng: osmid của source/target trong từng vùng phải khớp queries.csv
    g = {"r1000": load_graph(small), "r2000": load_graph(large)}
    by_id = {q["query_id"]: q for q in queries}
    for r in rows:
        meta = g[r["size_label"]][1]
        assert meta.node_osmid[int(r["source"])] == int(by_id[r["query_id"]]["source_osmid"])
        assert meta.node_osmid[int(r["target"])] == int(by_id[r["query_id"]]["target_osmid"])
    assert check_monotone(rows, ["r1000", "r2000"]) == []
    with (run / "load.csv").open(encoding="utf-8") as f:
        load = list(csv.DictReader(f))
    assert [x["size_label"] for x in load] == ["r1000", "r2000"]
    assert [int(x["n_nodes"]) for x in load] == [9, 16]
    assert all(float(x["load_ms"]) >= 0 and float(x["peak_mb"]) > 0 for x in load)


def test_missing_osmid_fails_before_writing_anything(nested):
    """Review #109: osmid sai phải báo lỗi gọn (mã 2) và không để lại queries.csv hay sizes/ dở dang."""
    tmp, small, _ = nested
    holed = _grid(tmp / "grid_hole.json", 4, "grid_hole", reverse_ids=True, drop=11)
    manifest = _manifest(tmp, [(1000, small), (2000, holed)])
    out = tmp / "results"
    code = main(["--manifest", str(manifest), "--pairs", "30", "--seed", "1", "--repeats", "1", "--warmup", "0",
                 "--out", str(out), "--run-id", "bad"])
    assert code == 2
    assert not (out / "bad").exists()


def test_config_paths_use_forward_slashes(nested):
    tmp, small, large = nested
    manifest = _manifest(tmp, [(1000, small), (2000, large)])
    out = tmp / "results"
    assert main(["--manifest", str(manifest), "--pairs", "6", "--seed", "42", "--repeats", "1", "--warmup", "0",
                 "--out", str(out), "--run-id", "posix"]) == 0
    assert "\\\\" not in (out / "posix" / "config.json").read_text(encoding="utf-8")
