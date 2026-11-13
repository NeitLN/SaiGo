# SaiGo — Kế hoạch thực nghiệm

Kết quả đo được ghi ở [EXPERIMENTS.md](EXPERIMENTS.md). Tài liệu này chỉ mô tả **cách đo**. Cập nhật 26/10 theo [đề xuất đổi phạm vi](proposals/2026-10-26-pham-vi.md) đã duyệt: E3 chỉ fixed trips; 28/10 chốt giữ đủ 4 kích thước sau pilot của T61. E5 (tour) giữ lại theo quyết định chiều 26/10. Mọi ô số liệu ở đây là **[Chưa đo]**; không điền số khi chưa chạy, không ước lượng thay cho số đo.

## 1. Các thực nghiệm

| Mã | Câu hỏi | Đồ thị | Bắt buộc? |
|---|---|---|---|
| E1 | Code có đúng không? | Fixture, đồ thị ngẫu nhiên, đồ thị thật | Có |
| E2 | A* vs Dijkstra trên vùng demo (RQ1) | Vùng demo | Có |
| E3 | Lợi thế của A* khi đồ thị lớn dần (RQ1b) | 4 vùng cắt lồng nhau, chỉ fixed trips | Có |
| E4 | Ảnh hưởng của ùn tắc và đóng đường (RQ3) | Vùng demo | Có |
| E5 | Chất lượng tour (RQ2) | Vùng demo | Có (T74) |

## 2. Truy vấn

### 2.1. Sinh cặp điểm [Đề xuất]

- Chọn ngẫu nhiên có seed (`--seed 42`) từ các node thuộc SCC của đồ thị đang đo; `source ≠ target`.
- Khoảng cách chuẩn hóa: `δ = hav(s, t) / L`, với `L` là cạnh hình vuông của vùng.
- Ba tầng, mỗi tầng 1/3 số cặp: **ngắn** `δ < 0,2` · **trung bình** `0,2 ≤ δ < 0,5` · **dài** `δ ≥ 0,5`.
- Lấy mẫu loại bỏ (rejection sampling) đến khi đủ chỉ tiêu mỗi tầng. Ghi số cặp bị loại và lý do.
- **Lưu `queries.csv` trước khi đo**, gồm `query_id, workload, stratum, source, target, hav_m, delta`. Lần chạy lại phải đọc đúng file này.
- Báo cáo phân bố `δ` thực tế của từng tầng (tầng "dài" khá rộng).

### 2.2. Số lượng

| Bộ | Số cặp | Ghi chú |
|---|---|---|
| E2 vùng demo | 1.000 | Như đã nêu trong proposal |
| E3 fixed trips | 250, dùng chung cho mọi kích thước | Không trùng với bộ E2 |
| ~~E3 growing trips~~ | — | Đã cắt 26/10 |
| E4 kịch bản | 300 cặp lấy từ bộ E2 (seed riêng) | |
| E4 đóng đường | 100 cặp lấy từ bộ E2 có tuyến cơ sở ≥ 3 cạnh | |

Trước khi chạy đầy đủ, chạy **pilot 20 cặp** để ước lượng tổng thời gian chạy = số cặp × 2 thuật toán × R lần × median. Nếu quá lâu, giảm R trước rồi mới giảm số cặp, và ghi lại quyết định.

## 3. Đo lường

### 3.1. Quy trình đo [Đề xuất]

1. Một tiến trình Python; nạp đồ thị và tạo snapshot **trước** khi đo (không tính vào thời gian truy vấn).
2. Tắt trace (`trace_limit = 0`) cho cả hai thuật toán.
3. Warm-up 20 truy vấn, không ghi kết quả.
4. Mỗi cặp: chạy mỗi thuật toán R = 5 lần; cặp chẵn chạy Dijkstra trước, cặp lẻ chạy A* trước.
5. Đo `time.perf_counter_ns()` sát quanh lời gọi hàm. Thời gian tính heuristic **được** tính vào A*.
6. `gc.collect()` trước mỗi cặp; `gc.disable()` trong lúc đo, bật lại sau đó.
7. Thời gian của một cặp = **median** của R lần chạy; lưu thêm min.
8. Laptop cắm sạc, chế độ hiệu năng cố định, đóng ứng dụng nặng, không chạy song song hai benchmark.
9. Ghi `env.json`: CPU, RAM, hệ điều hành, phiên bản Python và thư viện, commit Git, `sha256` dataset, thời điểm chạy.

### 3.2. Chỉ số

| Chỉ số | Định nghĩa |
|---|---|
| Khớp chi phí | `|cost_A* − cost_D| ≤ 1e-6 · max(1, cost_D)`; kết quả `no_path` phải trùng. **Phải đạt 100%**; nếu không, dừng và sửa lỗi |
| `expanded` | Số lần pop entry hợp lệ rồi duyệt cạnh ra; không tính lần pop đích ([DATA_MODEL.md](DATA_MODEL.md) mục 6.2) |
| `relaxations`, `max_frontier`, `reopened` | Như DATA_MODEL mục 6.2 |
| Thời gian truy vấn | Median/p95 trên tập cặp, đơn vị ms |
| Tỉ lệ node mở rộng | `r = expanded_A* / expanded_D` **từng cặp**, rồi báo median và khoảng tứ phân vị |
| Speedup | `s = t_D / t_A*` **từng cặp**, rồi báo median và tứ phân vị |

