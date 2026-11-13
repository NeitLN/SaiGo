# T11 — Dijkstra và SearchResult

**Trạng thái: ✅ đã merge 26/10 ([#59](https://github.com/NeitLN/SaiGo/pull/59)).**

Tuần mục tiêu: 2 (27–28/10) · Giao cho: Tiến (thay Duy Anh) · Nhánh: `t11-dijkstra` · Issue: [#7](https://github.com/NeitLN/SaiGo/issues/7)
Review: Bảo (đối chiếu với đáp án T03) · Người tích hợp: Tiến
Phụ thuộc: T01 (**tích hợp**; đã merge #57) · T03/#54 (**chấp nhận**; đã merge) · Ước lượng: 4 giờ

## Mục tiêu
Dijkstra đúng theo quy tắc ở DATA_MODEL mục 6, trả về `SearchResult` mà T13, T20, T12 dùng chung.

## Interface
```python
@dataclass(frozen=True)
class Snapshot:                       # định nghĩa DUY NHẤT, trong graph/scenario.py; T40 thêm Scenario + build_snapshot vào cùng file
    dataset_id: str
    scenario_id: str
    weights: list[float]              # weights[e]; math.inf nếu cạnh bị đóng
    blocked: frozenset[int]
    snapshot_id: str

def baseline_snapshot(graph: Graph) -> Snapshot: ...     # weights = edge_base_time_s

@dataclass(frozen=True)
class SearchResult: ...               # đủ trường ở DATA_MODEL mục 6.2

def dijkstra(graph: Graph, snap: Snapshot, source: int, target: int, *, trace_limit: int = 0) -> SearchResult: ...
```

## Việc cần làm
1. **`algorithms/result.py`:** `SearchResult`; hàm dựng tuyến từ `pred_edge`.
2. **`graph/scenario.py`** (đúng vị trí trong ARCHITECTURE mục 3): `Snapshot`, `baseline_snapshot`. T40 sẽ thêm `Scenario` và `build_snapshot` vào chính file này.
3. **`algorithms/dijkstra.py`:**
   - heap `(g, counter, node)`;
   - lazy deletion: bỏ entry lỗi thời **trước** khi kiểm đích;
   - dừng khi pop được đích;
   - đếm `expanded` (không tính lần pop đích), `relaxations`, `pushes`, `max_frontier`;
   - `source == target` trả chi phí 0, `expanded = 0`.
4. **`tests/test_dijkstra.py`:**
   - 6 tình huống trong `tests/fixtures/mini_expected.json`. Với tình huống ùn tắc, tạo `Snapshot` bằng tay trong test; T40 mới làm luật vùng.
   - `source == target`.
   - Cạnh song song: thêm vào bản sao fixture một cạnh S→A nhanh hơn, tuyến phải dùng đúng edge id đó.
   - Tổng `weights` theo `edge_ids` bằng `cost_s`.

## Sở hữu (chỉ task này được tạo/sửa)
- `backend/app/algorithms/result.py`, `dijkstra.py`
- `backend/app/graph/scenario.py` (tuần 2; T40 sửa tiếp ở tuần 3)
- `tests/test_dijkstra.py`

## Dùng (chỉ đọc)
- `graph/model.py` (T01)
- `tests/fixtures/mini.json`, `mini_expected.json`

## Tiêu chí chấp nhận
- [x] `pytest tests/test_dijkstra.py -q` → PASS
- [x] Tình huống cơ sở S→T: `cost_s = 80`, tuyến S→A→T, `expanded = 5`
- [x] T→S: 100. Đóng A→T và B→T: `no_path`
- [x] Bảo approve sau khi đối chiếu đủ 6 tình huống với bảng tính tay (review #59)

## Ngoài phạm vi
A* (T20); luật ùn tắc theo vùng (T40); CLI (T12).

## Khi xong
Bình luận vào #49 (T13), #9 (T20), #8 (T12) rằng `dijkstra()` đã merge.
