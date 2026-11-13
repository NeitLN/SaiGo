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

## E4 — Kết quả: ùn tắc và đóng đường (T63)

**Run:** `20261113-0444-scenario-c1cd80b` (thư mục `results/20261113-0444-scenario-c1cd80b/`) · lệnh `python scripts/run_scenarios.py --seed 42` (mặc định 300 cặp, 100 cặp đóng đoạn, 30 cặp không còn đường, lặp 5, warm-up 20) · commit `c1cd80b`, `git_dirty: false` · đồ thị demo `hcm-benthanh-r2000-20261024` (sha256 `928c1f8b…`) · kịch bản `data/config/scenarios.json` · máy: laptop Windows 11 của Tiến, Python 3.11.9.

**Kiểm tính đúng (đạt hết):** 2.060 dòng; mọi cặp C1 `ok` dưới cả 3 kịch bản, chi phí dưới ùn tắc không bao giờ thấp hơn cơ sở; C3: tuyến mới không đi qua cạnh đóng, chi phí không giảm; C4: 30/30 cặp `no_path` ở cả hai thuật toán; Dijkstra = A* mọi dòng `ok`. Case T55 (Dinh Độc Lập → Bitexco) chạy qua cùng hàm: cơ sở 186,1 s, `peak-center` 246,1 s, tuyến khác nhau (`route_sig` `33e05fd35114` → `96e43150f51f`).

### Ùn tắc (C1): 300 cặp × 3 kịch bản

| Kịch bản | Cặp đổi tuyến | % tăng chi phí (median / p90) | median expanded Dijkstra | median expanded A* | median r = A*/Dijkstra |
|---|---:|---:|---:|---:|---:|
| `baseline` | — | — | 586 | 189 | 0,403 |
| `peak-center` | 56/300 (18,7%) | 0,0% / 15,7% | 584 | 200 | 0,422 |
| `peak-ben-thanh` | 47/300 (15,7%) | 0,0% / 10,6% | 589 | 196 | 0,413 |

### Đóng đoạn giữa tuyến (C3): 100 cặp có tuyến cơ sở ≥ 3 cạnh

p90 tính bằng nội suy tuyến tính giữa hai giá trị kề (như mặc định của `numpy.percentile`). Còn đường 100/100. Chi phí tăng median 4,3%, p90 21,9%. Thời gian lập lại tách hai phần: dựng snapshot median 0,451 ms; tìm lại median 0,785 ms (Dijkstra), 0,640 ms (A*).

### Không còn đường (C4): 30 cặp, đóng mọi cạnh đi vào đích

Cả hai thuật toán `no_path` ở 30/30 cặp, cùng median 1.763 node mở rộng (toàn bộ phần đồ thị tới được). Thời gian kết luận `no_path`: median 1,53 ms (Dijkstra), 3,40 ms (A*).

Hình: `fig_e4_ratio_by_scenario.png` trong thư mục run.

**Diễn giải (không phải số đo):**

- **H3 đúng về chiều, yếu về mức:** dưới ùn tắc, median `r` tăng từ 0,403 lên 0,422 (`peak-center`) và 0,413 (`peak-ben-thanh`), tức A* mất một ít lợi thế. Lý do dự kiến: heuristic dùng `v_max` cơ sở nên cận dưới lỏng hơn khi trọng số trong vùng bị nhân α. Mức tăng nhỏ vì phần lớn cặp không đi qua vùng ùn tắc (median % tăng chi phí là 0).
- Ùn tắc đổi tuyến ở 16–19% số cặp, nhưng chỉ cặp nào đi qua vùng mới bị ảnh hưởng: median tăng chi phí 0%, p90 10–16%.
- **Không còn đường: A* không có lợi thế, còn chậm hơn ~2,2 lần** dù mở đúng cùng số node. Khi không có đường, cả hai phải duyệt hết phần tới được (DATA_MODEL mục 7); A* tốn thêm chi phí tính heuristic cho từng node mà không thu lại được gì.
- Đóng một đoạn giữa tuyến hầu như luôn còn đường vòng trong lõi đô thị dày (100/100), nhưng một phần cặp phải đi vòng xa (p90 +21,9%).
