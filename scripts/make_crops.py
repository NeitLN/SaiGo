"""Cắt các hình vuông lồng nhau cho thí nghiệm tăng quy mô (T61; EXPERIMENT_PLAN mục 6, DATA_MODEL mục 8.4).

    python scripts/make_crops.py                          # 4 kích thước ứng viên + pilot ở kích thước lớn nhất
    python scripts/make_crops.py --sizes 1000 2000 4500   # chỉ các nửa cạnh đã chốt

Mọi kích thước cắt từ cùng một `outer.graphml` đã đóng băng (Release data-raw-20261024).
SCC chọn kiểu lồng nhau: SCC lớn nhất của vùng nhỏ nhất, rồi ở mỗi vùng lớn hơn lấy SCC chứa SCC trước,
nên cặp "fixed trips" lấy từ vùng nhỏ nhất tồn tại ở mọi kích thước.
Kết quả: data/processed/crop_r<nửa cạnh>_<ngày tải>.json (gitignored) và data/processed/crop_manifest.json (commit).
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))

from prepare_data import (  # noqa: E402
    ATTRIBUTION, CONFIG, PROCESSED, crop_nodes, export_graph, import_osmnx, load_frozen_raw,
)

CANDIDATES = [1000, 2000, 3000, 4500]  # nửa cạnh ứng viên, mét (EXPERIMENT_PLAN mục 6.1)
PILOT_LIMIT_S = 1.0                     # median Dijkstra > ~1 s/truy vấn thì giảm hoặc bỏ kích thước


def vn(n: int) -> str:
    """Số nguyên viết theo kiểu Việt Nam: 12.131."""
    return f"{n:,}".replace(",", ".")


def nested_sccs(G, crops: dict[int, list]) -> dict[int, set]:
    """SCC lồng nhau theo kích thước tăng dần; kiểm tra SCC nhỏ nằm trọn trong SCC lớn."""
    import networkx as nx

    out, prev = {}, None
    for half in sorted(crops):
        comps = list(nx.strongly_connected_components(G.subgraph(crops[half])))
        largest = max(comps, key=len)
        if prev is None:
            scc = largest
        else:
            seed = next(iter(prev))
            scc = next(c for c in comps if seed in c)
            if not prev <= scc:
                sys.exit(f"SCC của nửa cạnh {half} m không chứa SCC của kích thước nhỏ hơn")
            if len(scc) < len(largest):
                print(f"CẢNH BÁO: nửa cạnh {half} m: SCC lồng nhau ({len(scc)} node) không phải SCC lớn nhất "
                      f"của vùng ({len(largest)} node)")
        out[half] = scc
        prev = scc
    return out


def pilot(path: Path, n: int, seed: int) -> dict:
    """n truy vấn dài (cặp xa nhất trong 50·n cặp ngẫu nhiên thuộc SCC) chạy Dijkstra; đo median."""
    from app.algorithms.dijkstra import dijkstra
    from app.graph.geo import haversine_m
    from app.graph.model import load_graph
    from app.graph.scenario import baseline_snapshot

    graph, meta = load_graph(path)
    in_scc = [i for i, flag in enumerate(meta.node_in_scc) if flag]
    rng = random.Random(seed)
    cand = [tuple(rng.sample(in_scc, 2)) for _ in range(50 * n)]
    dist = {p: haversine_m(graph.node_lat[p[0]], graph.node_lon[p[0]], graph.node_lat[p[1]], graph.node_lon[p[1]])
            for p in cand}
    pairs = sorted(cand, key=lambda p: (-dist[p], p))[:n]

    snap = baseline_snapshot(graph)
    dijkstra(graph, snap, *pairs[0])  # warm-up, không tính
    times, expanded, no_path = [], [], 0
    for s, t in pairs:
        t0 = time.perf_counter()
        res = dijkstra(graph, snap, s, t)
        times.append(time.perf_counter() - t0)
        expanded.append(res.expanded)
        no_path += res.status != "ok"
    median_s = statistics.median(times)
    return {
        "queries": n, "seed": seed, "no_path": no_path,
        "haversine_m_min": round(min(dist[p] for p in pairs), 1),
        "median_s": median_s, "max_s": max(times),
        "median_expanded": statistics.median(expanded),
        "pass": median_s <= PILOT_LIMIT_S,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", type=int, nargs="+", default=CANDIDATES, help="nửa cạnh (m), mặc định 1000 2000 3000 4500")
    ap.add_argument("--pilot", type=int, default=20, help="số truy vấn pilot ở kích thước lớn nhất (0 = bỏ qua)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    ox = import_osmnx()
    import networkx as nx

    raw_manifest, G = load_frozen_raw()
    areas = json.loads((CONFIG / "areas.json").read_text(encoding="utf-8"))
    speeds = json.loads((CONFIG / "speeds.json").read_text(encoding="utf-8"))
    max_half = areas["download"]["half_side_m"]
    if max(a.sizes) > max_half:
        sys.exit(f"nửa cạnh lớn nhất là {max_half} m (vùng tải không tính đệm)")

    crops, utm = {}, None
    for half in sorted(set(a.sizes)):
        crops[half], utm = crop_nodes(G, areas["center"], half)
    sccs = nested_sccs(G, crops)

    date = raw_manifest["downloaded_at"][:10].replace("-", "")
    sizes = []
    for half in sorted(crops):
        dataset_id = f"crop_r{half}_{date}"
        report = export_graph(G.subgraph(crops[half]).copy(), sccs[half], dataset_id, speeds)
        sizes.append({"half_side_m": half, "dataset_id": dataset_id, **report})
        print(f"nửa cạnh {half} m: |V|={report['node_count']} |E|={report['edge_count']} "
              f"SCC={report['scc_node_count']} → {report['file']}")

    largest = sizes[-1]
    pilot_result = None
    if a.pilot:
        pilot_result = pilot(ROOT / largest["file"], a.pilot, a.seed)
        verdict = "đạt" if pilot_result["pass"] else f"KHÔNG đạt (> {PILOT_LIMIT_S} s), cần giảm hoặc bỏ kích thước này"
        print(f"pilot nửa cạnh {largest['half_side_m']} m: {a.pilot} truy vấn dài (≥ {pilot_result['haversine_m_min']:.0f} m), "
              f"median Dijkstra {pilot_result['median_s'] * 1000:.1f} ms, max {pilot_result['max_s'] * 1000:.1f} ms, "
              f"median expanded {pilot_result['median_expanded']:.0f} → {verdict}")

    manifest = {
        "raw": {k: raw_manifest[k] for k in ("dataset_id", "downloaded_at", "bbox", "network_type", "sha256")},
        "snapshot_date": date,
        "center": areas["center"],
        "projected_crs": utm,
        "crop_rule": "giữ node trong hình vuông (mét trên UTM); giữ cạnh có cả hai đầu bên trong",
        "scc_rule": "lồng nhau: SCC lớn nhất của vùng nhỏ nhất; mỗi vùng lớn hơn lấy SCC chứa SCC trước",
        "nested_scc_checked": True,
        "sizes": sizes,
        # Chỉ ghi phần không đổi giữa các lần chạy; thời gian đo nằm ở crop_pilot.json (không commit).
        "pilot": {"half_side_m": largest["half_side_m"], "algorithm": "dijkstra", "limit_s": PILOT_LIMIT_S,
                  **{k: pilot_result[k] for k in ("queries", "seed", "no_path", "haversine_m_min", "median_expanded")}}
        if pilot_result else None,
        "speed_config": speeds,
        "dependencies": {"python": platform.python_version(), "osmnx": ox.__version__, "networkx": nx.__version__},
        "attribution": ATTRIBUTION,
    }
    out = PROCESSED / "crop_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if pilot_result:
        timing = {"half_side_m": largest["half_side_m"], "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                  "python": platform.python_version(), "machine": platform.node(), **pilot_result}
        (PROCESSED / "crop_pilot.json").write_text(json.dumps(timing, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8")

    print("\n| Nửa cạnh | `dataset_id` | \\|V\\| | \\|E\\| | SCC (node) | Cạnh một chiều | sha256 |")
    print("|---:|---|---:|---:|---:|---:|---|")
    for s in sizes:
        km = f"{s['half_side_m'] / 1000:g}".replace(".", ",")
        print(f"| {km} km | `{s['dataset_id']}` | {vn(s['node_count'])} | {vn(s['edge_count'])} | "
              f"{vn(s['scc_node_count'])} | {vn(s['oneway_edge_count'])} | `{s['sha256'][:12]}…` |")
    print(f"\nđã ghi {out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
