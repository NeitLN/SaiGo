"""Bộ chạy benchmark offline, xuất CSV/JSON vào results/ (docs/EXPERIMENT_PLAN.md mục 2, 3).

Đo thời gian chạy độc lập của Dijkstra và A* bằng time.perf_counter_ns quanh lời gọi hàm,
hỗ trợ phân tầng (ngắn, trung bình, dài), warm-up, đổi thứ tự thuật toán và xuất đủ
các tệp queries.csv, measurements.csv, env.json, config.json.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import gc
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Đảm bảo import được backend từ thư mục gốc repo
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.algorithms.astar import astar
from app.algorithms.dijkstra import dijkstra
from app.algorithms.heuristics import make_geo_heuristic
from app.graph.closures import validate_blocked
from app.graph.geo import haversine_m
from app.graph.model import Graph, GraphMeta, load_graph
from app.graph.scenario import Snapshot, build_snapshot, load_scenarios

# 27 cột chuẩn của measurements.csv theo docs/EXPERIMENT_PLAN.md mục 3.3
MEASUREMENT_COLUMNS = [
    "run_id",
    "suite",
    "dataset_id",
    "size_label",
    "n_nodes",
    "n_edges",
    "query_id",
    "workload",
    "stratum",
    "source",
    "target",
    "hav_m",
    "algo",
    "scenario_id",
    "blocked_count",
    "status",
    "cost_s",
    "distance_m",
    "expanded",
    "unique_expanded",
    "reopened",
    "relaxations",
    "pushes",
    "max_frontier",
    "runtime_ns_median",
    "runtime_ns_min",
    "repeats",
]

# Cột của queries.csv theo docs/EXPERIMENT_PLAN.md mục 2.1
QUERY_COLUMNS = [
    "query_id",
    "workload",
    "stratum",
    "source",
    "target",
    "hav_m",
    "delta",
]


def _get_ram_bytes() -> int | None:
    """Lấy tổng dung lượng RAM vật lý theo byte mà không cần thư viện bên ngoài."""
    if sys.platform == "win32":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return int(stat.ullTotalPhys)
        except Exception:
            return None
    elif hasattr(os, "sysconf"):
        try:
            return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
        except Exception:
            return None
    return None


def _get_git_info() -> tuple[str, str, bool]:
    """Lấy commit hash rút gọn, tên nhánh hiện tại và trạng thái git dirty."""
    commit, branch, dirty = "unknown", "unknown", False
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        # Bỏ qua results/: chính lần chạy này đã tạo results/<run_id>/ trước khi ghi env.json,
        # nên nếu tính thư mục đó thì mọi lần đo trên code sạch đều bị ghi là dirty.
        status_out = subprocess.check_output(
            ["git", "status", "--porcelain", "--", ".", ":(exclude)results"],
            cwd=str(REPO_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = bool(status_out)
    except Exception:
        pass
    return commit, branch, dirty


def collect_env(dataset_path: Path | None = None) -> dict:
    """Ghi nhận môi trường máy đo theo EXPERIMENT_PLAN mục 3.1 bước 9."""
    ram_bytes = _get_ram_bytes()
    dataset_sha256 = ""
    if dataset_path and Path(dataset_path).is_file():
        dataset_sha256 = hashlib.sha256(Path(dataset_path).read_bytes()).hexdigest()

    packages: dict[str, str] = {}
    for pkg in ("pytest", "networkx", "fastapi", "pydantic", "httpx", "starlette"):
        try:
            packages[pkg] = importlib.metadata.version(pkg)
        except Exception:
            pass

    commit, branch, dirty = _get_git_info()

    return {
        "timestamp": datetime.now().isoformat(),
        "platform": platform.platform(),
        "os": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "ram_total_bytes": ram_bytes,
        "ram_total_gb": round(ram_bytes / (1024**3), 2) if ram_bytes else None,
        "git_commit": commit,
        "git_branch": branch,
        "git_dirty": dirty,
        "dataset_path": str(dataset_path) if dataset_path else "",
        "dataset_sha256": dataset_sha256,
        "packages": packages,
    }


def compute_bounding_box_l(graph: Graph) -> float:
    """Tính cạnh hình vuông L (mét) từ bounding box của các node trong đồ thị (bỏ kẹp 1000m)."""
    lat_min, lat_max = min(graph.node_lat), max(graph.node_lat)
    lon_min, lon_max = min(graph.node_lon), max(graph.node_lon)
    mid_lat = (lat_min + lat_max) / 2.0
    h_m = haversine_m(lat_min, lon_min, lat_max, lon_min)
    w_m = haversine_m(mid_lat, lon_min, mid_lat, lon_max)
    l_box = max(h_m, w_m)
    return float(l_box) if l_box > 0 else 1.0


def resolve_side_m(graph_path: Path, graph: Graph, side_m: float | None = None) -> tuple[float, str]:
    """Xác định L (cạnh hình vuông của vùng) theo thứ tự:
    1. Tham số dòng lệnh --side-m
    2. Đọc crop.half_side_m * 2 từ manifest.json cùng thư mục file đồ thị (nếu dataset_id khớp)
    3. Bounding box của đồ thị (L_source = 'bbox').
    """
    if side_m is not None:
        if side_m <= 0:
            raise ValueError(f"side_m phải dương, nhận {side_m}")
        return float(side_m), "side_m"

    manifest_path = graph_path.parent / "manifest.json"
    if manifest_path.is_file():
        try:
            mdata = json.loads(manifest_path.read_text(encoding="utf-8"))
            half_side = None
            if mdata.get("dataset_id") == graph.dataset_id:
                crop = mdata.get("crop")
                if isinstance(crop, dict) and "half_side_m" in crop:
                    half_side = float(crop["half_side_m"])
            elif "datasets" in mdata and isinstance(mdata["datasets"], dict):
                d_entry = mdata["datasets"].get(graph.dataset_id, {})
                crop = d_entry.get("crop") if isinstance(d_entry, dict) else None
                if isinstance(crop, dict) and "half_side_m" in crop:
                    half_side = float(crop["half_side_m"])
            elif "crops" in mdata and isinstance(mdata["crops"], dict):
                d_entry = mdata["crops"].get(graph.dataset_id, {})
                crop = d_entry.get("crop") if isinstance(d_entry, dict) else d_entry
                if isinstance(crop, dict) and "half_side_m" in crop:
                    half_side = float(crop["half_side_m"])

            if half_side is not None and half_side > 0:
                return float(half_side * 2.0), "manifest"
        except Exception:
            pass

    return compute_bounding_box_l(graph), "bbox"


def generate_queries(
    graph: Graph,
    meta: GraphMeta,
    n_pairs: int,
    seed: int,
    workload: str = "demo",
    l_box_m: float | None = None,
    l_source: str = "bbox",
) -> tuple[list[dict], dict]:
    """Sinh tập cặp truy vấn có seed và phân tầng theo EXPERIMENT_PLAN mục 2.1."""
    rng = random.Random(seed)
    n = len(graph.node_lat)
    if n < 2:
        raise ValueError(f"đồ thị cần ít nhất 2 node để sinh cặp truy vấn, nhận {n}")

    # Lấy các node thuộc SCC (nếu có trường node_in_scc)
    candidate_nodes = [i for i in range(n) if meta.node_in_scc[i]]
    if len(candidate_nodes) < 2:
        candidate_nodes = list(range(n))

    l_val = l_box_m if l_box_m is not None else compute_bounding_box_l(graph)

    # 3 tầng: ngắn (delta < 0.2), trung bình (0.2 <= delta < 0.5), dài (delta >= 0.5)
    target_per_stratum = max(1, n_pairs // 3)
    counts = {"ngan": 0, "trung_binh": 0, "dai": 0}
    queries: list[dict] = []

    rejected_same_node = 0
    rejected_stratum_full = 0
    fallback_used = False

    # 1. Thử lấy mẫu loại bỏ (rejection sampling) để cân bằng 3 tầng
    max_attempts = max(3000, n_pairs * 100)
    attempts = 0
    while len(queries) < n_pairs and attempts < max_attempts:
        attempts += 1
        s = rng.choice(candidate_nodes)
        t = rng.choice(candidate_nodes)
        if s == t:
            rejected_same_node += 1
            continue
        hav = haversine_m(graph.node_lat[s], graph.node_lon[s], graph.node_lat[t], graph.node_lon[t])
        delta = hav / l_val
        strat = "ngan" if delta < 0.2 else ("trung_binh" if delta < 0.5 else "dai")

        if counts[strat] < target_per_stratum or (len(queries) >= target_per_stratum * 3):
            counts[strat] += 1
            queries.append({
                "query_id": len(queries),
                "workload": workload,
                "stratum": strat,
                "source": s,
                "target": t,
                "hav_m": round(hav, 2),
                "delta": round(delta, 4),
            })
        else:
            rejected_stratum_full += 1

    # 2. Dự phòng nếu đồ thị nhỏ không tồn tại một số tầng (như mini.json thiếu delta < 0.2)
    if len(queries) < n_pairs:
        fallback_used = True
        while len(queries) < n_pairs:
            s = rng.choice(candidate_nodes)
            t = rng.choice(candidate_nodes)
            if s == t:
                rejected_same_node += 1
                continue
            hav = haversine_m(graph.node_lat[s], graph.node_lon[s], graph.node_lat[t], graph.node_lon[t])
            delta = hav / l_val
            strat = "ngan" if delta < 0.2 else ("trung_binh" if delta < 0.5 else "dai")
            counts[strat] += 1
            queries.append({
                "query_id": len(queries),
                "workload": workload,
                "stratum": strat,
                "source": s,
                "target": t,
                "hav_m": round(hav, 2),
                "delta": round(delta, 4),
            })

        sys.stderr.write(
            f"Cảnh báo: không đủ cặp phân tầng theo rejection sampling (fallback_used=True, L_m={l_val:.1f}). "
            f"Số cặp thực tế: {counts}\n"
        )

    # Thống kê delta phân bố thực tế của từng tầng
    strata_stats = {}
    for strat in ("ngan", "trung_binh", "dai"):
        deltas = [q["delta"] for q in queries if q["stratum"] == strat]
        strata_stats[strat] = {
            "count": len(deltas),
            "delta_min": min(deltas) if deltas else None,
            "delta_median": round(statistics.median(deltas), 4) if deltas else None,
            "delta_max": max(deltas) if deltas else None,
        }

    sampling_info = {
        "L_m": round(l_val, 2),
        "L_source": l_source,
        "target_per_stratum": {
            "ngan": target_per_stratum,
            "trung_binh": target_per_stratum,
            "dai": target_per_stratum,
        },
        "actual_per_stratum": counts,
        "rejected": {
            "same_node": rejected_same_node,
            "stratum_full": rejected_stratum_full,
        },
        "fallback_used": fallback_used,
        "strata_stats": strata_stats,
    }

    return queries, sampling_info


def write_queries_csv(path: Path, queries: list[dict]) -> None:
    """Ghi queries.csv trước khi đo lường (docs/EXPERIMENT_PLAN.md mục 2.1)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=QUERY_COLUMNS)
        writer.writeheader()
        for q in queries:
            writer.writerow(q)


