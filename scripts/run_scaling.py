"""E3 — tăng quy mô bản đồ, workload fixed trips (EXPERIMENT_PLAN mục 6; docs/tasks/T62-scaling.md).

Một lần chạy đo **cùng một** tập cặp trên mọi vùng cắt lồng nhau trong `crop_manifest.json`:

1. Kiểm sha256 từng vùng (S5).
2. Sinh cặp trong SCC của vùng **nhỏ nhất** bằng `generate_queries` của `run_benchmarks.py` (S1).
3. Mỗi vùng đánh số node lại từ đầu, nên đổi cặp sang id node của từng vùng qua `osmid` (S2).
4. Đo từng vùng bằng `run_benchmark` (quy trình mục 3.1), gộp vào một `measurements.csv` chung `run_id` (S3).
5. Đo thời gian nạp và bộ nhớ đỉnh khi nạp **riêng**, ghi `load.csv` (S4).
6. Kiểm bất biến: vùng lớn chứa mọi cạnh của vùng nhỏ, nên chi phí của một cặp không được tăng khi vùng lớn dần.

Ví dụ:
    python scripts/run_scaling.py --manifest data/processed/crop_manifest.json --pairs 250 --seed 42
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.graph.model import Graph, GraphMeta, load_graph  # noqa: E402
from app.graph.scenario import baseline_snapshot  # noqa: E402
from run_benchmarks import (  # noqa: E402
    MEASUREMENT_COLUMNS,
    QUERY_COLUMNS,
    _get_git_info,
    collect_env,
    generate_queries,
    run_benchmark,
)

SUITE = "scaling"
WORKLOAD = "fixed_trips"


def _rel(path: Path) -> Path:
    """Đường dẫn tương đối với gốc repo nếu nằm trong repo (giống run E2): file kết quả không mang đường dẫn máy."""
    try:
        return Path(path).resolve().relative_to(ROOT.resolve())
    except ValueError:
        return Path(path)


def _resolve(path_str: str, base: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (ROOT / p) if (ROOT / p).exists() else (base / p)


def load_sizes(manifest_path: Path) -> list[dict]:
    """Các vùng trong `crop_manifest.json`, sắp theo nửa cạnh tăng dần; file thiếu hoặc sai sha256 → ValueError."""
    manifest_path = Path(manifest_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    sizes = []
    for s in sorted(data["sizes"], key=lambda s: s["half_side_m"]):
        path = _resolve(s["file"], manifest_path.parent)
        if not path.is_file():
            raise ValueError(f"thiếu file vùng {s['dataset_id']}: {path} (chạy scripts/make_crops.py trước)")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != s["sha256"]:
            raise ValueError(f"{path.name}: sha256 {digest[:12]}… không khớp crop_manifest ({s['sha256'][:12]}…); "
                             "dựng lại bằng scripts/make_crops.py")
        sizes.append({"label": f"r{int(s['half_side_m'])}", "half_side_m": float(s["half_side_m"]),
                      "dataset_id": s["dataset_id"], "path": path, "sha256": digest})
    if len(sizes) < 2:
        raise ValueError("cần ít nhất 2 vùng trong crop_manifest để đo tăng quy mô")
    return sizes


def map_queries(queries: list[dict], src_meta: GraphMeta, dst_graph: Graph, dst_meta: GraphMeta) -> list[dict]:
    """Đổi cặp sinh trên vùng nhỏ sang id node của vùng `dst` qua `osmid` (S2).

    `osmid` không có, hoặc nằm ngoài SCC của vùng đích → ValueError: SCC lồng nhau bảo đảm điều này
    không xảy ra, nên gặp là dữ liệu sai, không được bỏ qua lặng lẽ.
    """
    index = {osm: i for i, osm in enumerate(dst_meta.node_osmid) if osm is not None}
    out = []
    for q in queries:
        mapped = dict(q)
        for end in ("source", "target"):
            osm = src_meta.node_osmid[q[end]]
            if osm is None:
                raise ValueError(f"query {q['query_id']}: node {q[end]} ({end}) của vùng nhỏ không có osmid")
            node = index.get(osm)
            if node is None:
                raise ValueError(f"query {q['query_id']}: osmid {osm} ({end}) không có trong {dst_graph.dataset_id}")
            if not dst_meta.node_in_scc[node]:
                raise ValueError(f"query {q['query_id']}: osmid {osm} ({end}) nằm ngoài SCC của {dst_graph.dataset_id}")
            mapped[end] = node
            mapped[f"{end}_osmid"] = osm
        out.append(mapped)
    return out


def measure_load(path: Path) -> tuple[float, float]:
    """(thời gian nạp ms, bộ nhớ đỉnh MB) — hai lần nạp riêng để tracemalloc không làm chậm số đo thời gian (S4)."""
    t0 = time.perf_counter_ns()
    load_graph(path)
    load_ms = (time.perf_counter_ns() - t0) / 1e6
    tracemalloc.start()
    try:
        load_graph(path)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return load_ms, peak / 2**20


def check_monotone(rows: list[dict], labels: list[str]) -> list[dict]:
    """Cặp có chi phí **tăng** khi sang vùng lớn hơn (theo thứ tự `labels`), hoặc mất đường. Rỗng là đạt."""
    cost: dict[tuple[str, str], dict[str, dict]] = {}
    for r in rows:
        cost.setdefault((str(r["query_id"]), r["algo"]), {})[r["size_label"]] = r
    bad = []
    for (qid, algo), by_size in sorted(cost.items()):
        present = [lb for lb in labels if lb in by_size]
        for small, big in zip(present, present[1:]):
            a, b = by_size[small], by_size[big]
            if a["status"] != "ok":
                continue
            if b["status"] != "ok":
                bad.append({"query_id": qid, "algo": algo, "from": small, "to": big, "reason": "mất đường"})
                continue
            ca, cb = float(a["cost_s"]), float(b["cost_s"])
            if cb > ca + 1e-6 * max(1.0, ca):
                bad.append({"query_id": qid, "algo": algo, "from": small, "to": big,
                            "reason": f"chi phí tăng {ca} → {cb}"})
    return bad


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    # Console Windows mặc định cp1252: in tiếng Việt sẽ lỗi và thoát mã 1 (review #108).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", type=Path, default=ROOT / "data" / "processed" / "crop_manifest.json")
    ap.add_argument("--pairs", type=int, default=250)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args(argv)

    try:
        sizes = load_sizes(args.manifest)
    except ValueError as err:
        sys.stderr.write(f"Lỗi: {err}\n")
        return 2

    # S1: sinh cặp trên vùng nhỏ nhất; L = cạnh hình vuông của vùng đó.
    smallest = sizes[0]
    g0, m0 = load_graph(smallest["path"])
    base_queries, sampling = generate_queries(g0, m0, args.pairs, args.seed, workload=WORKLOAD,
                                              l_box_m=2 * smallest["half_side_m"], l_source="crop_manifest")
    # S2: đổi cặp sang mọi vùng TRƯỚC khi ghi gì, để osmid sai không để lại run dở dang (review #109).
    try:
        with_osm = map_queries(base_queries, m0, g0, m0)
        per_size = []
        for size in sizes:
            graph, meta = load_graph(size["path"])
            per_size.append((size, graph, meta, map_queries(base_queries, m0, graph, meta)))
    except ValueError as err:
        sys.stderr.write(f"Lỗi: {err}\n")
        return 2

    commit, _, dirty = _get_git_info()
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M')}-{SUITE}-{commit[:7]}"
    run_dir = Path(args.out) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if dirty:
        sys.stderr.write("Cảnh báo: repo đang có thay đổi chưa commit, run sẽ ghi git_dirty = true (T62 S5)\n")
    _write_csv(run_dir / "queries.csv", QUERY_COLUMNS + ["source_osmid", "target_osmid"], with_osm)

    rows: list[dict] = []
    load_rows: list[dict] = []
    for size, graph, meta, mapped in per_size:
        # run_benchmark ghi queries.csv đúng cột của nó, nên bỏ cột osmid (đã ghi ở queries.csv chung của run).
        queries = [{k: v for k, v in q.items() if k in QUERY_COLUMNS} for q in mapped]
        sub = run_dir / "sizes" / size["label"]
        run_benchmark(graph, meta, baseline_snapshot(graph), queries, run_id, SUITE, size["label"], sub,
                      repeats=args.repeats, warmup=args.warmup, dataset_path=_rel(size["path"]),
                      cli_config={**vars(args), "manifest": _rel(args.manifest).as_posix(), "out": _rel(args.out).as_posix()},
                      sampling_info=sampling)
        with (sub / "measurements.csv").open(encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
        load_ms, peak_mb = measure_load(size["path"])
        load_rows.append({"size_label": size["label"], "dataset_id": size["dataset_id"],
                          "n_nodes": len(graph.node_lat), "n_edges": len(graph.edge_u),
                          "load_ms": round(load_ms, 2), "peak_mb": round(peak_mb, 2)})
        print(f"{size['label']}: {len(graph.node_lat)} node, {len(queries)} cặp, nạp {load_ms:.0f} ms, {peak_mb:.1f} MB")

    _write_csv(run_dir / "measurements.csv", MEASUREMENT_COLUMNS, rows)
    _write_csv(run_dir / "load.csv", ["size_label", "dataset_id", "n_nodes", "n_edges", "load_ms", "peak_mb"],
               load_rows)
    (run_dir / "env.json").write_text(json.dumps(collect_env(_rel(smallest["path"])), indent=2, ensure_ascii=False),
                                      encoding="utf-8", newline="\n")
    config = {"run_id": run_id, "suite": SUITE, "workload": WORKLOAD, "pairs": args.pairs, "seed": args.seed,
              "repeats": args.repeats, "warmup": args.warmup, "n_queries": len(base_queries),
              "sizes": [{k: (_rel(v).as_posix() if isinstance(v, Path) else v) for k, v in s.items()} for s in sizes],
              "sampling": sampling}
    (run_dir / "config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8",
                                         newline="\n")

    violations = check_monotone(rows, [s["label"] for s in sizes])
    if violations:
        _write_csv(run_dir / "violations.csv", ["query_id", "algo", "from", "to", "reason"], violations)
        sys.stderr.write(f"Lỗi: {len(violations)} cặp vi phạm bất biến chi phí (xem violations.csv)\n")
        return 1
    print(f"Xong: {run_dir} ({len(rows)} dòng đo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
