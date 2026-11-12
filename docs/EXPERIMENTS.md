# Thực nghiệm

Cấu hình, bộ truy vấn, môi trường đo và phân tích kết quả. Thiết kế: [TOPIC.md](TOPIC.md) mục 18, [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md).
Mọi số dưới đây truy ngược được bằng `run_id` trong `results/`. Bảng sinh bằng `python scripts/summarize_results.py results/<run_id>` (T65); phần diễn giải được viết tách riêng khỏi số đo.

## E2 — A* vs Dijkstra trên vùng demo (RQ1)

**Nguồn chính thức:** run_id `20261031-1556-demo-054f300` (T60, #92) · dataset `hcm-benthanh-r2000-20261024` (1.889 node, 4.004 cạnh) · 1.000 cặp phân tầng theo δ = khoảng cách thẳng / L (333 ngắn, 334 trung bình, 333 dài), seed 42 · 20 truy vấn warm-up, mỗi cặp lặp 5 lần, lấy median · Python 3.11.9, Windows 11, Intel 16 GB (máy Duy Anh) · git `054f300`, không dirty.

| Thuật toán | Tầng | Median ms | p95 ms | Median expanded | Khớp chi phí |
|---|---|---:|---:|---:|---|
| Dijkstra | ngắn (δ<0,2) | 0,212 | 1,224 | 110 | — |
| Dijkstra | trung bình | 1,003 | 4,870 | 597,5 | — |
| Dijkstra | dài (δ≥0,5) | 2,072 | 8,160 | 1.279 | — |
| Dijkstra | tất cả | 0,929 | 5,505 | 578 | — |
| A* | ngắn (δ<0,2) | 0,242 | 1,097 | 41 | 100,0 % |
| A* | trung bình | 0,779 | 5,227 | 202 | 100,0 % |
| A* | dài (δ≥0,5) | 2,001 | 10,120 | 535 | 100,0 % |
| A* | tất cả | 0,763 | 6,290 | 194 | 100,0 % |

Tỉ số theo **từng cặp** rồi mới lấy median (EXPERIMENT_PLAN mục 3.2): `r` = expanded_A* / expanded_Dijkstra, `s` = thời gian Dijkstra / thời gian A* (s > 1 nghĩa là A* nhanh hơn).

| Tầng | Median r | Median s | Số cặp A* chậm hơn (s < 1) |
|---|---:|---:|---:|
| ngắn | 0,376 | 0,91 | 194 / 333 |
| trung bình | 0,348 | 1,22 | 116 / 334 |
| dài | 0,467 | 0,98 | 170 / 333 |
| tất cả | 0,398 | 1,03 | 480 / 1.000 |

**Tính đúng:** 1.000/1.000 cặp A* và Dijkstra cùng chi phí; `reopened = 0` ở mọi truy vấn A* (heuristic consistent trên dữ liệu thật, khớp T22 và T33).

**Kiểm chéo (yêu cầu của T65):** run_id `20261103-crosscheck-demo-minh` · cùng `queries.csv` của run chính thức (`--queries`), cùng tham số · Python 3.14.4, máy Minh · git `6ce33eb`, không dirty.
- 2.000/2.000 dòng (cặp × thuật toán) **trùng chi phí và trùng expanded** với run chính thức; `r` theo tầng giống hệt.
- Máy kiểm chéo chạy nhanh hơn máy chính thức khoảng 1,9 lần (median của tỉ số thời gian **giữa hai máy**, tính trên từng dòng cặp × thuật toán; không phải tỉ số s giữa hai thuật toán), nhưng cùng bậc: median tất cả Dijkstra 0,540 ms, A* 0,410 ms; p95 Dijkstra 1,731 ms, A* 2,087 ms.
- `s` theo tầng: ngắn 0,98 · trung bình 1,26 · dài 1,00 · tất cả 1,07; A* chậm hơn ở 444/1.000 cặp.

### Diễn giải

Các nhận xét dưới đây chỉ dựa trên những gì lặp lại ở **cả hai** run; chỗ hai run khác nhau thì ghi là chưa kết luận.

- **A* mở ít node hơn nhiều:** median chỉ bằng khoảng 40% số node Dijkstra mở (r = 0,398), ổn định ở mọi tầng và giống hệt trên hai máy (expanded là số xác định, không phụ thuộc máy).
- **Nhưng thời gian gần như không giảm:** median s chỉ 1,03–1,07, và ở 44–48% số cặp A* còn chậm hơn Dijkstra. Lợi ích rõ chỉ có ở tầng trung bình (s = 1,22–1,26). Giải thích hợp lý (giả thuyết, chưa đo riêng): mỗi lần đẩy một node vào hàng đợi, A* phải tính haversine (lượng giác), đắt hơn nhiều so với phép cộng của Dijkstra; trên đồ thị 1.889 node, mỗi truy vấn chỉ khoảng 1 ms, nên chi phí này ăn gần hết phần tiết kiệm từ việc mở ít node.
- **Đuôi chậm của A* là thật:** p95 của A* cao hơn Dijkstra ở cả hai run (6,29 so với 5,51 ms; 2,09 so với 1,73 ms), rõ nhất ở tầng dài (10,12 so với 8,16 ms).
- **Chưa kết luận:** median s của tầng ngắn và tầng dài dao động quanh 1 (0,91–1,00) giữa các run. Ở mức khoảng 0,1 ms mỗi truy vấn, sai số đo đủ để đổi chiều, nên không nói A* nhanh hay chậm hơn ở hai tầng này.
- **Trường hợp A* không có lợi:** (1) truy vấn trên vùng nhỏ, nơi chi phí tính heuristic lớn hơn phần tiết kiệm; (2) khi không có đường đi, A* vẫn phải duyệt hết vùng tới được như Dijkstra nên không còn lợi thế (kiểm ở E4 khi có run kịch bản đóng đường, T63).

## E3 — Đồ thị cho thí nghiệm tăng quy mô (T61)

Cắt bằng `python scripts/make_crops.py` từ `outer.graphml` đã đóng băng (Release `data-raw-20261024`, sha256 `24a28327…`, tải 24/10/2026), tâm chợ Bến Thành. Giữ node trong hình vuông đo bằng mét trên UTM 48N (EPSG:32648), giữ cạnh có cả hai đầu bên trong. SCC chọn lồng nhau (DATA_MODEL mục 8.4): SCC của vùng nhỏ nằm trọn trong SCC của vùng lớn, đã kiểm trong script và trong `tests/test_crops.py`. Chi tiết và sha256 đầy đủ: `data/processed/crop_manifest.json` (commit). Các file `crop_r*.json` không có trên Git; người chạy T62 tải `outer.graphml` từ Release (ONBOARDING mục 3), chạy `python scripts/make_crops.py` (cần OSMnx) rồi so 4 sha256 với manifest. Thời gian pilot của lần chạy gần nhất ghi ở `data/processed/crop_pilot.json` (không commit, vì đổi theo máy và mỗi lần chạy).

| Nửa cạnh | `dataset_id` | \|V\| | \|E\| | SCC (node) | Cạnh một chiều | sha256 |
|---:|---|---:|---:|---:|---:|---|
| 1 km | `crop_r1000_20261024` | 565 | 1.133 | 528 | 579 | `7af3acfb9aa7…` |
| 2 km | `crop_r2000_20261024` | 1.889 | 4.004 | 1.745 | 1.332 | `8c33ec4291eb…` |
| 3 km | `crop_r3000_20261024` | 4.411 | 9.613 | 4.020 | 2.369 | `e1aed60ffd5c…` |
| 4,5 km | `crop_r4500_20261024` | 10.143 | 22.953 | 9.450 | 4.205 | `b3ad87e2635b…` |

- Vùng 2 km trùng hoàn toàn đồ thị demo của T31 (`hcm-benthanh-r2000-20261024`), chỉ khác `dataset_id`.
- Từ 1 km lên 4,5 km, nửa cạnh tăng 4,5 lần (diện tích ~20 lần) nhưng \|V\| tăng ~18 lần. Vì vậy trục hoành các biểu đồ dùng \|V\| đo được, không dùng bán kính.

**Pilot (kiểm tính khả thi, không phải benchmark):** 20 truy vấn dài nhất trong 1.000 cặp ngẫu nhiên thuộc SCC của vùng 4,5 km (seed 42, khoảng cách thẳng ≥ 9.054 m), Dijkstra trên kịch bản cơ sở: median 13–25 ms qua 4 lần chạy trên cùng máy (dao động theo tải máy), lớn nhất < 30 ms, median 8.890 node mở rộng. Ngưỡng bỏ kích thước là median > ~1 s, nên cả 4 kích thước ứng viên đều dùng được. Máy đo: laptop Windows 11 của Minh, Python 3.14.4; benchmark chính thức (T62) chạy trên Python 3.11.

**Đã chốt (Q3, 28/10):** giữ cả **4 kích thước 1 / 2 / 3 / 4,5 km** cho E3. Pilot cho thấy vùng lớn nhất chỉ 13–25 ms/truy vấn và script đã cắt sẵn cả 4, nên thêm một điểm trên biểu đồ gần như không tốn thêm thời gian chạy.

**Còn thiếu:** E3 (tăng quy mô, chờ T62 chạy trên 4 vùng của T61), E4 (ùn tắc và đóng đường, chờ T63), E5 (tour, T74).