Không lấy "trung bình các tỉ số" rồi gọi đó là tỉ số của hai trung bình. Ghi rõ công thức dùng trong mỗi bảng. Cặp `source == target` bị loại khi sinh cặp. Cặp có `expanded_D = 0` không xuất hiện.

### 3.3. Cột của `measurements.csv`

`run_id, suite, dataset_id, size_label, n_nodes, n_edges, query_id, workload, stratum, source, target, hav_m, algo, scenario_id, blocked_count, status, cost_s, distance_m, expanded, unique_expanded, reopened, relaxations, pushes, max_frontier, runtime_ns_median, runtime_ns_min, repeats`

Thư mục: `results/<run_id>/` với `run_id = YYYYMMDD-HHMM-<suite>-<git7>`. Mỗi thư mục gồm `queries.csv`, `measurements.csv`, `env.json`, `config.json` (tham số dòng lệnh) và các hình.

## 4. E1 — Tính đúng

| Kiểm tra | Bộ dữ liệu | Tiêu chí |
|---|---|---|
| Đáp án tính tay | `mini.json` (6 tình huống) | Chi phí, tuyến, `expanded` khớp `mini_expected.json` |
| Đối chứng ngẫu nhiên | 20 đồ thị × 50 cặp, có cạnh song song và cặp không tới được | Chi phí và `no_path` khớp NetworkX |
| Đối chứng dữ liệu thật | 200 cặp trên vùng demo | Khớp NetworkX; `reopened = 0` |
| Tính hợp lệ tuyến | Mọi truy vấn trên | Cạnh nối tiếp, đúng chiều, không chứa cạnh đóng, tổng trọng số = `cost_s` |
| Heuristic | Đồ thị thật | Ghi `c`, `v_max`, số cạnh có `length < hav` |

## 5. E2 — A* vs Dijkstra trên vùng demo (RQ1)

- 1.000 cặp, kịch bản `baseline`.
- Báo cáo theo từng tầng và toàn bộ: median/p95 thời gian, median `expanded`, phân bố `r` và `s`.
- Câu hỏi phụ cần trả lời bằng số: ở tầng ngắn, A* có thật sự nhanh hơn không? (Chi phí tính heuristic có thể lớn hơn phần tiết kiệm.)

## 6. E3 — Tăng quy mô bản đồ (RQ1b)

### 6.1. Đồ thị [Đề xuất]

- Tải **một lần** vùng nửa cạnh 4,5 km + đệm 0,5 km quanh Bến Thành (T30), rồi cắt **4** hình vuông lồng nhau, nửa cạnh **1 / 2 / 3 / 4,5 km** (T61). Ngày 28/10 chốt giữ đủ 4 (Q3): pilot của T61 cho thấy Dijkstra ở vùng lớn nhất (10.143 node) chỉ khoảng 14 ms/truy vấn, nên thêm một kích thước gần như không tốn giờ chạy.
- Chọn SCC lồng nhau (DATA_MODEL mục 8.4), nên SCC nhỏ luôn nằm trong SCC lớn.
- Trục hoành của mọi biểu đồ là **`|V|` đo được**, không phải bán kính: tăng gấp đôi bán kính không bảo đảm số node tăng gấp bốn.
- Pilot ở kích thước lớn nhất: nếu median Dijkstra > ~1 s/truy vấn thì giảm hoặc bỏ kích thước đó và ghi lý do. Một giây là trần thực tế cho thời gian chạy, không phải mục tiêu.
- Đồ thị lưới tổng hợp: **không làm** ở bản đầu. Nếu thêm sau này thì chỉ là bổ sung có kiểm soát, không phải bằng chứng về TP.HCM.

### 6.2. Workload (chỉ fixed trips từ 26/10)

| Workload | Cách lấy cặp | Đo điều gì |
|---|---|---|
| **Fixed trips** | 250 cặp từ SCC của vùng nhỏ nhất, dùng lại y hệt ở mọi kích thước | Bản đồ lớn hơn ảnh hưởng thế nào khi chuyến đi giữ nguyên (có thể xuất hiện đường vòng mới qua vùng ngoài) |
| ~~Growing trips~~ | *Đã cắt 26/10 (D11)* | Nếu làm lại: bản đồ lớn hơn **và** chuyến đi dài hơn |

Kết luận chỉ nói về fixed trips: bản đồ lớn hơn khi chuyến đi giữ nguyên. Không suy ra kết luận cho chuyến đi dài hơn trên bản đồ lớn hơn.

### 6.3. Chỉ số bổ sung

- Thời gian nạp đồ thị và bộ nhớ đỉnh khi nạp (đo **riêng**, bằng `tracemalloc`, không đo cùng lúc với thời gian truy vấn).
- Với fixed trips: tỉ lệ cặp có chi phí giảm khi bản đồ lớn hơn (nhờ có đường vòng mới).

