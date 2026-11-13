# T62 — E3: tăng quy mô bản đồ, fixed trips

**Đặc tả đã duyệt 13/11 (Tiến).** Giao cho: Tiến · Review: Minh (D14) · Issue: [#27](https://github.com/NeitLN/SaiGo/issues/27)
Phụ thuộc: T60 (runner, **tích hợp**), T61 (4 vùng cắt lồng nhau, **đã merge** #82), #105 (manifest LF, **bắt đầu**: cần để run ghi `git_dirty: false`)
Ước lượng: 3 h (code 1,5 h + chạy ~20 phút + kiểm)

## Khảo sát

- **Hiện tại:** `run_benchmarks.py --suite scaling` chạy **một** đồ thị mỗi lần; `--queries` dùng lại `queries.csv` nhưng file này lưu **id node**, mà mỗi vùng cắt đánh số node lại từ đầu (node giữ `osmid`). Chưa đo thời gian nạp và bộ nhớ (EXPERIMENT_PLAN 6.3). `plot_results.py` gộp được nhiều thư mục run và vẽ hình 3 theo `n_nodes` khi có ≥ 2 kích thước.
- **Mong muốn:** 250 cặp lấy trong SCC vùng 1 km, chạy **y hệt** trên 4 vùng 1 / 2 / 3 / 4,5 km.
- **Phải giữ nguyên:** 27 cột `measurements.csv`; quy trình đo mục 3.1 (warm-up 20, lặp 5, đảo thứ tự thuật toán); sha256 4 vùng trong `crop_manifest.json`.
- **Chưa biết:** không có (pilot T61: Dijkstra vùng 4,5 km ~14 ms/truy vấn, 250 cặp × 4 vùng × 2 thuật toán × 6 lần chạy ≈ vài phút).

## Quy tắc

| ID | Quy tắc |
|---|---|
| S1 | Sinh 250 cặp bằng `generate_queries` trên **vùng 1 km** (seed 42, phân tầng như E2), lưu `queries.csv` kèm cột `source_osmid`, `target_osmid` |
| S2 | Ở mỗi vùng, đổi cặp sang id node của vùng đó qua `osmid`. WHEN một `osmid` không có trong SCC của vùng lớn hơn THE SYSTEM SHALL dừng và báo lỗi (SCC lồng nhau bảo đảm điều này không xảy ra; nếu xảy ra là dữ liệu sai, không được bỏ qua lặng lẽ) |
| S3 | Mọi vùng dùng **cùng một** `run_id`, `suite = scaling`, `workload = fixed_trips`, `size_label = r1000 / r2000 / r3000 / r4500`; ghi chung một `measurements.csv` để vẽ hình 3 bằng một thư mục |
| S4 | Đo thời gian nạp đồ thị và bộ nhớ đỉnh khi nạp **riêng**, bằng `tracemalloc`, không cùng lúc với thời gian truy vấn; ghi `load.csv` (`size_label, n_nodes, n_edges, load_ms, peak_mb`) |
| S5 | Trước khi chạy, dựng lại 4 vùng bằng `make_crops.py`, kiểm sha256 khớp `crop_manifest.json`, commit manifest nếu chỉ khác version máy; run phải ghi `git_dirty: false` |

## Ví dụ chấp nhận

| Kiểm tra | Phải ra | Nguồn |
|---|---|---|
| Đếm dòng | 250 cặp × 4 vùng × 2 thuật toán = 2.000 dòng, `status = ok` hết | S1–S3 |
| Cùng cặp ở mọi vùng | `source_osmid`, `target_osmid` của mỗi `query_id` giống nhau ở cả 4 vùng | S2 |
| Bất biến chi phí (vùng lớn chứa mọi cạnh của vùng nhỏ) | Với mỗi cặp: `cost_s(r4500) ≤ cost_s(r3000) ≤ cost_s(r2000) ≤ cost_s(r1000)` (sai số 1e-6) | DATA_MODEL 8.4, đề xuất của Tiến |
| Đúng đắn | Mỗi cặp, mỗi vùng: chi phí Dijkstra = A* (sai số 1e-6) | E1 |
| `osmid` lạ | Test: vùng thiếu một `osmid` → lỗi tiếng Việt nêu `osmid` đó, không ghi CSV | S2 |
| `load.csv` | 4 dòng, `n_nodes` = 565 / 1.889 / 4.411 / 10.143 như `crop_manifest.json` | S4 |
| Hình | `plot_results.py <run_dir>` ra hình 3 (median `expanded` và thời gian theo `|V|`) | T64 |
| Tái lập | Chạy lại với seed 42 ra `queries.csv` cùng sha256 | 3.1 |

Báo cáo trong EXPERIMENTS (T65): H2 đúng hay sai theo số đo; tỉ lệ cặp có chi phí giảm khi vùng lớn hơn (nhờ đường vòng mới). Chỉ kết luận cho fixed trips.

## Ngoài phạm vi

Growing trips (cắt 26/10, D11); đồ thị lưới tổng hợp.
