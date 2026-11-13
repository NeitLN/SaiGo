# T63 — E4: ùn tắc và đóng đường

**Đặc tả đã duyệt 13/11 (Tiến).** Giao cho: Tiến · Review: Minh (D14) · Issue: [#28](https://github.com/NeitLN/SaiGo/issues/28)
Phụ thuộc: T60 (runner, **tích hợp**), T41/T42 (snapshot, `scenarios.json`, **đã merge**), #105 (**bắt đầu**)
Ước lượng: 4 h (code 2,5 h + chạy + kiểm)

## Khảo sát

- **Hiện tại:** `--suite scenario` chạy một kịch bản mỗi lần với **một** danh sách `--blocked` dùng chung cho mọi cặp. `measurements.csv` không ghi tuyến đi qua cạnh nào, nên không tính được "tỉ lệ đổi tuyến" (EXPERIMENT_PLAN 7.1). Chưa có đóng cạnh theo từng cặp (7.2) và bộ "không còn đường". Hình 5 của `plot_results.py` vẽ `r` theo `scenario_id`.
- **Mong muốn:** đủ ba phần của mục 7: ùn tắc, đóng một đoạn giữa tuyến, không còn đường.
- **Phải giữ nguyên:** 27 cột hiện có và thứ tự của chúng (`plot_results.py`, `summarize_results.py` chỉ báo lỗi khi **thiếu** cột, nên thêm cột ở cuối là an toàn); quy trình đo mục 3.1.
- **Chưa biết:** không có.

## Quy tắc

| ID | Quy tắc |
|---|---|
| C1 | Ùn tắc: 300 cặp vùng demo (seed 42) chạy dưới **mọi** kịch bản trong `scenarios.json`, cùng `queries.csv`, cùng `run_id` |
| C2 | Thêm cột cuối `route_sig` vào `measurements.csv`: 12 ký tự đầu sha1 của danh sách `edge_ids` (rỗng khi `no_path`). Hai dòng cùng cặp có `route_sig` khác nhau nghĩa là **đổi tuyến** |
| C3 | Đóng đường: 100 cặp có tuyến cơ sở (Dijkstra) ≥ 3 cạnh. Mỗi cặp đóng cạnh ở vị trí `⌊k/2⌋` của tuyến cơ sở **và cạnh đối** nếu có (kiểu "đóng đoạn" của UI). Danh sách cạnh đóng của từng cặp ghi vào `queries.csv` (cột `blocked_edges`) |
| C4 | Không còn đường: 30 cặp, đóng **mọi cạnh đi vào đích**. Ghi thời gian hai thuật toán cần để kết luận `no_path` |
| C5 | Thời gian lập lại = thời gian dựng snapshot + thời gian tìm, ghi **riêng**: thêm cột cuối `snapshot_ns` (0 cho các suite không dựng snapshot theo cặp) |
| C6 | `suite` = `scenario` (C1), `closure` (C3), `nopath` (C4) để hình và bảng tách được |

Nếu trễ lịch (đã duyệt 13/11): cắt C4 trước, rồi C3; C1 luôn làm.

## Ví dụ chấp nhận

| Kiểm tra | Phải ra | Nguồn |
|---|---|---|
| Đếm dòng C1 | 300 cặp × số kịch bản (hiện 3) × 2 thuật toán | C1 |
| Bất biến ùn tắc (α ≥ 1 chỉ làm trọng số tăng) | Mỗi cặp: `cost_s(peak-*) ≥ cost_s(baseline)` (sai số 1e-6) | DATA_MODEL, đề xuất của Tiến |
| Case T55 trên đồ thị demo | Dinh Độc Lập → Bitexco: baseline 186,1 s, `peak-center` 246,1 s, `route_sig` khác nhau | Số đã kiểm ở T55/T56 |
| Đóng đoạn | Mỗi cặp C3: tuyến mới không chứa cạnh nào trong `blocked_edges`; `cost_s` mới ≥ cơ sở hoặc `no_path` | C3, T41 |
| Không còn đường | 30/30 cặp `status = no_path` ở cả hai thuật toán | C4 |
| Đúng đắn | Mọi dòng `ok`: chi phí Dijkstra = A* | E1 |
| Cột mới | Test: `measurements.csv` có đúng 27 cột cũ theo thứ tự cũ, rồi `route_sig`, `snapshot_ns`; `plot_results.py` và `summarize_results.py` vẫn chạy với file cũ (thiếu 2 cột mới) và file mới | C2, C5 |
| Hình | Hình 5 có `baseline`, `peak-center`, `peak-ben-thanh` | T64 |

Báo cáo trong EXPERIMENTS (T65): tỉ lệ đổi tuyến, % tăng chi phí, `r` theo kịch bản (H3); tỉ lệ còn đường sau khi đóng, % tăng chi phí; thời gian kết luận `no_path` (dự kiến A* không có lợi thế, phải có số mới được nói).

## Ngoài phạm vi

Kịch bản mới ngoài `scenarios.json`; đóng nhiều đoạn một lúc.
