"""Định tuyến các endpoint API của SaiGo (docs/ARCHITECTURE.md mục 4)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import DatasetResponse, HealthResponse, RouteRequest, RouteResponse
from app.graph.model import Graph, GraphMeta
from app.services.routing import RouteInputError, route

router = APIRouter()


def _loaded(request: Request) -> tuple[Graph, GraphMeta]:
    graph: Graph | None = getattr(request.app.state, "graph", None)
    meta: GraphMeta | None = getattr(request.app.state, "meta", None)
    if graph is None or meta is None:
        raise HTTPException(
            status_code=503,
            detail="Chưa nạp đồ thị (dataset not loaded)",
        )
    return graph, meta


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Kiểm tra trạng thái server và đồ thị đã nạp."""
    dataset_loaded = getattr(request.app.state, "dataset_loaded", False)
    dataset_id = getattr(request.app.state, "dataset_id", None)
    return HealthResponse(
        status="ok",
        dataset_loaded=dataset_loaded,
        dataset_id=dataset_id,
    )


@router.get("/dataset", response_model=DatasetResponse)
def dataset(request: Request) -> DatasetResponse:
    """Đồ thị đang nạp và các kịch bản ùn tắc dùng được (cùng cấu trúc file `saigo-scenarios/1`)."""
    graph, _ = _loaded(request)
    scenarios = [
        {"id": s.id, "label": s.label,
         "rules": [{"zone": {"type": r.zone.type, "lat": r.zone.lat, "lon": r.zone.lon, "radius_m": r.zone.radius_m},
                    "alpha": r.alpha, "highway": list(r.highway) if r.highway is not None else None}
                   for r in s.rules]}
        for s in request.app.state.scenarios.values()
    ]
    return DatasetResponse(dataset_id=graph.dataset_id, node_count=len(graph.node_lat),
                           edge_count=len(graph.edge_u), scenarios=scenarios)


@router.post("/route", response_model=RouteResponse)
def compute_route(req: RouteRequest, request: Request) -> RouteResponse:
    """Tìm đường giữa hai điểm theo kịch bản và danh sách cạnh đóng (contract v1 + phần thêm ở T51)."""
    graph, meta = _loaded(request)
    try:
        return route(graph, meta, req, request.app.state.scenarios, request.app.state.twins)
    except RouteInputError as err:
        raise HTTPException(status_code=422, detail=str(err)) from None
