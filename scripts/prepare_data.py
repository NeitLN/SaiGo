"""Tạo dataset snapshot từ OpenStreetMap (docs/TOPIC.md mục 7, docs/DATA_MODEL.md mục 8).

    python scripts/prepare_data.py --smoke     # T02: tải vùng ~500 m quanh Bến Thành để thử OSMnx
    python scripts/prepare_data.py download    # T30: tải vùng tải một lần → data/raw/outer.graphml + raw_manifest.json
    python scripts/prepare_data.py build --area demo   # T31: cắt vùng → data/processed/<dataset_id>.json + manifest.json

Cần cài nhóm thư viện `data` (OSMnx): `pip install -e ".[data]"`.
Dữ liệu tải về nằm trong data/raw/ và cache/ (đã có trong .gitignore).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.graph.geo import haversine_m  # noqa: E402  (dùng chung với backend, cùng bán kính 6 371 009 m)

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
CONFIG = ROOT / "data" / "config"
VN = timezone(timedelta(hours=7))
ATTRIBUTION = "© OpenStreetMap contributors, dữ liệu theo giấy phép ODbL (https://www.openstreetmap.org/copyright)"
RELEASE = "data-raw-20261024"  # GitHub Release chứa outer.graphml đã đóng băng (T34)

BEN_THANH = (10.7725, 106.6980)  # (lat, lon) chợ Bến Thành
SMOKE_HALF_SIDE_M = 250          # bbox 500 m × 500 m


def import_osmnx():
    try:
        import osmnx as ox
    except ImportError:
        sys.exit('chưa cài OSMnx: pip install -e ".[data]" (xem docs/team/start/MINH.md nếu pip lỗi)')
    ox.settings.cache_folder = str(ROOT / "cache")
    return ox


def first(value):
    """Sau simplify, OSMnx có thể gộp thuộc tính thành list; lấy phần tử đầu để thống kê."""
    return value[0] if isinstance(value, list) else value


def smoke() -> None:
    ox = import_osmnx()
    import networkx as nx

    G = ox.graph_from_point(BEN_THANH, dist=SMOKE_HALF_SIDE_M, dist_type="bbox", network_type="drive")
    oneway = sum(1 for _, _, d in G.edges(data=True) if d.get("oneway") is True)
    highways = Counter(first(d.get("highway")) for _, _, d in G.edges(data=True))

    print(f"graph: {type(G).__name__}, directed={G.is_directed()}")
    print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()} oneway_edges={oneway}")
    print("highway: " + ", ".join(f"{k}={v}" for k, v in highways.most_common()))
    print(f"strongly connected components: {nx.number_strongly_connected_components(G)}, "
          f"largest={len(max(nx.strongly_connected_components(G), key=len))} nodes")

    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / "smoke.graphml"
    ox.save_graphml(G, out)
    print(f"đã lưu {out.relative_to(ROOT)}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(force: bool) -> None:
    """Tải vùng tải (nửa cạnh + đệm) một lần rồi đóng băng; các bước sau chỉ đọc file này."""
    out = RAW / "outer.graphml"
    manifest_path = PROCESSED / "raw_manifest.json"
    if out.exists() and not force:
        sys.exit(f"{out.relative_to(ROOT)} đã có; dữ liệu thô đã đóng băng. Dùng --force nếu thật sự muốn tải lại.")

    ox = import_osmnx()
    import networkx as nx

    areas = json.loads((CONFIG / "areas.json").read_text(encoding="utf-8"))
    center = (areas["center"]["lat"], areas["center"]["lon"])
    dist = areas["download"]["half_side_m"] + areas["download"]["buffer_m"]
    west, south, east, north = ox.utils_geo.bbox_from_point(center, dist)

    downloaded_at = datetime.now(VN)
    G = ox.graph_from_bbox((west, south, east, north), network_type=areas["network_type"],
                           simplify=True, retain_all=True)
    RAW.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(G, out)

    manifest = {
        "dataset_id": f"hcmc-benthanh-{downloaded_at:%Y%m%d}",
        "downloaded_at": downloaded_at.isoformat(timespec="seconds"),
        "center": areas["center"],
        "half_side_m": areas["download"]["half_side_m"],
        "buffer_m": areas["download"]["buffer_m"],
        "bbox": {"west": west, "south": south, "east": east, "north": north},
        "network_type": areas["network_type"],
        "simplify": True,
        "retain_all": True,
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "oneway_edge_count": sum(1 for _, _, d in G.edges(data=True) if d.get("oneway") is True),
        "weak_components": nx.number_weakly_connected_components(G),
        "file": out.relative_to(ROOT).as_posix(),
        "file_bytes": out.stat().st_size,
        "sha256": sha256(out),
        "dependencies": {"python": platform.python_version(), "osmnx": ox.__version__, "networkx": nx.__version__},
        "attribution": ATTRIBUTION,
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"nodes={manifest['node_count']} edges={manifest['edge_count']} oneway_edges={manifest['oneway_edge_count']}")
    print(f"đã lưu {manifest['file']} ({manifest['file_bytes'] / 1e6:.1f} MB, sha256 {manifest['sha256'][:12]}…)")
    print(f"đã ghi {manifest_path.relative_to(ROOT).as_posix()}")


# ---------- build: GraphML thô → saigo-graph/1 (DATA_MODEL mục 2.1 và 8.2) ----------

def as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def main_highway(value, speeds: dict) -> str | None:
    """Một loại đường duy nhất: loại "cao nhất" theo bảng tốc độ; hòa thì lấy loại đứng trước trong bảng."""
    table = list(speeds["highway_kmh"])
    values = as_list(value)
    if not values:
        return None
    return max(values, key=lambda h: (speeds["highway_kmh"].get(h, speeds["default_kmh"]),
                                      -table.index(h) if h in table else -len(table)))


def build(area: str) -> None:
    """Cắt vùng, chuẩn hóa thuộc tính, gán tốc độ, đánh dấu SCC, đánh lại ID, xuất JSON + manifest."""
    # Kiểm file thô trước khi nạp OSMnx, để máy thiếu cả hai thấy đúng việc cần làm trước.
    raw_manifest = json.loads((PROCESSED / "raw_manifest.json").read_text(encoding="utf-8"))
    raw = ROOT / raw_manifest["file"]
    if not raw.exists():
        sys.exit(f"thiếu {raw_manifest['file']}; tải đúng bản đã đóng băng từ Release {RELEASE}: "
                 f"gh release download {RELEASE} -p {raw.name} -D {raw.parent.relative_to(ROOT).as_posix()} "
                 "(xem docs/team/ONBOARDING.md mục 3, \"Tải dữ liệu\"). Không tải lại từ OSM.")
    if sha256(raw) != raw_manifest["sha256"]:
        sys.exit(f"{raw_manifest['file']} không khớp sha256 trong raw_manifest.json; "
                 f"tải lại đúng bản đã đóng băng từ Release {RELEASE} (thêm --clobber để ghi đè)")

    ox = import_osmnx()
    import networkx as nx
    from pyproj import Transformer
    from shapely.geometry import Point

    areas = json.loads((CONFIG / "areas.json").read_text(encoding="utf-8"))
    speeds = json.loads((CONFIG / "speeds.json").read_text(encoding="utf-8"))
    if area in ("center", "download") or not isinstance(areas.get(area), dict) or "half_side_m" not in areas[area]:
        sys.exit(f"không có vùng {area!r} trong data/config/areas.json")
    half = areas[area]["half_side_m"]
    lat0, lon0 = areas["center"]["lat"], areas["center"]["lon"]

    G = ox.load_graphml(raw)

    # Bước 4: giữ node trong hình vuông (mét, hệ chiếu UTM) và cạnh có cả hai đầu bên trong.
    _, utm = ox.projection.project_geometry(Point(lon0, lat0))
    to_utm = Transformer.from_crs("EPSG:4326", utm, always_xy=True)
    cx, cy = to_utm.transform(lon0, lat0)
    keep = [n for n, d in G.nodes(data=True)
            if (lambda x, y: abs(x - cx) <= half and abs(y - cy) <= half)(*to_utm.transform(d["x"], d["y"]))]
    H = G.subgraph(keep).copy()

    # Bước 5: SCC lớn nhất. Node ngoài SCC vẫn giữ để vẽ nhưng không dùng làm điểm snap/benchmark (mục 8.4).
    scc = max(nx.strongly_connected_components(H), key=len)

    # Bước 6: đánh lại ID. Node theo osmid; cạnh theo (u, v, key) gốc, nên ID ổn định với cùng dữ liệu.
    node_ids = {n: i for i, n in enumerate(sorted(H.nodes))}
    nodes = [{"id": node_ids[n], "osmid": n, "lat": round(H.nodes[n]["y"], 7), "lon": round(H.nodes[n]["x"], 7),
              "in_scc": n in scc} for n in sorted(H.nodes)]

    edges, reversed_geom = [], 0
    for j, (u, v, k) in enumerate(sorted(H.edges(keys=True))):
        d = H.edges[u, v, k]
        hw = main_highway(d.get("highway"), speeds)
        if "geometry" in d:
            coords = [[round(x, 7), round(y, 7)] for x, y in d["geometry"].coords]
            # Hình học phải bắt đầu ở u; nếu gần v hơn thì đảo lại.
            ux, uy = H.nodes[u]["x"], H.nodes[u]["y"]
            vx, vy = H.nodes[v]["x"], H.nodes[v]["y"]
            sx, sy = coords[0]
            if (sx - vx) ** 2 + (sy - vy) ** 2 < (sx - ux) ** 2 + (sy - uy) ** 2:
                coords.reverse()
                reversed_geom += 1
        else:
            coords = [[nodes[node_ids[u]]["lon"], nodes[node_ids[u]]["lat"]],
                      [nodes[node_ids[v]]["lon"], nodes[node_ids[v]]["lat"]]]
        edges.append({
            "id": j, "u": node_ids[u], "v": node_ids[v], "key": k,
            "way_ids": sorted(as_list(d.get("osmid"))),
            "highway": hw,
            "oneway": bool(d.get("oneway")),
            "length_m": float(d["length"]),
            "speed_kmh": speeds["highway_kmh"].get(hw, speeds["default_kmh"]),
            "geometry": coords,
        })

    # Bước 7: báo cáo kiểm tra, tính trên đúng các giá trị được xuất ra file.
    # Cạnh thẳng có length == haversine nên chênh lệch kiểu 1e-9 m chỉ là sai số dấu phẩy động;
    # chỉ đếm là vi phạm khi length ngắn hơn haversine quá 1 mm.
    ratios, below = [], 0
    for e in edges:
        a, b = nodes[e["u"]], nodes[e["v"]]
        hav = haversine_m(a["lat"], a["lon"], b["lat"], b["lon"])
        if hav > 0:
            ratios.append(e["length_m"] / hav)
            below += e["length_m"] < hav - 1e-3
    c = min(1.0, min(ratios)) if ratios else 1.0
    pairs = Counter((e["u"], e["v"]) for e in edges)

    dataset_id = f"hcm-benthanh-r{half}-{raw_manifest['downloaded_at'][:10].replace('-', '')}"
    graph = {"format": "saigo-graph/1", "dataset_id": dataset_id, "crs": "EPSG:4326", "nodes": nodes, "edges": edges}
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / f"{dataset_id}.json"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(graph, f, ensure_ascii=False, separators=(",", ":"))

    report = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "oneway_edge_count": sum(1 for e in edges if e["oneway"]),
        "parallel_edge_count": sum(n - 1 for n in pairs.values() if n > 1),
        "self_loop_count": sum(1 for e in edges if e["u"] == e["v"]),
        "scc_node_count": len(scc),
        "nodes_outside_scc": len(nodes) - len(scc),
        "weak_components": nx.number_weakly_connected_components(H),
        "geometry_reversed": reversed_geom,
        "heuristic_c": c,
        "edges_length_below_haversine_1mm": below,
        "v_max_kmh": max(e["speed_kmh"] for e in edges),
        "highway": dict(Counter(e["highway"] for e in edges).most_common()),
    }
    manifest = {
        "format": "saigo-graph/1",
        "dataset_id": dataset_id,
        "file": out.relative_to(ROOT).as_posix(),
        "file_bytes": out.stat().st_size,
        "sha256": sha256(out),
        "raw": {k: raw_manifest[k] for k in ("dataset_id", "downloaded_at", "bbox", "network_type", "sha256")},
        "crop": {"area": area, "center": areas["center"], "half_side_m": half, "projected_crs": str(utm),
                 "rule": "giữ node trong hình vuông; giữ cạnh có cả hai đầu bên trong"},
        "simplification": {"simplify": raw_manifest["simplify"], "retain_all": raw_manifest["retain_all"]},
        **report,
        "speed_config": speeds,
        "dependencies": {"python": platform.python_version(), "osmnx": ox.__version__, "networkx": nx.__version__},
        "attribution": ATTRIBUTION,
    }
    (PROCESSED / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pct = 100 * report["oneway_edge_count"] / max(1, report["edge_count"])
    print(f"dataset {dataset_id}: vùng {area}, nửa cạnh {half} m")
    print(f"nodes={report['node_count']} edges={report['edge_count']} oneway={report['oneway_edge_count']} ({pct:.1f}%)")
    print(f"parallel_edges={report['parallel_edge_count']} self_loops={report['self_loop_count']} "
          f"weak_components={report['weak_components']}")
    print(f"SCC lớn nhất={report['scc_node_count']} node, ngoài SCC={report['nodes_outside_scc']} node")
    print(f"c={c!r} (cạnh có length < haversine quá 1 mm: {below}), "
          f"v_max={report['v_max_kmh']} km/h, hình học bị đảo={reversed_geom}")
    print(f"đã lưu {manifest['file']} ({manifest['file_bytes'] / 1e6:.1f} MB) + data/processed/manifest.json")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", choices=["download", "build"],
                    help="download: tải vùng tải và ghi manifest · build: xuất saigo-graph/1 cho một vùng")
    ap.add_argument("--smoke", action="store_true", help="tải vùng nhỏ quanh Bến Thành để kiểm tra OSMnx")
    ap.add_argument("--force", action="store_true", help="download: tải lại dù đã có dữ liệu thô")
    ap.add_argument("--area", default="demo", help="build: tên vùng trong data/config/areas.json (mặc định: demo)")
    a = ap.parse_args()
    # Windows: stdout bị chuyển hướng dùng cp1252, in tiếng Việt sẽ lỗi sau khi file đã ghi xong.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if a.smoke:
        smoke()
    elif a.command == "download":
        download(a.force)
    elif a.command == "build":
        build(a.area)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
