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

## E3 — Kết quả: tăng quy mô, fixed trips (T62)

**Run:** `20261113-0438-scaling-cb16bc0` (thư mục `results/20261113-0438-scaling-cb16bc0/`) · lệnh `python scripts/run_scaling.py --pairs 250 --seed 42 --repeats 5 --warmup 20` · commit `cb16bc0`, `git_dirty: false` · máy: laptop Windows 11 của Tiến, Intel (Family 6 Model 197), RAM 31,4 GB, Python 3.11.9 · 4 vùng đúng sha256 trong `crop_manifest.json`.

**Cách đo:** 250 cặp sinh trong SCC vùng 1 km (seed 42, phân tầng ngắn / trung bình / dài = 83 / 84 / 83), dùng **y hệt** trên cả 4 vùng: mỗi vùng đánh số node lại nên cặp được đổi qua `osmid`. Quy trình đo mục 3.1 (warm-up 20, lặp 5, lấy median, đảo thứ tự thuật toán theo cặp). Thời gian nạp đồ thị và bộ nhớ đỉnh đo riêng (`load.csv`, bộ nhớ bằng `tracemalloc`).

**Kiểm tính đúng (đạt hết):** 2.000 dòng, mọi dòng `ok`; chi phí Dijkstra = A* ở mọi cặp, mọi vùng; 0 lệch `osmid`; chi phí của mỗi cặp **không tăng** khi vùng lớn dần (vùng lớn chứa mọi cạnh của vùng nhỏ); chạy lại với seed 42 ra `queries.csv` cùng nội dung (sha256 `d37a0eda…` cho file trong repo, xuống dòng LF; `f1d8e20f…` là bản CRLF lúc chạy trên Windows).

| Vùng | \|V\| | median expanded Dijkstra | median expanded A* | median r = A*/Dijkstra | median thời gian Dijkstra (ms) | median thời gian A* (ms) | Nạp đồ thị (ms) | Bộ nhớ đỉnh khi nạp (MB) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 km | 565 | 186 | 60 | 0,448 | 0,101 | 0,085 | 4,5 | 1,7 |
| 2 km | 1.889 | 236 | 66 | 0,327 | 0,142 | 0,110 | 26,1 | 6,3 |
| 3 km | 4.411 | 236 | 66 | 0,316 | 0,176 | 0,137 | 67,3 | 15,3 |
| 4,5 km | 10.143 | 236 | 66 | 0,316 | 0,200 | 0,138 | 303,4 | 35,3 |

Cặp có chi phí **giảm** khi vùng lớn hơn: 48/250 (19,2%) từ 1 km lên 2 km, và vẫn đúng 48/250 từ 1 km lên 4,5 km (không cặp nào giảm thêm sau 2 km). Hình: `fig_e3_expanded_runtime.png`, `fig_e3_ratio_by_size.png` trong thư mục run (chú thích hình ghi "số cặp: 1000" là 250 cặp × 4 vùng).

**Diễn giải (không phải số đo):**

- **H2 đúng ở median, không đúng với từng cặp:** từ 2 km trở lên, median `expanded` đứng yên (235,5 và 65,5; bảng làm tròn thành 236 và 66). A* mở y hệt ở mọi cặp giữa 2 km và 4,5 km (0/250 cặp khác), nhưng Dijkstra khác ở 65/250 cặp (lệch lớn nhất +2.160 node; `expanded` lớn nhất 1.310 → 2.554 → 3.459) dù không cặp nào đổi chi phí sau 2 km: một số cặp Dijkstra vẫn lan sang vùng ngoài. Bước nhảy 1 km → 2 km đi cùng 48 cặp tìm được đường vòng mới qua vùng ngoài (chi phí giảm).
- **Thời gian vẫn tăng dù median `expanded` không đổi:** từ 2 km lên 4,5 km, Dijkstra ×1,41 (0,142 → 0,200 ms), A* ×1,25 (0,110 → 0,138 ms). Một phần giải thích được: mỗi truy vấn khởi tạo hai mảng dài \|V\| (`g`, `pred_edge`). Đo riêng trên cùng máy bằng `python -c "import timeit, math; n = 10143; print(min(timeit.repeat(lambda: ([math.inf] * n, [-1] * n), number=2000, repeat=5)) / 2000 * 1e6)"` (đổi `n` theo vùng, kết quả là µs), hai mảng này tốn ~1,6 µs ở 2 km; ở 4,5 km số đo dao động 9–32 µs giữa các lần chạy (máy Tiến và máy Minh), nên chỉ ước lượng được là khoảng 15–55% của ~58 µs chênh của Dijkstra. Phần còn lại **chưa đo được nguyên nhân** (có thể do bộ nhớ đệm khi dữ liệu đồ thị lớn hơn); không kết luận thêm.
- Lợi thế của A* lớn hơn từ 2 km trở lên (median `r` 0,448 ở 1 km, 0,327 ở 2 km, 0,316 ở 3 và 4,5 km). `r` giảm ở cả 48 cặp có đổi chi phí (0,530 → 0,346) lẫn 202 cặp còn lại (0,412 → 0,323), nên không chỉ do đường vòng mới. Giải thích khả dĩ, chưa kiểm: hiệu ứng biên của vùng 1 km (cặp gần mép vùng nhỏ bị chặn bởi mép, làm Dijkstra mở ít hơn). Vì vậy số ở vùng 1 km nên đọc thận trọng.
- Chỉ kết luận cho fixed trips (bản đồ lớn hơn, chuyến đi giữ nguyên); growing trips đã cắt (D11).
- **Hạn chế:** số của vùng 1 km có thể chịu hiệu ứng biên (xem trên); số đo khởi tạo mảng là ước lượng có dao động lớn; thời gian đo trên một máy.

