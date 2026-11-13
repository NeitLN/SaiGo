# T74 — E5: benchmark tour

**Đặc tả đã duyệt 13/11 (Tiến).** Giao cho: Tiến · Review: Minh (D14) · Issue: [#36](https://github.com/NeitLN/SaiGo/issues/36)
Phụ thuộc: T70, T71 (thuật toán tour, **đã merge**), T72 (`cost_matrix`, **đã merge** #102), T64 phần E5 (**đã merge** #96)
Ước lượng: 3 h

## Khảo sát

- **Hiện tại:** `plot_results.py` và `summarize_results.py` đã đọc `tour_measurements.csv` và vẽ hình 6, nhưng **chưa có gì sinh ra file này**; thông báo lỗi trỏ tới `E5_proposal.md mục 2`, file không có trong repo. `services/tour.py` có `cost_matrix` (ma trận từ đồ thị, T72); `algorithms/tour.py` có NN, 2-opt có hướng, Held–Karp (≤ 11 điểm kể cả kho).
- **Mong muốn:** số đo E5 theo EXPERIMENT_PLAN mục 8.
- **Phải giữ nguyên:** 15 cột mà `plot_results.TOUR_COLUMNS` đang đọc: `run_id, suite, dataset_id, set_id, n_stops, seed, depot_node, stop_nodes, method, feasible, cost_s, order, matrix_ns, order_ns, route_ns`; tên phương án `input`, `nearest_neighbor`, `nearest_neighbor_2opt`, `held_karp`.
- **Chưa biết:** không có (Held–Karp 11 điểm ~ 11² · 2¹⁰ phép tính, dưới 1 s).

## Quy tắc

| ID | Quy tắc |
|---|---|
| U1 | `run_benchmarks.py --suite tour` trên đồ thị demo: n ∈ {4, 6, 8, 10} điểm giao, 20 bộ mỗi n (seed 42), mỗi bộ có kho + n điểm lấy trong SCC, các điểm cách nhau ≥ 150 m (haversine); thứ tự nhập = thứ tự sinh |
| U2 | Mỗi bộ ghi 4 dòng (một dòng mỗi phương án) với đúng 15 cột trên; `order` là id điểm theo thứ tự ghé, ngăn cách bằng `;` |
| U3 | Thời gian ghi riêng: `matrix_ns` (dựng ma trận, một lần mỗi bộ, chép vào cả 4 dòng), `order_ns` (sắp thứ tự của phương án đó), `route_ns` (nối tuyến từ các chặng) |
| U4 | IF một bộ có chặng không đi được THEN `feasible = false` cho cả 4 dòng, `cost_s` rỗng; bộ đó không tính vào improvement hay gap, nhưng được đếm |
| U5 | Sửa thông báo lỗi trong `plot_results.py` và `summarize_results.py` trỏ về phiếu này thay cho `E5_proposal.md` |

## Ví dụ chấp nhận

| Kiểm tra | Phải ra | Nguồn |
|---|---|---|
| Đếm dòng | 4 n × 20 bộ × 4 phương án = 320 dòng | U1, U2 |
| Thứ tự chi phí (bộ khả thi) | `held_karp ≤ nearest_neighbor_2opt ≤ nearest_neighbor` (sai số 1e-6) | T70, T71 |
| Khớp API | Bộ "Kho + 5 điểm giao" của T55 chạy qua cùng hàm cho 1.066,0 / 1.003,3 / 898,1 / 627,8 s như `/api/tour` | T72, case T55 |
| Khoảng cách điểm | Mọi cặp điểm trong một bộ cách nhau ≥ 150 m | U1 |
| Bộ không khả thi | Test trên `mini.json` với cạnh đóng làm một chặng không đi được → 4 dòng `feasible = false`, `summarize_results.py` không tính gap cho bộ đó | U4 |
| Đọc lại | `plot_results.py <run_dir>` ra hình 6; `summarize_results.py` ra bảng improvement và gap theo n | T64 |
| Tái lập | Cùng seed → cùng `depot_node`, `stop_nodes` | 3.1 |

Báo cáo trong EXPERIMENTS (T65): Improvement% và Gap% (median, p90) theo n; số bộ không khả thi; thời gian ma trận so với sắp thứ tự. Nêu case demo (2-opt kém tối ưu 43%, tối ưu là tour NN đi ngược chiều; Minh phát hiện 31/10) như một ví dụ, không như kết luận chung.

## Ngoài phạm vi

Tour mở (không quay về kho); chạy tour dưới kịch bản ùn tắc.
