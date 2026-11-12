# Thực nghiệm

Cấu hình, bộ truy vấn, môi trường đo và phân tích kết quả. Thiết kế: [TOPIC.md](TOPIC.md) mục 18.
Kết quả benchmark đã có: E3 (mục "E3 — Kết quả"). Mục E3 đầu tiên là số đo kích thước đồ thị và pilot kiểm tính khả thi.

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

## E3 — Kết quả: tăng quy mô, fixed trips (T62)

**Run:** `20261113-0438-scaling-cb16bc0` (thư mục `results/20261113-0438-scaling-cb16bc0/`) · lệnh `python scripts/run_scaling.py --pairs 250 --seed 42 --repeats 5 --warmup 20` · commit `cb16bc0`, `git_dirty: false` · máy: laptop Windows 11 của Tiến, Intel (Family 6 Model 197), RAM 31,4 GB, Python 3.11.9 · 4 vùng đúng sha256 trong `crop_manifest.json`.

**Cách đo:** 250 cặp sinh trong SCC vùng 1 km (seed 42, phân tầng ngắn / trung bình / dài = 83 / 84 / 83), dùng **y hệt** trên cả 4 vùng: mỗi vùng đánh số node lại nên cặp được đổi qua `osmid`. Quy trình đo mục 3.1 (warm-up 20, lặp 5, lấy median, đảo thứ tự thuật toán theo cặp). Thời gian nạp đồ thị và bộ nhớ đỉnh đo riêng (`load.csv`, bộ nhớ bằng `tracemalloc`).

**Kiểm tính đúng (đạt hết):** 2.000 dòng, mọi dòng `ok`; chi phí Dijkstra = A* ở mọi cặp, mọi vùng; 0 lệch `osmid`; chi phí của mỗi cặp **không tăng** khi vùng lớn dần (vùng lớn chứa mọi cạnh của vùng nhỏ); chạy lại với seed 42 ra `queries.csv` cùng sha256 (`f1d8e20f…`).

| Vùng | \|V\| | median expanded Dijkstra | median expanded A* | median r = A*/Dijkstra | median thời gian Dijkstra (ms) | median thời gian A* (ms) | Nạp đồ thị (ms) | Bộ nhớ đỉnh khi nạp (MB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 km | 565 | 186 | 60 | 0,448 | 0,101 | 0,085 | 4,5 | 1,7 |
| 2 km | 1.889 | 236 | 66 | 0,327 | 0,142 | 0,110 | 26,1 | 6,3 |
| 3 km | 4.411 | 236 | 66 | 0,316 | 0,176 | 0,137 | 67,3 | 15,3 |
| 4,5 km | 10.143 | 236 | 66 | 0,316 | 0,200 | 0,138 | 303,4 | 35,3 |

Cặp có chi phí **giảm** khi vùng lớn hơn: 48/250 (19,2%) từ 1 km lên 2 km, và vẫn đúng 48/250 từ 1 km lên 4,5 km (không cặp nào giảm thêm sau 2 km). Hình: `fig_e3_expanded_runtime.png`, `fig_e3_ratio_by_size.png` trong thư mục run (chú thích hình ghi "số cặp: 1000" là 250 cặp × 4 vùng).

**Diễn giải (không phải số đo):**

- **H2 đúng với workload này:** từ 2 km trở lên, median `expanded` của cả hai thuật toán đứng yên (236 và 66). Dijkstra chỉ mở các node có chi phí nhỏ hơn chi phí tới đích, nên vùng ngoài xa không được chạm tới. Bước nhảy 1 km → 2 km đi cùng 48 cặp tìm được đường vòng mới qua vùng ngoài (chi phí giảm), tức là phần đồ thị thêm vào thật sự được dùng.
- **Thời gian vẫn tăng khoảng 1,4 lần từ 2 km lên 4,5 km dù `expanded` không đổi.** Một phần giải thích được: mỗi truy vấn khởi tạo hai mảng dài \|V\| (`g`, `pred_edge`); đo riêng trên cùng máy, hai mảng này tốn ~1,6 µs ở 2 km và ~27 µs ở 4,5 km, tức khoảng 25 µs trong ~58 µs chênh của Dijkstra. Phần còn lại **chưa đo được nguyên nhân** (có thể do bộ nhớ đệm khi dữ liệu đồ thị lớn hơn); không kết luận thêm.
- Lợi thế của A* (`r`) lớn hơn ở vùng 2 km trở lên (0,33 → 0,32) so với 1 km (0,45), vì các cặp tìm được đường vòng chủ yếu là cặp dài, nơi heuristic có tác dụng rõ hơn.
- Chỉ kết luận cho fixed trips (bản đồ lớn hơn, chuyến đi giữ nguyên); growing trips đã cắt (D11).
