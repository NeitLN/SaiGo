# T01 — Chốt định dạng đồ thị, fixture mẫu và `load_graph`

**Trạng thái: ✅ đã merge 26/10 ([#57](https://github.com/NeitLN/SaiGo/pull/57)).** Còn một tiêu chí chờ dữ liệu thật (T34).

Tuần mục tiêu: 2 (26–27/10, **trễ từ 24/10**) · Giao cho: Tiến (thay Duy Anh, vắng tuần 2; đã chuyển 26/10) · Nhánh: `t01-graph-model` · Issue: [#3](https://github.com/NeitLN/SaiGo/issues/3)
Review: Bảo (đối chiếu fixture với bảng tính tay T03); Minh xác nhận `load_graph` đọc được file của T31 · Người tích hợp: Tiến
Phụ thuộc: interface `Graph`/`GraphMeta` (chặn **bắt đầu**; đã chốt cùng #57) · Ước lượng: 3 giờ

## Mục tiêu
Một bộ nạp đồ thị dùng chung đọc được **cả** fixture 6 node **lẫn** đồ thị vùng demo do T31 xuất ra. Đây là **Q1**: T11, T13, T20 code theo interface này ngay từ 27/10.

## Interface (đã chốt cùng #57; đổi sau đó phải báo Tiến và Bảo)
```python
@dataclass(frozen=True)
class Graph:                 # chỉ những thứ thuật toán cần (DATA_MODEL mục 2.2)
    dataset_id: str
    node_lat: list[float]; node_lon: list[float]
    edge_u: list[int]; edge_v: list[int]
    edge_length_m: list[float]; edge_speed_mps: list[float]; edge_base_time_s: list[float]
    out_edges: list[list[int]]   # out_edges[u] = edge id đi ra từ u, sắp tăng dần
    v_max_mps: float

@dataclass(frozen=True)
class GraphMeta:             # thứ để vẽ và tra cứu, thuật toán không đọc
    node_osmid: list[int | None]; node_name: list[str | None]; node_in_scc: list[bool]
    edge_key: list[int]; edge_way_ids: list[list[int]]; edge_highway: list[str | None]
    edge_oneway: list[bool]; edge_geometry: list[list[list[float]]]   # [lon, lat]

def load_graph(path: str | Path) -> tuple[Graph, GraphMeta]: ...
def node_by_name(meta: GraphMeta, name: str) -> int: ...
```
`in_scc` không có trong file thì mặc định `True`. Như vậy fixture không cần trường này, còn file của T31 thì có.

## Việc cần làm
1. **`tests/fixtures/mini.json`** theo `saigo-graph/1`, dựa trên ví dụ ở DATA_MODEL mục 7:
   - 6 node id 0–5 theo thứ tự S, A, T, B, C, D, mỗi node có `"name"`.
   - Đổi tọa độ (x, y) mét sang độ quanh (10.7725, 106.6980): `lat = 10.7725 + y/111320`, `lon = 106.6980 + x/(111320·cos(10.7725°))`. Với công thức này, haversine thấp hơn `length_m` từ 0,33 đến 0,57 m tùy cạnh, đã kiểm.
   - `length_m` giữ đúng 400 / 500 / 300.
   - 8 cạnh, `speed_kmh: 36`, `highway: "residential"`. Đánh `id` sau khi sắp theo `(u, v, key)`: (0,1), (0,3), (0,4), (0,5), (1,2), (2,3), (3,0), (3,2).
2. **`backend/app/graph/model.py`**: `Graph`, `GraphMeta`, `load_graph`, `node_by_name`. Kiểm tra khi nạp theo DATA_MODEL mục 2.3; sai thì raise `ValueError` có thông báo rõ.
3. **`tests/test_graph_model.py`**:
   - Có 6 node và 8 cạnh.
   - `out_edges[S]` gồm 4 cạnh.
   - Có A→T nhưng không có T→A.
   - `base_time_s` của S→A là 40.
   - `v_max_mps` là 10.
   - `speed_kmh: 0` bị từ chối.
   - Nếu có `data/processed/manifest.json` thì nạp được đồ thị vùng demo (đánh dấu `realdata`).
4. **DATA_MODEL mục 2.1**: thêm một dòng mô tả trường `in_scc` (theo quyết định Q1).
5. Test `load_graph` trong `tests/test_realdata.py` (nằm ở #53 của Minh) tự bật khi có `app.graph.model`. Test này phải nhận đúng cặp trả về: `g, _ = model.load_graph(...)` (sửa trong #53, xem T34).

## Sở hữu (chỉ task này được tạo/sửa)
- `backend/app/graph/model.py`
- `tests/fixtures/mini.json`
- `tests/test_graph_model.py`
- Mục 2.1 của DATA_MODEL
- Test `load_graph` trong `tests/test_realdata.py`

## Dùng (chỉ đọc)
- DATA_MODEL mục 2, 7
- `data/processed/manifest.json`
- `tests/fixtures/mini_expected.json` (T03, PR #54)

## Tiêu chí chấp nhận
- [x] `pytest tests/test_graph_model.py -q` → PASS (17 test, #57)
- [ ] `pytest -m realdata -q` → `load_graph` đọc được đồ thị vùng demo (1.889 node, 4.004 cạnh). **Chờ T34:** Release chưa có, chưa máy nào ngoài máy Minh có file
- [x] Bảo xác nhận fixture khớp DATA_MODEL mục 7 và bảng tính tay của T03 (review #57)
- [x] Không đồ thị nào bị chuyển sang vô hướng; cạnh song song có ID riêng (`test_directed_one_way`; cạnh song song kiểm trong `test_dijkstra.py`)

## Ngoài phạm vi
Dijkstra/A* (T11, T20); haversine dùng chung (T10); snap (T50).

## Khi xong
Bình luận vào #7 (T11) và #49 (T13) rằng interface đã merge, kèm link file.
