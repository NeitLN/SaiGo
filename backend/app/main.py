"""Khởi tạo ứng dụng FastAPI và nạp đồ thị lúc khởi động (docs/ARCHITECTURE.md mục 4.1)."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI

from app.algorithms.heuristics import geo_scale
from app.api.routes import router
from app.graph.closures import reverse_twins
from app.graph.model import load_graph
from app.graph.scenario import load_scenarios

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _repo_path(raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute() and (REPO_ROOT / p).is_file():
        return REPO_ROOT / p
    return p


def get_graph_path() -> Path:
    """Lấy đường dẫn file đồ thị từ biến môi trường SAIGO_GRAPH hoặc mặc định tests/fixtures/mini.json."""
    return _repo_path(os.environ.get("SAIGO_GRAPH", "tests/fixtures/mini.json"))


def get_scenarios_path() -> Path:
    """File kịch bản `saigo-scenarios/1` từ SAIGO_SCENARIOS, mặc định data/config/scenarios.json."""
    return _repo_path(os.environ.get("SAIGO_SCENARIOS", "data/config/scenarios.json"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan nạp đồ thị khi server khởi động; lỗi nạp file sẽ dừng server (fail-fast)."""
    path = get_graph_path()
    if not path.is_file():
        raise RuntimeError(f"Không tìm thấy file đồ thị tại: {path}")

    try:
        graph, meta = load_graph(path)
    except Exception as err:
        raise RuntimeError(f"Lỗi khi nạp file đồ thị tại {path}: {err}") from err

    try:
        scenarios = load_scenarios(get_scenarios_path())
    except Exception as err:
        raise RuntimeError(f"Lỗi khi nạp file kịch bản tại {get_scenarios_path()}: {err}") from err

    # Tính một lần lúc khởi động, không để rơi vào request đầu tiên (review #67, #73):
    # geo_scale duyệt mọi cạnh (có cache), reverse_twins dùng cho "đóng đoạn" hai chiều.
    geo_scale(graph)
    app.state.twins = reverse_twins(graph, meta)

    app.state.graph = graph
    app.state.meta = meta
    app.state.scenarios = scenarios
    app.state.dataset_id = graph.dataset_id
    app.state.dataset_loaded = True

    yield


app = FastAPI(title="SaiGo API", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api")
