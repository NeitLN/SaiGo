"""Tên đường cho từng cạnh, từ bảng phụ `saigo-street-names/1` (scripts/build_street_names.py).

File đồ thị không giữ tên đường; bảng phụ ánh xạ mã đường OSM → tên. Bảng là tùy chọn: thiếu file hay file sai định
dạng thì mọi cạnh không có tên, app vẫn chạy như trước (chỉ dùng để ghi tên đoạn trong danh sách đóng đoạn).
"""

from __future__ import annotations

import json
from pathlib import Path

FORMAT = "saigo-street-names/1"


def load_street_names(path: Path) -> dict[int, str]:
    """Đọc bảng `{mã đường: tên}`; không có file hoặc sai định dạng thì trả bảng rỗng."""
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict) or doc.get("format") != FORMAT or not isinstance(doc.get("names"), dict):
        return {}
    return {int(k): str(v) for k, v in doc["names"].items() if str(k).isdigit() and str(v).strip()}


def edge_names(edge_way_ids: list[list[int]], names: dict[int, str]) -> list[str | None]:
    """Tên của mỗi cạnh: tên của mã đường đầu tiên có tên trong `way_ids` của cạnh đó, không có thì `None`."""
    out: list[str | None] = []
    for ways in edge_way_ids:
        out.append(next((names[w] for w in ways if w in names), None))
    return out