### 6.4. Giả thuyết cần kiểm chứng (không phải kết luận)

- ~~H1~~ (growing trips): không kiểm ở bản này vì workload đã cắt.
- H2: Với fixed trips, `expanded` của cả hai thuật toán thay đổi ít theo kích thước, vì Dijkstra chỉ mở rộng các node có chi phí nhỏ hơn chi phí tới đích. Nếu đúng thì "khoảng cách chuyến đi" quan trọng hơn "kích thước bản đồ".

## 7. E4 — Ùn tắc và đóng đường (RQ3)

### 7.1. Ùn tắc

- 300 cặp × các kịch bản trong `scenarios.json` (`baseline`, `peak-center`, …).
- Chỉ số: tỉ lệ cặp **đổi tuyến** (tập cạnh khác cơ sở), % tăng chi phí, thay đổi `expanded` của A* và của `r`.
- Giả thuyết H3: dưới ùn tắc, `r` tăng (A* kém lợi thế hơn), vì heuristic dùng `v_max` cơ sở nên cận dưới lỏng hơn.

### 7.2. Đóng đường

- 100 cặp có tuyến cơ sở ≥ 3 cạnh. Quy tắc cố định: đóng cạnh ở vị trí `⌊k/2⌋` của tuyến (k = số cạnh), theo kiểu **đóng đoạn** (cả cạnh đối nếu có).
- Chạy lại cả hai thuật toán. Kiểm tra tuyến mới không chứa cạnh đóng.
- Chỉ số: tỉ lệ còn đường, % tăng chi phí, thời gian lập lại = thời gian tạo snapshot + thời gian tìm (ghi riêng hai phần).
- **Bộ không còn đường:** 30 cặp, đóng mọi cạnh đi vào đích. Đo thời gian để kết luận `no_path` của hai thuật toán. Dự kiến A* không có lợi thế (ví dụ ở DATA_MODEL mục 7); cần số đo để xác nhận.

## 8. E5 — Tour

- n ∈ {4, 6, 8, 10} điểm giao, 20 bộ mỗi n (seed); kho và điểm giao lấy từ SCC vùng demo, cách nhau ≥ 150 m; thứ tự nhập = thứ tự sinh ngẫu nhiên.
- Phương án: thứ tự nhập, NN, NN + 2-opt, Held–Karp (tối ưu).
- Chỉ số: `Improvement% = 100 · (C_nhập − C_pp) / C_nhập`; `Gap% = 100 · (C_pp − C_opt) / C_opt`; thời gian xây ma trận, thời gian sắp thứ tự, thời gian dựng tuyến ghi riêng; số bộ không khả thi (không gán gap 0 cho các bộ này).

## 9. Bảng kết quả mẫu

| Thuật toán | Tầng | Median ms | p95 ms | Median expanded | Khớp chi phí |
|---|---|---|---|---|---|
| Dijkstra | tất cả | Chưa đo | Chưa đo | Chưa đo | — |
| A* | tất cả | Chưa đo | Chưa đo | Chưa đo | Chưa kiểm tra |

| Kích thước | \|V\| | \|E\| | Workload | Median r | Median s | Median ms Dijkstra | Median ms A* |
|---|---|---|---|---|---|---|---|
| 1 km | Chưa đo | Chưa đo | fixed | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| … | | | | | | | |

| Kịch bản | % đổi tuyến | Median % tăng chi phí | Median r | Tỉ lệ còn đường |
|---|---|---|---|---|
| peak-center | Chưa đo | Chưa đo | Chưa đo | — |
| đóng đoạn giữa tuyến | — | Chưa đo | Chưa đo | Chưa đo |

## 10. Biểu đồ dự kiến

1. Boxplot `expanded` của Dijkstra và A* theo tầng (E2).
2. Scatter `expanded_D` với `expanded_A*` trên trục log, kèm đường y = x (E2).
3. Median `expanded` và median thời gian theo `|V|`, fixed trips (E3).
4. Median `r` theo `|V|` (E3).
5. Boxplot `r` theo kịch bản (E4).
6. *(E5)* Improvement và gap theo n.

Mỗi hình ghi `run_id`, số cặp và `dataset_id` trong chú thích.

## 11. Mối đe dọa tới tính hợp lệ

| Mối đe dọa | Cách giảm |
|---|---|
| Thời gian Python dao động | Warm-up, R lần, median, đổi thứ tự, `gc.disable`, cùng máy |
| Chỉ một khu vực | Ghi rõ trong giới hạn; không khái quát cho mọi thành phố |
| Tốc độ giả định | Kết quả chỉ đúng với mô hình; ghi rõ bảng tốc độ đã dùng |
| Hiệu ứng biên khi cắt vùng | Vùng đệm; workload fixed trips lấy từ vùng lõi; công bố quy ước cắt |
| Simplify và snap về node | Cùng một quy trình cho mọi kích thước |
| Chỉ có một máy đo | Ghi `env.json`; nếu kịp thì chạy lại một bộ nhỏ trên máy thứ hai để kiểm tra xu hướng |
