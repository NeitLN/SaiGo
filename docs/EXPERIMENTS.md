# Thực nghiệm

Cấu hình, bộ truy vấn, môi trường đo và phân tích kết quả. Thiết kế: [TOPIC.md](TOPIC.md) mục 18.
Kết quả benchmark ghi ở các mục "… — Kết quả" bên dưới; mỗi mục kèm `run_id`, lệnh chạy và máy đo. Mục E3 đầu tiên là số đo kích thước đồ thị và pilot kiểm tính khả thi.

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

## E5 — Kết quả: tour (T74)

**Run:** `20261113-0448-tour-12dd1e0` (thư mục `results/20261113-0448-tour-12dd1e0/`) · lệnh `python scripts/run_benchmarks.py --suite tour --graph data/processed/hcm-benthanh-r2000-20261024.json --seed 42` · commit `12dd1e0`, `git_dirty: false` · đồ thị demo (sha256 `928c1f8b…`), kịch bản cơ sở · máy: laptop Windows 11 của Tiến, Python 3.11.9.

**Cách đo:** n ∈ {4, 6, 8, 10} điểm giao × 20 bộ (seed 42); kho và điểm giao lấy ngẫu nhiên trong SCC, mọi cặp điểm cách nhau ≥ 150 m; thứ tự nhập = thứ tự sinh. Ma trận chi phí dựng từ đồ thị bằng đúng hàm của `/api/tour` (`services/tour.cost_matrix`). Bảng dưới do `python scripts/summarize_results.py results/20261113-0448-tour-12dd1e0` sinh ra.

**Kiểm tính đúng (đạt hết):** 80/80 bộ khả thi; mọi bộ có Held–Karp ≤ NN + 2-opt ≤ NN; bộ "Kho + 5 điểm giao" của T55 chạy qua cùng hàm ra 1.066,0 / 1.003,3 / 898,1 / 627,8 s, khớp `/api/tour` (test `realdata`).

| Điểm giao | Phương án | Median Improvement % | IQR Improvement % | Median Gap % | IQR Gap % | Median thời gian sắp thứ tự (ms) |
|---|---|---|---|---|---|---|
| 4 | thứ tự nhập | — | — | 13,17 | [6,34; 26,45] | 0 |
| 4 | NN | 9,53 | [3,89; 20,9] | 1,7 | [0; 6,69] | 0,007 |
| 4 | NN + 2-opt | 11,58 | [5,96; 20,9] | 0 | [0; 0,07] | 0,022 |
| 4 | Held–Karp | — | — | — | — | 0,019 |
| 6 | thứ tự nhập | — | — | 39,05 | [30,99; 54,7] | 0 |
| 6 | NN | 24,57 | [16,46; 29,28] | 8,08 | [3,35; 12,91] | 0,01 |
| 6 | NN + 2-opt | 27,84 | [23,63; 35,17] | 0 | [0; 0,71] | 0,046 |
| 6 | Held–Karp | — | — | — | — | 0,106 |
| 8 | thứ tự nhập | — | — | 57,53 | [45,05; 70,57] | 0 |
| 8 | NN | 30,03 | [23,74; 35,44] | 9,27 | [6,6; 13,3] | 0,014 |
| 8 | NN + 2-opt | 36,4 | [29,51; 40,45] | 0,19 | [0; 3,88] | 0,082 |
| 8 | Held–Karp | — | — | — | — | 0,616 |
| 10 | thứ tự nhập | — | — | 71,62 | [61,99; 81,83] | 0 |
| 10 | NN | 32,37 | [28,59; 39,39] | 14,09 | [7,96; 20,25] | 0,022 |
| 10 | NN + 2-opt | 41,04 | [36,79; 42,46] | 1,76 | [0; 5,06] | 0,147 |
| 10 | Held–Karp | — | — | — | — | 3,814 |

Dựng ma trận (một lần mỗi bộ): median 2,79 / 4,67 / 6,29 / 7,78 ms với n = 4 / 6 / 8 / 10. NN + 2-opt trùng tối ưu ở 45/80 bộ; gap lớn nhất của NN + 2-opt là 14,1%, của NN là 34,5%. Hình: `fig_e5_tour.png` trong thư mục run.

**Diễn giải (không phải số đo):**

- Sắp lại thứ tự có lợi rõ và lợi càng lớn khi nhiều điểm: NN + 2-opt rẻ hơn thứ tự nhập median 11,6% (n = 4) đến 41,0% (n = 10). 2-opt thêm 2–9 điểm phần trăm so với NN. Thứ tự nhập ở đây là thứ tự sinh ngẫu nhiên, nên Improvement đo so với một thứ tự ngẫu nhiên, không phải so với cách người điều phối thật xếp tuyến.
- NN + 2-opt gần tối ưu: median gap 0–1,8%, p75 ≤ 5,1%. NN một mình kém hơn hẳn (median gap 1,7–14,1%).
- Thời gian: dựng ma trận (vài ms, n + 1 lần Dijkstra một-nguồn-nhiều-đích) gấp khoảng 128 lần (n = 4) đến 53 lần (n = 10) thời gian sắp thứ tự bằng NN + 2-opt (dưới 0,15 ms). Held–Karp tăng nhanh theo n (0,019 → 0,106 → 0,616 → 3,814 ms): từ 8 lên 10 điểm tăng ×6,2, khớp bậc 2ⁿ·n² (×6,25); ở n nhỏ phần chi phí cố định chiếm nhiều nên tăng chậm hơn lý thuyết (4 → 6 điểm ×5,6 so với ×9). Vì vậy Held–Karp chỉ dùng làm đối chứng tới 10 điểm giao.
- **Case demo là trường hợp hiếm:** ở bộ "Kho + 5 điểm giao" của T55, NN + 2-opt kém tối ưu 43% (tối ưu là tour NN đi ngược chiều; 2-opt nhận nước cải thiện đầu tiên nên kẹt cực trị địa phương trên ma trận bất đối xứng; Minh thấy từ 31/10). Trên 80 bộ ngẫu nhiên, gap lớn nhất của NN + 2-opt chỉ 14,1%. Sau run này, #122 thêm Or-opt (tùy chọn) và tìm được tối ưu ở case demo; Or-opt không nằm trong 4 phương án đo ở E5. Demo dùng case này để minh họa giới hạn của 2-opt, không để nói 2-opt thường kém như vậy.