## E4 — Kết quả: ùn tắc và đóng đường (T63)

**Run:** `20261113-0444-scenario-c1cd80b` (thư mục `results/20261113-0444-scenario-c1cd80b/`) · lệnh `python scripts/run_scenarios.py --seed 42` (mặc định 300 cặp, 100 cặp đóng đoạn, 30 cặp không còn đường, lặp 5, warm-up 20) · commit `c1cd80b`, `git_dirty: false` · đồ thị demo `hcm-benthanh-r2000-20261024` (sha256 `928c1f8b…`) · kịch bản `data/config/scenarios.json` · máy: laptop Windows 11 của Tiến, Python 3.11.9.

**Kiểm tính đúng (đạt hết):** 2.060 dòng; mọi cặp C1 `ok` dưới cả 3 kịch bản, chi phí dưới ùn tắc không bao giờ thấp hơn cơ sở; C3: tuyến mới không đi qua cạnh đóng, chi phí không giảm; C4: 30/30 cặp `no_path` ở cả hai thuật toán; Dijkstra = A* mọi dòng `ok`. Case T55 (Dinh Độc Lập → Bitexco) qua cùng `measure_query` (test `test_t55_case_under_peak_center_through_measure_query`, cần đồ thị thật): cơ sở 186,1 s, `peak-center` 246,1 s, tuyến khác nhau (`route_sig` `33e05fd35114` → `96e43150f51f`).

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

- **H3: có tín hiệu cùng chiều nhưng nhỏ.** Median `r` toàn bộ tăng từ 0,403 lên 0,422 (`peak-center`) và 0,413 (`peak-ben-thanh`). Tách theo cặp: ở cặp có đổi chi phí, Δr = r(kịch bản) − r(cơ sở) median +0,023 (IQR +0,002 – +0,066; 105 cặp, `peak-center`) và +0,024 (IQR −0,008 – +0,065; 60 cặp, `peak-ben-thanh`); ở cặp không đổi chi phí, median Δr là 0 nhưng vẫn có 119/195 và 154/240 cặp Δr khác 0 (−0,12 đến +0,21), vì trọng số trong vùng đổi làm thứ tự mở node đổi. Lý do dự kiến (heuristic dùng `v_max` cơ sở nên cận dưới lỏng hơn) chưa được tách riêng để kiểm.
- Ùn tắc đổi tuyến ở 16–19% số cặp, nhưng chỉ cặp nào đi qua vùng mới bị ảnh hưởng: median tăng chi phí 0%, p90 10–16%.
- **Không còn đường: A* không có lợi thế.** Hai thuật toán mở đúng cùng số node ở 30/30 cặp (cả hai phải duyệt hết phần tới được, DATA_MODEL mục 7). Theo từng cặp, thời gian A*/Dijkstra median 2,15 (IQR 1,95 – 2,43). Nguyên nhân có thể do A* tốn thêm chi phí tính heuristic cho từng node mà không thu lại được gì; chưa đo tách.
- Trên đồ thị demo, khi đóng **một** đoạn giữa tuyến (kèm cạnh đối), 100/100 cặp vẫn còn đường vòng, nhưng một phần cặp phải đi vòng xa (p90 +21,9%). Không suy ra cho việc đóng nhiều đoạn hay cho vùng thưa đường hơn.

## E5 — Kết quả: tour (T74)

**Run:** `20261113-0448-tour-12dd1e0` (thư mục `results/20261113-0448-tour-12dd1e0/`) · lệnh `python scripts/run_benchmarks.py --suite tour --graph data/processed/hcm-benthanh-r2000-20261024.json --seed 42` · commit `12dd1e0`, `git_dirty: false` · đồ thị demo (sha256 `928c1f8b…`), kịch bản cơ sở · máy: laptop Windows 11 của Tiến, Python 3.11.9.

**Cách đo:** n ∈ {4, 6, 8, 10} điểm giao × 20 bộ (seed 42); kho và điểm giao lấy ngẫu nhiên trong SCC, mọi cặp điểm cách nhau ≥ 150 m; thứ tự nhập = thứ tự sinh. Ma trận chi phí dựng từ đồ thị bằng đúng hàm của `/api/tour` (`services/tour.cost_matrix`). Bảng dưới do `python scripts/summarize_results.py results/20261113-0448-tour-12dd1e0` sinh ra.

