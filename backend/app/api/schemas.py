"""Định nghĩa schema Pydantic cho request và response của API (docs/ARCHITECTURE.md mục 4.1)."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field, StrictInt, field_validator, model_validator


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
        allowed = {"dijkstra", "astar", "alt", "bidijkstra"}
        for algo in v:
            if algo not in allowed:
                raise ValueError(
                    f"thuật toán không hỗ trợ: {algo!r}, chỉ hỗ trợ 'dijkstra', 'astar', 'alt', "
                    "'bidijkstra'")
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
    # edge_geometries[i] = hình học [lon, lat] của edge_ids[i], để UI biết người dùng bấm vào cạnh nào (T54).
    edge_geometries: list[list[list[float]]] = Field(default_factory=list)
    geometry: GeometryLineString
    expanded: int
    runtime_ms: float
    trace: list[list[float]] = Field(default_factory=list)
    trace_truncated: bool = False


class BlockedEdge(BaseModel):
    """Một cạnh đóng trong request kèm hình học [lon, lat], để UI vẽ được cả cạnh đóng sẵn của case (review 14/11)."""

    edge_id: int
    geometry: list[list[float]]


class RouteResponse(BaseModel):
    """Phản hồi tìm đường theo contract v1 (docs/ARCHITECTURE.md mục 4.1)."""

    dataset_id: str
    snapshot_id: str | None = None
    snapped: SnappedResponse
    results: dict[str, AlgorithmRouteResult]
    costs_match: bool | None = None
    warnings: list[str] = Field(default_factory=list)
    # Thêm 14/11: các cạnh trong blocked_edge_ids, theo thứ tự gửi lên, bỏ trùng.
    blocked_edges: list[BlockedEdge] = Field(default_factory=list)


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


class NetworkResponse(BaseModel):
    """Mạng đường của đồ thị đang nạp, để UI vẽ nền khi không tải được tile OSM (T56 R8).

    `lines[i]` là hình học `[lon, lat]` của một đoạn đường; đoạn hai chiều chỉ có một lần.
    """

    dataset_id: str
    lines: list[list[list[float]]]


class DatasetResponse(BaseModel):
    """Đồ thị đang nạp và các kịch bản dùng được (cùng cấu trúc `saigo-scenarios/1`)."""

    dataset_id: str
    node_count: int
    edge_count: int
    scenarios: list[ScenarioOut]


# --- /api/tour (T72; TOPIC mục 15.3–15.4) ---

MAX_TOUR_STOPS = 14   # TOPIC: 5–15 điểm kể cả kho; 2-opt tính lại toàn tour nên vẫn nhanh


class TourStop(LatLon):
    """Một điểm giao; `id` do UI đặt, dùng để đánh số và báo lỗi."""

    id: str = Field(..., min_length=1, max_length=40)


class TourRequest(BaseModel):
    """Tour khép kín kho → các điểm giao → kho trên snapshot của kịch bản và cạnh đóng."""

    depot: LatLon
    stops: list[TourStop] = Field(..., min_length=1, max_length=MAX_TOUR_STOPS)
    scenario_id: str | None = "baseline"
    blocked_edge_ids: list[StrictInt] = Field(default_factory=list)   # StrictInt: không nhận true/false là id 1/0
    include_optimal: bool = False      # Held–Karp làm đối chứng, chỉ khi tổng số điểm ≤ HELD_KARP_MAX_POINTS (11)
    include_or_opt: bool = False       # Or-opt xen kẽ 2-opt, thêm ứng viên nearest_neighbor_2opt_oropt
    return_to_depot: Literal[True] = True   # chưa hỗ trợ tour mở (TOPIC 15.3): gửi false → 422
    # R1 C1: thứ tự id điểm giao của tour trước khi đóng đường; có thì thêm ứng viên kept_order.
    keep_order: list[str] | None = None

    @field_validator("stops")
    @classmethod
    def unique_ids(cls, v: list[TourStop]) -> list[TourStop]:
        ids = [s.id for s in v]
        if len(set(ids)) != len(ids) or "depot" in ids:
            raise ValueError("id điểm giao phải khác nhau và khác 'depot'")
        return v

    @model_validator(mode="after")
    def keep_order_is_permutation(self) -> TourRequest:
        if self.keep_order is not None and sorted(self.keep_order) != sorted(s.id for s in self.stops):
            raise ValueError("keep_order phải gồm đúng mỗi id điểm giao một lần (không thiếu, không thừa, không trùng)")
        return self


class SnappedStop(SnappedPoint):
    id: str


class TourCandidate(BaseModel):
    """Một phương án thứ tự giao; chi phí = tổng trọng số các cạnh trong `edge_ids`."""

    stop_order: list[str]              # id điểm giao theo thứ tự đi, không gồm kho
    cost_s: float
    distance_m: float
    improvement_pct: float             # so với thứ tự nhập: 100 · (C_nhập − C) / C_nhập
    edge_ids: list[int]
    geometry: GeometryLineString
    # R1 C3: cùng định nghĩa với /api/route, để UI biết người dùng bấm vào cạnh nào của tour.
    edge_twin_ids: list[int | None] = Field(default_factory=list)
    edge_geometries: list[list[list[float]]] = Field(default_factory=list)


class TourOptimal(BaseModel):
    stop_order: list[str]
    cost_s: float
    gap_pct: float                     # của phương án được chọn: 100 · (C_chọn − C_opt) / C_opt
    or_opt_gap_pct: float | None = None  # gap của phương án Or-opt so với tối ưu Held–Karp


class UnreachablePair(BaseModel):
    from_id: str
    to_id: str


class TourResponse(BaseModel):
    dataset_id: str
    snapshot_id: str
    status: Literal["ok", "infeasible_under_model"]
    snapped: dict[str, SnappedStop]    # "depot" và id của từng điểm giao
    candidates: dict[str, TourCandidate] = Field(default_factory=dict)   # input | nearest_neighbor | nearest_neighbor_2opt
    chosen: str | None = None
    optimal: TourOptimal | None = None
    unreachable: list[UnreachablePair] = Field(default_factory=list)
    matrix_runtime_ms: float
    order_runtime_ms: float | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_edges: list[BlockedEdge] = Field(default_factory=list)   # như RouteResponse; có cả khi không khả thi
