# Phiếu bắt đầu — Bùi Duy Anh (@anh7032)

> **Từ 26/10 phân công đã đổi** (cắt T32; Duy Anh vắng sáng 26/10 rồi quay lại chiều 26/10). Danh sách task dưới đây là của tuần 1; việc hiện tại xem [phiếu giao việc](../../tasks/README.md), [ROADMAP](../../ROADMAP.md) mục 6 và tab Issues.

**Vai trò:** Dijkstra, A*, heuristic, test đối chứng; sau đó thuật toán tour (NN, 2-opt, Held–Karp).
Làm xong [ONBOARDING.md](../ONBOARDING.md) mục 1–5 trước.

## Task của bạn theo thứ tự

| Thứ tự | Issue | Task | Dự kiến | Review bởi |
|---|---|---|---|---|
| 1 | [#3](https://github.com/NeitLN/SaiGo/issues/3) | T01 · Định dạng đồ thị, fixture mẫu, bộ nạp Graph | 23–24/10 | Tiến |
| 2 | [#6](https://github.com/NeitLN/SaiGo/issues/6) | T10 · Hàm địa lý (haversine, trung điểm) | 24–25/10 | Tiến |
| 3 | [#7](https://github.com/NeitLN/SaiGo/issues/7) | T11 · Dijkstra + SearchResult | 24–26/10 | Tiến |
| 4 | [#9](https://github.com/NeitLN/SaiGo/issues/9) | T20 · A* + heuristic địa lý | 26–27/10 | Tiến |
| 5 | [#10](https://github.com/NeitLN/SaiGo/issues/10) | T21 · Đối chứng NetworkX trên đồ thị ngẫu nhiên | 27–28/10 | Tiến |
| 6 | [#11](https://github.com/NeitLN/SaiGo/issues/11) | T22 · Kiểm tra điều kiện heuristic | 27–28/10 | Tiến |
| 7 | [#15](https://github.com/NeitLN/SaiGo/issues/15) | T33 · Dữ liệu thật + đối chứng 200 cặp (cùng Tiến) | 28–29/10 | Minh |
| 8 | [#32](https://github.com/NeitLN/SaiGo/issues/32) | T70 · Tour trên ma trận: NN, 2-opt có hướng | 29–31/10 | Tiến |
| 9 | [#33](https://github.com/NeitLN/SaiGo/issues/33) | T71 · Held–Karp | 31/10–02/11 | Tiến |

Thêm: viết phần của mình trong [#31](https://github.com/NeitLN/SaiGo/issues/31) (T65, kết quả) và [#40](https://github.com/NeitLN/SaiGo/issues/40) (T83, essay).
Danh sách luôn cập nhật: [issue được giao cho bạn](https://github.com/NeitLN/SaiGo/issues?q=is%3Aopen+assignee%3Aanh7032).

**Bạn review:** [#5](https://github.com/NeitLN/SaiGo/issues/5) T03 của Bảo (đáp án tính tay; T11 dùng file này), các PR của Tiến (PR #43, PR onboarding, T12, T40, T41, T51, T60…). CODEOWNERS tự gửi yêu cầu review cho bạn ở `backend/app/algorithms/` và `backend/app/graph/`.

## Đọc trước

- [DATA_MODEL.md](../../DATA_MODEL.md) mục 2 (định dạng `saigo-graph/1`), 5 (heuristic, chứng minh), 6 (chữ ký hàm, `SearchResult`, quy tắc cài đặt), 7 (ví dụ 6 node).
- [TOPIC.md](../../TOPIC.md) mục 9.1–9.3 (pseudocode Dijkstra/A*).
- [ARCHITECTURE.md](../../ARCHITECTURE.md) mục 3 (file nào ở đâu).

## Task đầu tiên: T01 (#3) từng bước

**Branch:** `t01-graph-model`

1. **`tests/fixtures/mini.json`**, theo `saigo-graph/1`:
   - 6 node id 0–5 theo thứ tự S, A, T, B, C, D; mỗi node thêm `"name"`.
   - Đổi tọa độ mét (x, y) ở DATA_MODEL mục 7 sang độ quanh tâm (10.7725, 106.6980):
     `lat = 10.7725 + y / 111320`, `lon = 106.6980 + x / (111320 · cos(10.7725°))`.
   - Giữ `length_m` đúng 400/500/300 để đáp án là số tròn (80 s, 100 s…).
   - **Bẫy:** phải có `haversine(u, v) ≤ length_m` ở mọi cạnh, nếu không heuristic không còn chắc là cận dưới. Với đúng công thức trên (R = 6 371 009 m), haversine thấp hơn `length_m` khoảng 0,3 m, nên đạt. Nếu dùng hằng số khác mà vượt, nhân x, y với 0,999 trước khi đổi.
   - 8 cạnh, mọi cạnh `speed_kmh: 36`, `highway: "residential"`. `geometry` gồm 2 điểm `[lon, lat]`. Đánh `id` sau khi sắp theo `(u, v, key)`: (0,1), (0,3), (0,4), (0,5), (1,2), (2,3), (3,0), (3,2).
2. **`backend/app/graph/model.py`**:
   - `Graph` theo DATA_MODEL mục 2.2, cộng `GraphMeta` (geometry, highway, way_ids, tên node).
   - `load_graph(path) -> tuple[Graph, GraphMeta]`: kiểm tra theo mục 2.3, raise `ValueError` có thông báo rõ.
   - `node_by_name(meta, "S") -> int`.
3. **`tests/test_graph_model.py`**:
   - Có 6 node và 8 cạnh.
   - `out_edges[S]` gồm 4 cạnh.
   - Có A→T nhưng không có T→A.
   - `base_time_s` của S→A là 40.
   - `v_max_mps` là 10.
   - Mọi cạnh có `haversine(u, v) ≤ length_m` (dùng tạm công thức tự viết trong test; T10 sẽ có hàm chung).
   - File có `speed_kmh: 0` bị từ chối.
4. Chạy `.venv\Scripts\python.exe -m pytest tests/test_graph_model.py -q`, mở PR `Closes #3`.
5. **Phối hợp:** khi PR được merge, bình luận vào [#13](https://github.com/NeitLN/SaiGo/issues/13) (T31 của Minh) rằng định dạng đã chốt, kèm link file. Minh xuất dữ liệu thật đúng định dạng này.

**Bẫy chung:** không chuyển đồ thị sang vô hướng; cạnh song song phải có ID riêng; km/h ÷ 3,6 = m/s; trong JSON, `geometry` là `[lon, lat]` còn node là `lat`/`lon` có tên trường.

## Phải giải thích được trước giảng viên

- Vì sao adjacency theo **edge id** chứ không theo cặp node (cạnh song song, đóng đường đúng cạnh).
- Dijkstra đúng khi trọng số không âm; lazy deletion; độ phức tạp `O((V+E) log V)`.
- `h = c · haversine / v_max` là cận dưới và consistent (DATA_MODEL mục 5.2); vì sao `h = 0` thì A* giống Dijkstra.
- Vì sao A* không pop C, D trong ví dụ; vì sao khi không có đường thì A* không tiết kiệm được gì.