def read_queries_csv(path: Path) -> list[dict]:
    """Đọc queries.csv đã lưu từ trước để chạy lại cùng tập cặp."""
    queries = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append({
                "query_id": int(row["query_id"]),
                "workload": row["workload"],
                "stratum": row["stratum"],
                "source": int(row["source"]),
                "target": int(row["target"]),
                "hav_m": float(row["hav_m"]),
                "delta": float(row["delta"]),
            })
    return queries


def run_benchmark(
    graph: Graph,
    meta: GraphMeta,
    snap: Snapshot,
    queries: list[dict],
    run_id: str,
    suite: str,
    size_label: str,
    out_dir: Path,
    repeats: int = 5,
    warmup: int = 20,
    dataset_path: Path | None = None,
    cli_config: dict | None = None,
    sampling_info: dict | None = None,
) -> dict:
    """Thực hiện quy trình đo lường benchmark theo EXPERIMENT_PLAN mục 3.1."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Lưu queries.csv TRƯỚC KHI đo (mục 2.1)
    queries_file = out_dir / "queries.csv"
    write_queries_csv(queries_file, queries)

    # 2. Warm-up (mục 3.1 bước 3)
    n_warmup = min(warmup, len(queries))
    for i in range(n_warmup):
        wq = queries[i]
        ws, wt = wq["source"], wq["target"]
        dijkstra(graph, snap, ws, wt, trace_limit=0)
        h = make_geo_heuristic(graph, wt)
        astar(graph, snap, ws, wt, h, trace_limit=0)

    # 3. Đo lường chính thức từng cặp
    measurements: list[dict] = []
    n_nodes = len(graph.node_lat)
    n_edges = len(graph.edge_u)
    blocked_count = len(snap.blocked)

    for q_idx, q in enumerate(queries):
        source = q["source"]
        target = q["target"]
        hav_m = q["hav_m"]
        workload = q["workload"]
        stratum = q["stratum"]
        query_id = q["query_id"]

        times_d: list[int] = []
        times_a: list[int] = []
        last_res_d = None
        last_res_a = None

        gc.collect()
        gc.disable()
        try:
            # Cặp chẵn chạy Dijkstra trước rồi A*, cặp lẻ chạy A* trước rồi Dijkstra (mục 3.1 bước 4)
            if q_idx % 2 == 0:
                for _ in range(repeats):
                    t0 = time.perf_counter_ns()
                    last_res_d = dijkstra(graph, snap, source, target, trace_limit=0)
                    t1 = time.perf_counter_ns()
                    times_d.append(t1 - t0)

                for _ in range(repeats):
                    t0 = time.perf_counter_ns()
                    h = make_geo_heuristic(graph, target)
                    last_res_a = astar(graph, snap, source, target, h, trace_limit=0)
                    t1 = time.perf_counter_ns()
                    times_a.append(t1 - t0)
            else:
                for _ in range(repeats):
                    t0 = time.perf_counter_ns()
                    h = make_geo_heuristic(graph, target)
                    last_res_a = astar(graph, snap, source, target, h, trace_limit=0)
                    t1 = time.perf_counter_ns()
                    times_a.append(t1 - t0)

                for _ in range(repeats):
                    t0 = time.perf_counter_ns()
                    last_res_d = dijkstra(graph, snap, source, target, trace_limit=0)
                    t1 = time.perf_counter_ns()
                    times_d.append(t1 - t0)
        finally:
            gc.enable()

        assert last_res_d is not None and last_res_a is not None

        # Kiểm tra tính đúng đắn nghiêm ngặt giữa Dijkstra và A* (mục 3.2: 100% khớp chi phí)
        if last_res_d.status != last_res_a.status:
            raise RuntimeError(
                f"Lỗi không khớp trạng thái tại query {query_id} ({source} -> {target}): "
                f"Dijkstra={last_res_d.status}, A*={last_res_a.status}"
            )
        if last_res_d.status == "ok":
            cost_d = last_res_d.cost_s
            cost_a = last_res_a.cost_s
            tol = 1e-6 * max(1.0, cost_d)
            if abs(cost_a - cost_d) > tol:
                raise RuntimeError(
                    f"Lỗi lệch chi phí tại query {query_id} ({source} -> {target}): "
                    f"Dijkstra={cost_d}, A*={cost_a}, tol={tol}"
                )

        # Tính median và min theo EXPERIMENT_PLAN mục 3.1 bước 7
        median_d = int(statistics.median(times_d))
        min_d = min(times_d)
        median_a = int(statistics.median(times_a))
        min_a = min(times_a)

        # Hàng đo cho Dijkstra
        measurements.append({
            "run_id": run_id,
            "suite": suite,
            "dataset_id": graph.dataset_id,
            "size_label": size_label,
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "query_id": query_id,
            "workload": workload,
            "stratum": stratum,
            "source": source,
            "target": target,
            "hav_m": hav_m,
            "algo": "dijkstra",
            "scenario_id": snap.scenario_id,
            "blocked_count": blocked_count,
            "status": last_res_d.status,
            "cost_s": round(last_res_d.cost_s, 6) if last_res_d.cost_s is not None else "",
            "distance_m": round(last_res_d.distance_m, 2) if last_res_d.distance_m is not None else "",
            "expanded": last_res_d.expanded,
            "unique_expanded": last_res_d.unique_expanded,
            "reopened": last_res_d.reopened,
            "relaxations": last_res_d.relaxations,
            "pushes": last_res_d.pushes,
            "max_frontier": last_res_d.max_frontier,
            "runtime_ns_median": median_d,
            "runtime_ns_min": min_d,
            "repeats": repeats,
        })

        # Hàng đo cho A*
        measurements.append({
            "run_id": run_id,
            "suite": suite,
            "dataset_id": graph.dataset_id,
            "size_label": size_label,
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "query_id": query_id,
            "workload": workload,
            "stratum": stratum,
            "source": source,
            "target": target,
            "hav_m": hav_m,
            "algo": "astar",
            "scenario_id": snap.scenario_id,
            "blocked_count": blocked_count,
            "status": last_res_a.status,
            "cost_s": round(last_res_a.cost_s, 6) if last_res_a.cost_s is not None else "",
            "distance_m": round(last_res_a.distance_m, 2) if last_res_a.distance_m is not None else "",
            "expanded": last_res_a.expanded,
            "unique_expanded": last_res_a.unique_expanded,
            "reopened": last_res_a.reopened,
            "relaxations": last_res_a.relaxations,
            "pushes": last_res_a.pushes,
            "max_frontier": last_res_a.max_frontier,
            "runtime_ns_median": median_a,
            "runtime_ns_min": min_a,
            "repeats": repeats,
        })

    # 4. Ghi measurements.csv
    meas_file = out_dir / "measurements.csv"
    with meas_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MEASUREMENT_COLUMNS)
        writer.writeheader()
        for row in measurements:
            writer.writerow(row)

    # 5. Ghi env.json
    env_file = out_dir / "env.json"
    env_data = collect_env(dataset_path)
    env_file.write_text(json.dumps(env_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # 6. Ghi config.json
    cfg = cli_config or {}
    config_file = out_dir / "config.json"
    config_data = {
        "run_id": run_id,
        "suite": suite,
        "size_label": size_label,
        "repeats": repeats,
        "warmup": warmup,
        "n_queries": len(queries),
        "cli_args": cfg,
        "sampling": sampling_info or {},
    }
    config_file.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "run_id": run_id,
        "out_dir": str(out_dir),
        "n_queries": len(queries),
        "n_measurements": len(measurements),
        "cost_match_rate": 1.0,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chạy bộ benchmark đo hiệu năng Dijkstra và A*")
    parser.add_argument("--suite", default="demo", choices=["demo", "scaling", "scenario", "test"],
                        help="Tên bộ benchmark (mặc định: demo)")
    parser.add_argument("--graph", type=Path, default=Path("tests/fixtures/mini.json"),
                        help="Đường dẫn file đồ thị json (mặc định: tests/fixtures/mini.json)")
    parser.add_argument("--pairs", type=int, default=20,
                        help="Số lượng cặp truy vấn cần đo (mặc định: 20)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Seed ngẫu nhiên sinh cặp (mặc định: 42)")
    parser.add_argument("--repeats", type=int, default=5,
                        help="Số lần lặp mỗi thuật toán trên mỗi cặp (mặc định: 5)")
    parser.add_argument("--warmup", type=int, default=20,
                        help="Số truy vấn chạy warm-up (mặc định: 20)")
    parser.add_argument("--workload", default="demo",
                        help="Nhãn workload (mặc định: demo)")
    parser.add_argument("--size-label", default="",
                        help="Nhãn kích thước (mặc định: dataset_id)")
    parser.add_argument("--side-m", type=float, default=None,
                        help="Cạnh hình vuông L (mét) của vùng cắt (mặc định: đọc manifest hoặc bbox)")
    parser.add_argument("--run-id", default=None,
                        help="Ép run_id cụ thể (mặc định: YYYYMMDD-HHMM-<suite>-<git7>)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Thư mục cha ghi kết quả (mặc định: results/)")
    parser.add_argument("--queries", type=Path, default=None,
                        help="Đường dẫn queries.csv có sẵn để tái lập")
    parser.add_argument("--scenario", default="baseline",
                        help="Mã kịch bản snapshot (mặc định: baseline)")
    parser.add_argument("--scenario-file", type=Path, default=Path("data/config/scenarios.json"),
                        help="File scenarios.json kịch bản ùn tắc (mặc định: data/config/scenarios.json)")
    parser.add_argument("--blocked", type=int, nargs="*", default=[],
                        help="Danh sách id cạnh bị đóng")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    args = parse_args(argv)

    # 1. Nạp đồ thị
    graph_path = args.graph
    if not graph_path.is_absolute():
        if not graph_path.exists() and (REPO_ROOT / graph_path).exists():
            graph_path = REPO_ROOT / graph_path
    if not graph_path.is_file():
        sys.stderr.write(f"Lỗi: không tìm thấy file đồ thị {graph_path}\n")
        return 1

    graph, meta = load_graph(graph_path)

    # 2. Xây snapshot từ load_scenarios và build_snapshot (Review mục 1)
    scenario_file = args.scenario_file
    if not scenario_file.is_absolute():
        if not scenario_file.exists() and (REPO_ROOT / scenario_file).exists():
            scenario_file = REPO_ROOT / scenario_file
    if not scenario_file.is_file():
        sys.stderr.write(f"Lỗi: không tìm thấy file kịch bản {scenario_file}\n")
        return 1

    try:
        scenarios = load_scenarios(scenario_file)
    except Exception as err:
        sys.stderr.write(f"Lỗi khi đọc file kịch bản {scenario_file}: {err}\n")
        return 1

    if args.scenario not in scenarios:
        sys.stderr.write(f"Lỗi: kịch bản {args.scenario!r} không có trong {scenario_file}\n")
        return 1

    try:
        blocked_set = validate_blocked(graph, args.blocked)
    except ValueError as err:
        sys.stderr.write(f"Lỗi: danh sách blocked không hợp lệ: {err}\n")
        return 1

    snap = build_snapshot(graph, meta, scenarios[args.scenario], blocked=blocked_set)

    # 3. Chuẩn bị định danh run_id và thư mục xuất kết quả (Review mục 2)
    commit, _, _ = _get_git_info()
    if args.run_id:
        run_id = args.run_id
    else:
        now_str = datetime.now().strftime("%Y%m%d-%H%M")
        run_id = f"{now_str}-{args.suite}-{commit[:7]}"

    out_base = args.out if args.out is not None else (REPO_ROOT / "results")
    out_dir = Path(out_base) / run_id

    size_label = args.size_label or graph.dataset_id

    # 4. Xác định L_m và L_source (Review mục 4)
    l_val, l_source = resolve_side_m(graph_path, graph, args.side_m)

    # 5. Sinh hoặc nạp cặp truy vấn (Review mục 3)
    if args.queries:
        q_path = args.queries
        if not q_path.is_absolute() and not q_path.exists() and (REPO_ROOT / q_path).exists():
            q_path = REPO_ROOT / q_path
        queries = read_queries_csv(q_path)
        sampling_info = {
            "source": "reused_queries_file",
            "file": str(q_path),
            "count": len(queries),
            "L_m": round(l_val, 2),
            "L_source": l_source,
        }
    else:
        queries, sampling_info = generate_queries(
            graph=graph,
            meta=meta,
            n_pairs=args.pairs,
            seed=args.seed,
            workload=args.workload,
            l_box_m=l_val,
            l_source=l_source,
        )

    # 6. Chạy đo lường
    cli_cfg = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    res = run_benchmark(
        graph=graph,
        meta=meta,
        snap=snap,
        queries=queries,
        run_id=run_id,
        suite=args.suite,
        size_label=size_label,
        out_dir=out_dir,
        repeats=args.repeats,
        warmup=args.warmup,
        dataset_path=graph_path,
        cli_config=cli_cfg,
        sampling_info=sampling_info,
    )

    print(f"Đã hoàn thành benchmark: {run_id}")
    print(f"- Đồ thị: {graph.dataset_id} (|V|={len(graph.node_lat)}, |E|={len(graph.edge_u)})")
    print(f"- Số cặp đo: {res['n_queries']} (khớp chi phí: {res['cost_match_rate'] * 100:.1f}%)")
    print(f"- Thư mục kết quả: {res['out_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
