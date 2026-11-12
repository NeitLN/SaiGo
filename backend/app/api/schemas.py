"""Định nghĩa schema Pydantic cho request và response của API (docs/ARCHITECTURE.md mục 4.1)."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, StrictInt, field_validator


class HealthResponse(BaseModel):
    """Thông tin trạng thái server và dataset đang nạp."""

    status: str = "ok"
    dataset_loaded: bool
    dataset_id: str | None = None


class LatLon(BaseModel):
    """Tọa độ địa lý vĩ độ (lat) và kinh độ (lon)."""

    lat: float = Field(..., description="Vĩ độ trong khoảng [-90, 90]")
    lon: float = Field(..., description="Kinh độ trong khoảng [-180, 180]")

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)):
            raise ValueError("vĩ độ phải là số thực hữu hạn")
        if not (-90.0 <= v <= 90.0):
            raise ValueError("vĩ độ phải nằm trong khoảng [-90, 90]")
        return float(v)

    @field_validator("lon")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if not (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)):
            raise ValueError("kinh độ phải là số thực hữu hạn")
        if not (-180.0 <= v <= 180.0):
            raise ValueError("kinh độ phải nằm trong khoảng [-180, 180]")
        return float(v)


class RouteRequest(BaseModel):
    """Yêu cầu tìm đường giữa hai điểm theo contract v1."""

    source: LatLon
    target: LatLon
    algorithms: list[str] = Field(default_factory=lambda: ["dijkstra"])
    scenario_id: str | None = "baseline"
    blocked_edge_ids: list[StrictInt] = Field(default_factory=list)   # StrictInt: không nhận true/false là id 1/0
    trace_limit: int = Field(0, ge=0, le=5000)

    @field_validator("algorithms")
    @classmethod
    def validate_algorithms(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("danh sách thuật toán không được rỗng")
        allowed = {"dijkstra", "astar"}
        for algo in v:
            if algo not in allowed:
                raise ValueError(f"thuật toán không hỗ trợ: {algo!r}, chỉ hỗ trợ 'dijkstra', 'astar'")
        return v


class SnappedPoint(BaseModel):
    """Thông tin node sau khi snap từ tọa độ người dùng."""

    node_id: int
    lat: float
    lon: float
    snap_distance_m: float


class SnappedResponse(BaseModel):
    """Các điểm snap nguồn và đích."""

    source: SnappedPoint
    target: SnappedPoint


class GeometryLineString(BaseModel):
    """GeoJSON LineString biểu diễn hình học tuyến đường."""

    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]]


class AlgorithmRouteResult(BaseModel):
    """Kết quả tìm đường của một thuật toán cụ thể."""

    status: str                         # "ok" | "no_path"
    cost_s: float | None = None         # Giây (None nếu no_path)
    distance_m: float | None = None     # Mét (None nếu no_path)
    edge_ids: list[int] = Field(default_factory=list)
    # edge_twin_ids[i] = cạnh đối của edge_ids[i] (v → u, cùng đoạn đường) hoặc None nếu một chiều.
    # UI "đóng đoạn" gửi cả hai id trong blocked_edge_ids (DATA_MODEL 4.2). Thêm ở T51.
    edge_twin_ids: list[int | None] = Field(default_factory=list)
    geometry: GeometryLineString
    expanded: int
    runtime_ms: float
    trace: list[list[float]] = Field(default_factory=list)
    trace_truncated: bool = False


class RouteResponse(BaseModel):
    """Phản hồi tìm đường theo contract v1 (docs/ARCHITECTURE.md mục 4.1)."""

    dataset_id: str
    snapshot_id: str | None = None
    snapped: SnappedResponse
    results: dict[str, AlgorithmRouteResult]
    costs_match: bool | None = None
    warnings: list[str] = Field(default_factory=list)


class ZoneOut(BaseModel):
    type: str = "circle"
    lat: float
    lon: float
    radius_m: float


class RuleOut(BaseModel):
    zone: ZoneOut
    alpha: float
    highway: list[str] | None = None


class ScenarioOut(BaseModel):
    id: str
    label: str
    rules: list[RuleOut]


class DatasetResponse(BaseModel):
    """Đồ thị đang nạp và các kịch bản dùng được (cùng cấu trúc `saigo-scenarios/1`)."""

    dataset_id: str
    node_count: int
    edge_count: int
    scenarios: list[ScenarioOut]