**Kiểm tính đúng (đạt hết):** 80/80 bộ khả thi; mọi bộ có Held–Karp ≤ NN + 2-opt ≤ NN; bộ "Kho + 5 điểm giao" của T55 chạy qua cùng hàm ra 1.066,0 / 1.003,3 / 898,1 / 627,8 s, khớp `/api/tour` (test `realdata`).

| Điểm giao | Phương án | Median Improvement % | IQR Improvement % | Median Gap % | IQR Gap % | Median thời gian sắp thứ tự (ms) | Bộ khả thi |
|---|---|---|---|---|---|---|---|
| 4 | thứ tự nhập | — | — | 13,17 | [6,34; 26,45] | 0 | 20/20 |
| 4 | NN | 9,53 | [3,89; 20,9] | 1,7 | [0; 6,69] | 0,007 | 20/20 |
| 4 | NN + 2-opt | 11,58 | [5,96; 20,9] | 0 | [0; 0,07] | 0,022 | 20/20 |
| 4 | Held–Karp | — | — | — | — | 0,019 | 20/20 |
| 6 | thứ tự nhập | — | — | 39,05 | [30,99; 54,7] | 0 | 20/20 |
| 6 | NN | 24,57 | [16,46; 29,28] | 8,08 | [3,35; 12,91] | 0,01 | 20/20 |
| 6 | NN + 2-opt | 27,84 | [23,63; 35,17] | 0 | [0; 0,71] | 0,046 | 20/20 |
| 6 | Held–Karp | — | — | — | — | 0,106 | 20/20 |
| 8 | thứ tự nhập | — | — | 57,53 | [45,05; 70,57] | 0 | 20/20 |
| 8 | NN | 30,03 | [23,74; 35,44] | 9,27 | [6,6; 13,3] | 0,014 | 20/20 |
| 8 | NN + 2-opt | 36,4 | [29,51; 40,45] | 0,19 | [0; 3,88] | 0,082 | 20/20 |
| 8 | Held–Karp | — | — | — | — | 0,616 | 20/20 |
| 10 | thứ tự nhập | — | — | 71,62 | [61,99; 81,83] | 0 | 20/20 |
| 10 | NN | 32,37 | [28,59; 39,39] | 14,09 | [7,96; 20,25] | 0,022 | 20/20 |
| 10 | NN + 2-opt | 41,04 | [36,79; 42,46] | 1,76 | [0; 5,06] | 0,147 | 20/20 |
| 10 | Held–Karp | — | — | — | — | 3,814 | 20/20 |

Dựng ma trận (một lần mỗi bộ): median 2,79 / 4,67 / 6,29 / 7,78 ms với n = 4 / 6 / 8 / 10. p90 gap của NN + 2-opt: 3,4 / 1,6 / 5,9 / 8,6% với n = 4 / 6 / 8 / 10. NN + 2-opt trùng tối ưu ở 45/80 bộ; gap lớn nhất của NN + 2-opt là 14,1%, của NN là 34,5%. Hình: `fig_e5_tour.png` trong thư mục run.

**Diễn giải (không phải số đo):**

- Sắp lại thứ tự có lợi rõ và lợi càng lớn khi nhiều điểm: NN + 2-opt rẻ hơn thứ tự nhập median 11,6% (n = 4) đến 41,0% (n = 10). 2-opt thêm 2–9 điểm phần trăm so với NN. Thứ tự nhập ở đây là thứ tự sinh ngẫu nhiên, nên Improvement đo so với một thứ tự ngẫu nhiên, không phải so với cách người điều phối thật xếp tuyến.
- NN + 2-opt gần tối ưu: median gap 0–1,8%, p75 ≤ 5,1%. NN một mình kém hơn hẳn (median gap 1,7–14,1%).
- Thời gian: dựng ma trận (vài ms, n + 1 lần Dijkstra một-nguồn-nhiều-đích) gấp khoảng 128 lần (n = 4) đến 53 lần (n = 10) thời gian sắp thứ tự bằng NN + 2-opt (dưới 0,15 ms). Held–Karp tăng nhanh theo n (0,019 → 0,106 → 0,616 → 3,814 ms): từ 8 lên 10 điểm tăng ×6,2, khớp bậc 2ⁿ·n² (×6,25); ở n nhỏ phần chi phí cố định chiếm nhiều nên tăng chậm hơn lý thuyết (4 → 6 điểm ×5,6 so với ×9). Vì vậy Held–Karp chỉ dùng làm đối chứng tới 10 điểm giao.
- **Case demo không đại diện được bằng E5:** ở bộ "Kho + 5 điểm giao" của T55, NN + 2-opt kém tối ưu 43% (tối ưu là tour NN đi ngược chiều; 2-opt nhận nước cải thiện đầu tiên nên kẹt cực trị địa phương trên ma trận bất đối xứng; Minh thấy từ 31/10). E5 không có bộ 5 điểm giao, nên chỉ nói được: trong 80 bộ ngẫu nhiên (n = 4–10) không gặp gap lớn như vậy; gap lớn nhất của NN + 2-opt là 14,1%, của NN một mình là 34,5%. Sau run này, #122 thêm Or-opt (tùy chọn) và tìm được tối ưu ở case demo; Or-opt không nằm trong 4 phương án đo ở E5.
