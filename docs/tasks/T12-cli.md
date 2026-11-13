# T12 — CLI tìm đường (có cả A*)

Tuần mục tiêu: 2 (30–31/10) · Giao cho: Bảo (thay Tiến, vì Tiến nhận thêm T11, T20) · Nhánh: `t12-cli` · Issue: [#8](https://github.com/NeitLN/SaiGo/issues/8)
Review: Tiến · Người tích hợp: Tiến
Phụ thuộc: T11 (**bắt đầu**; đã merge #59) · T13 (**tích hợp**: `--from-latlon` dùng hàm snap của T13; làm phần tên node trước) · T20 (**chấp nhận**: chỉ tính là xong khi gọi được cả A*) · Ước lượng: 2 giờ

## Mục tiêu
Chạy thuật toán bằng dòng lệnh để kiểm tra và giải thích, chưa cần web. T22 và T33 (tuần 3) sẽ dùng CLI này trên dữ liệu thật.

## Việc cần làm
1. **`backend/app/cli.py`:**
   ```text
   python -m app.cli route --graph <file> --from S --to T --algo dijkstra|astar|both
   python -m app.cli route --graph <file> --from-latlon 10.7725,106.6980 --to-latlon 10.7730,106.7050 --algo both
   ```
   - Nhận tên node (`--from S`, dùng `node_by_name(meta, "S")`) hoặc tọa độ (`--from-latlon`); với tọa độ thì tạm dùng `nearest_node_naive(graph, meta, lat, lon)` của T13.
   - In ra: tuyến (tên hoặc ID node), chi phí (s), quãng đường (m), `expanded`, thời gian chạy (ms), và dòng "Chi phí trùng khớp: có/không" khi `--algo both`.
2. **`tests/test_cli.py`:** chạy `main([...])` với `mini.json`, kiểm chuỗi in ra có `80.0` và `expanded` đúng.

## Sở hữu (chỉ task này được tạo/sửa) trong tuần 2
- `backend/app/cli.py`
- `tests/test_cli.py`

## Dùng (chỉ đọc)
- `graph/model.py`, `algorithms/*`, `services/routing.py`

## Tiêu chí chấp nhận
- [ ] `PYTHONPATH=backend python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo both` → Dijkstra 80 s / expanded 5; A* 80 s / expanded 2; "Chi phí trùng khớp: có"
- [ ] `pytest tests/test_cli.py -q` → PASS

## Kiến thức cần giải thích được
Vì sao đo thời gian chỉ quanh lời gọi thuật toán (`perf_counter_ns`), không tính phần nạp đồ thị.
