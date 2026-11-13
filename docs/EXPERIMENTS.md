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
- **Đuôi chậm của A*: thấy ở cả hai run.** p95 của A* cao hơn Dijkstra ở cả hai run (6,29 so với 5,51 ms; 2,09 so với 1,73 ms), rõ nhất ở tầng dài (10,12 so với 8,16 ms). Hai run khác cả máy lẫn phiên bản Python và mới chỉ có hai run, nên đây là quan sát lặp lại, chưa phải kết luận; nguyên nhân chưa được đo tách.
- **Chưa kết luận:** median s của tầng ngắn và tầng dài dao động quanh 1 (0,91–1,00) giữa các run. Ở mức khoảng 0,1 ms mỗi truy vấn, sai số đo đủ để đổi chiều, nên không nói A* nhanh hay chậm hơn ở hai tầng này.
- **Trường hợp A* không có lợi:** (1) truy vấn trên vùng nhỏ, nơi chi phí tính heuristic lớn hơn phần tiết kiệm; (2) khi không có đường đi, A* vẫn phải duyệt hết vùng tới được như Dijkstra nên không còn lợi thế (đã đo ở E4, bộ C4: cùng số node mở rộng ở 30/30 cặp, A* chậm hơn).

## E2b — Mở rộng: Dijkstra, Dijkstra hai chiều, A*, ALT (D17)

Ngoài phạm vi proposal (ALT là mở rộng tùy chọn; Dijkstra hai chiều có trong danh sách gợi ý của đề bài). Ghi để trả lời câu hỏi "heuristic mạnh hơn có giúp không", không thay cho E2.

**Run:** `20261113-1327-compare-871bf02` (thư mục `results/20261113-1327-compare-871bf02/`, #121) · `scripts/compare_algorithms.py` · commit `871bf02`, `git_dirty: false` · Python 3.11.9, Windows, Intel Family 6 Model 186 (máy khác máy đo E3–E5) · đồ thị demo `hcm-benthanh-r2000-20261024` (sha256 `928c1f8b…`, 1.889 node) và `hcm-benthanh-r4500-20261024` (sha256 `7cb46484…`, 10.143 node, 22.953 cạnh; dựng bằng `prepare_data.py build --area demo-large` (#116) từ cùng Release dữ liệu thô, cùng kích thước với vùng 4,5 km của E3 nhưng là file khác) · 500 cặp mỗi đồ thị (seed 20261113, phân tầng theo δ = khoảng cách thẳng / cạnh vùng), warm-up 20, lặp 5 lấy median, mỗi cặp đo cả `baseline` và `peak-center` xen kẽ · ALT dùng 8 landmark; thời gian truy vấn **không** gồm tiền xử lý landmark.

**Khác E3:** cặp được sinh **riêng cho từng đồ thị**, nên tầng "dài" ở vùng 4,5 km là chuyến đi dài hơn thật. Bảng này vì vậy trộn hai yếu tố (bản đồ lớn hơn và chuyến đi dài hơn), không so trực tiếp với E3 (fixed trips).

**Kiểm tính đúng:** 2.000/2.000 nhóm (cặp × đồ thị × kịch bản) có 4 thuật toán cùng chi phí (sai số 1e-6); không có cặp `no_path`.

Kịch bản `baseline`. Thời gian là median ms trên các cặp; s = thời gian Dijkstra / thời gian thuật toán đó, tính **theo từng cặp** rồi lấy median (s > 1 là nhanh hơn Dijkstra).

| Đồ thị | Tầng | Dijkstra ms | Hai chiều ms (s) | A* ms (s) | ALT ms (s) | Median expanded D / hai chiều / A* / ALT |
|---|---|---:|---:|---:|---:|---|
| 2 km | ngắn | 0,110 | 0,104 (0,96) | 0,101 (0,99) | 0,236 (0,39) | 118 / 67,5 / 43 / 18 |
| 2 km | trung bình | 0,679 | 0,523 (1,31) | 0,515 (1,42) | 0,443 (1,45) | 624 / 349 / 219 / 62 |
| 2 km | dài | 1,285 | 1,288 (1,06) | 1,198 (1,06) | 0,626 (1,94) | 1.337 / 837 / 548 / 119 |
| 4,5 km | ngắn | 0,736 | 0,492 (1,40) | 0,506 (1,43) | 1,618 (0,44) | 631 / 277 / 198 / 65 |
| 4,5 km | trung bình | 4,092 | 2,540 (1,55) | 1,961 (1,94) | 2,255 (1,80) | 2.754 / 1.321 / 786 / 196 |
| 4,5 km | dài | 11,182 | 10,130 (1,12) | 8,048 (1,27) | 3,942 (2,67) | 6.912 / 4.355 / 2.665 / 616 |

Tiền xử lý ALT: 29,7 ms và 0,24 MB (2 km); 365,9 ms và 1,30 MB (4,5 km). Dưới `peak-center`, thứ tự số node mở rộng giữ nguyên (ALT < A* < hai chiều < Dijkstra ở mọi ô); thời gian xem `summary.csv` (có ô A* chậm hơn Dijkstra, ví dụ 2 km tầng dài 1,362 so với 1,169 ms).

**Diễn giải (không phải số đo):**

- Số node mở rộng giảm theo thứ tự Dijkstra > hai chiều > A* > ALT ở mọi ô. Hai chiều giảm nhờ tìm từ cả hai đầu (không dùng heuristic); A* và ALT giảm nhờ heuristic, và heuristic landmark của ALT trên các cặp này chặt hơn heuristic địa lý của A* (thấy qua số node; không đúng cho mọi cặp nút).
- Ít node hơn chưa chắc nhanh hơn: thời gian chỉ giảm khi phần tiết kiệm lớn hơn chi phí thêm cho mỗi node. Ở tầng ngắn, ALT **chậm hơn** Dijkstra khoảng 2,3–2,6 lần (s = 0,44 và 0,39) dù mở ít node nhất.
- Trên vùng 2 km (cùng kích thước vùng của E2), tầng dài: A* s = 1,06, gần như không nhanh hơn, khớp với E2; ALT s = 1,94. Lợi lớn nhất của ALT là ở vùng 4,5 km, tầng dài (s = 2,67; A* ở đó s = 1,27). Đây là một run trên một máy; không suy ra cho đồ thị khác.
- Kết luận cho essay: số node mở rộng và thời gian truy vấn là hai thước đo khác nhau; chọn thuật toán phụ thuộc độ dài chuyến đi và việc có chấp nhận tiền xử lý hay không.

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
| `baseline` | — | — | 585,5 | 189 | 0,403 |
| `peak-center` | 56/300 (18,7%) | 0,0% / 15,7% | 584,5 | 199,5 | 0,422 |
| `peak-ben-thanh` | 47/300 (15,7%) | 0,0% / 10,6% | 589 | 195,5 | 0,413 |

### Đóng đoạn giữa tuyến (C3): 100 cặp có tuyến cơ sở ≥ 3 cạnh

p90 tính bằng nội suy tuyến tính giữa hai giá trị kề (như mặc định của `numpy.percentile`). Còn đường 100/100. Chi phí tăng median 4,3%, p90 21,9%. Thời gian lập lại tách hai phần: dựng snapshot median 0,451 ms; tìm lại median 0,785 ms (Dijkstra), 0,640 ms (A*).

### Không còn đường (C4): 30 cặp, đóng mọi cạnh đi vào đích

Bộ này cô lập đích **có chủ ý** để kiểm hành vi khi không có đường; nó không ước lượng khả năng mất đường khi đóng đường ngoài thực tế. Cả hai thuật toán `no_path` ở 30/30 cặp, cùng median 1.763 node mở rộng (toàn bộ phần đồ thị tới được). Thời gian kết luận `no_path`: median 1,53 ms (Dijkstra), 3,40 ms (A*).

Hình: `fig_e4_ratio_by_scenario.png` trong thư mục run.

**Diễn giải (không phải số đo):**

- **H3: có tín hiệu cùng chiều nhưng nhỏ.** Median `r` toàn bộ tăng từ 0,403 lên 0,422 (`peak-center`) và 0,413 (`peak-ben-thanh`). Tách theo cặp: ở cặp có đổi chi phí, Δr = r(kịch bản) − r(cơ sở) median +0,023 (IQR +0,002 – +0,066; 105 cặp, `peak-center`) và +0,024 (IQR −0,008 – +0,065; 60 cặp, `peak-ben-thanh`); ở cặp không đổi chi phí, median Δr là 0 nhưng vẫn có 119/195 và 154/240 cặp Δr khác 0 (−0,12 đến +0,21), vì trọng số trong vùng đổi làm thứ tự mở node đổi. Lý do dự kiến (heuristic dùng `v_max` cơ sở nên cận dưới lỏng hơn) chưa được tách riêng để kiểm.
- Ùn tắc đổi tuyến ở 16–19% số cặp, nhưng chỉ cặp nào đi qua vùng mới bị ảnh hưởng: median tăng chi phí 0%, p90 10–16%.
- **Không còn đường: A* không có lợi thế.** Hai thuật toán mở đúng cùng số node ở 30/30 cặp (cả hai phải duyệt hết phần tới được, DATA_MODEL mục 7). Theo từng cặp, thời gian A*/Dijkstra median 2,15 (IQR 1,95 – 2,43). Nguyên nhân có thể do A* tốn thêm chi phí tính heuristic cho từng node mà không thu lại được gì; chưa đo tách.
- Trên đồ thị demo, khi đóng **một** đoạn giữa tuyến (kèm cạnh đối), 100/100 cặp vẫn còn đường vòng, nhưng một phần cặp phải đi vòng xa (p90 +21,9%). Không suy ra cho việc đóng nhiều đoạn hay cho vùng thưa đường hơn.

## E5 — Kết quả: tour (T74)

**Run:** `20261113-0448-tour-12dd1e0` (n = 4, 6, 8, 10; lệnh `python scripts/run_benchmarks.py --suite tour --graph data/processed/hcm-benthanh-r2000-20261024.json --seed 42`; commit `12dd1e0`) và `20261114-0517-tour-04a0d7e` (n = 5, thêm ở R2 để có cùng cỡ với case demo; lệnh `python scripts/run_tour.py --graph data/processed/hcm-benthanh-r2000-20261024.json --sizes 5 --sets 20 --seed 42`; commit `04a0d7e`) · cả hai `git_dirty: false` · đồ thị demo (sha256 `928c1f8b…`), kịch bản cơ sở · máy: laptop Windows 11 của Tiến, Python 3.11.9.

**Cách đo:** n ∈ {4, 5, 6, 8, 10} điểm giao × 20 bộ (seed 42); kho và điểm giao lấy ngẫu nhiên trong SCC, mọi cặp điểm cách nhau ≥ 150 m; thứ tự nhập = thứ tự sinh. Ma trận chi phí dựng từ đồ thị bằng đúng hàm của `/api/tour` (`services/tour.cost_matrix`). Bảng dưới do `python scripts/summarize_results.py results/20261113-0448-tour-12dd1e0 results/20261114-0517-tour-04a0d7e` sinh ra.

**Kiểm tính đúng (đạt hết):** 100/100 bộ khả thi; mọi bộ có Held–Karp ≤ NN + 2-opt ≤ NN; bộ "Kho + 5 điểm giao" của T55 chạy qua cùng hàm ra 1.066,0 / 1.003,3 / 898,1 / 627,8 s, khớp `/api/tour` (test `realdata`).

| Điểm giao | Phương án | Median Improvement % | IQR Improvement % | Median Gap % | IQR Gap % | p90 Gap % | Max Gap % | Median thời gian sắp thứ tự (ms) | Bộ khả thi |
|---|---|---|---|---|---|---|---|---|---|
| 4 | thứ tự nhập | — | — | 13,17 | [6,34; 26,45] | 37,5 | 58,23 | 0 | 20/20 |
| 4 | NN | 9,53 | [3,89; 20,9] | 1,7 | [0; 6,69] | 11,39 | 14,53 | 0,007 | 20/20 |
| 4 | NN + 2-opt | 11,58 | [5,96; 20,9] | 0 | [0; 0,07] | 3,39 | 11,31 | 0,022 | 20/20 |
| 4 | Held–Karp | — | — | — | — | — | — | 0,019 | 20/20 |
| 5 | thứ tự nhập | — | — | 35,3 | [30,39; 41,31] | 52,86 | 64,04 | 0 | 20/20 |
| 5 | NN | 21,22 | [10,2; 25,07] | 6,63 | [1,24; 16,37] | 20,83 | 21,39 | 0,009 | 20/20 |
| 5 | NN + 2-opt | 25,41 | [19,99; 27,49] | 0 | [0; 0,48] | 7,36 | 12,22 | 0,033 | 20/20 |
| 5 | Held–Karp | — | — | — | — | — | — | 0,044 | 20/20 |
| 6 | thứ tự nhập | — | — | 39,05 | [30,99; 54,7] | 61,16 | 64,12 | 0 | 20/20 |
| 6 | NN | 24,57 | [16,46; 29,28] | 8,08 | [3,35; 12,91] | 16,54 | 24,53 | 0,01 | 20/20 |
| 6 | NN + 2-opt | 27,84 | [23,63; 35,17] | 0 | [0; 0,71] | 1,64 | 13,85 | 0,046 | 20/20 |
| 6 | Held–Karp | — | — | — | — | — | — | 0,106 | 20/20 |
| 8 | thứ tự nhập | — | — | 57,53 | [45,05; 70,57] | 93,78 | 131,45 | 0 | 20/20 |
| 8 | NN | 30,03 | [23,74; 35,44] | 9,27 | [6,6; 13,3] | 19,95 | 24,63 | 0,014 | 20/20 |
| 8 | NN + 2-opt | 36,4 | [29,51; 40,45] | 0,19 | [0; 3,88] | 5,89 | 13,52 | 0,082 | 20/20 |
| 8 | Held–Karp | — | — | — | — | — | — | 0,616 | 20/20 |
| 10 | thứ tự nhập | — | — | 71,62 | [61,99; 81,83] | 89,6 | 136,76 | 0 | 20/20 |
| 10 | NN | 32,37 | [28,59; 39,39] | 14,09 | [7,96; 20,25] | 23,05 | 34,51 | 0,022 | 20/20 |
| 10 | NN + 2-opt | 41,04 | [36,79; 42,46] | 1,76 | [0; 5,06] | 8,61 | 14,07 | 0,147 | 20/20 |
| 10 | Held–Karp | — | — | — | — | — | — | 3,814 | 20/20 |

Dựng ma trận (một lần mỗi bộ): median 2,79 / 4,67 / 6,29 / 7,78 ms với n = 4 / 6 / 8 / 10; n = 5 (run sau, cùng máy) 3,84 ms. NN + 2-opt trùng tối ưu ở 45/80 bộ của run đầu. Hình: `fig_e5_tour.png` trong thư mục run đầu (chỉ có n = 4, 6, 8, 10; chưa vẽ lại với n = 5).

**Diễn giải (không phải số đo):**

- Sắp lại thứ tự có lợi rõ và lợi càng lớn khi nhiều điểm: NN + 2-opt rẻ hơn thứ tự nhập median 11,6% (n = 4) đến 41,0% (n = 10). Phần 2-opt cải thiện thêm so với NN, tính trên **từng bộ** (Improvement của NN + 2-opt trừ Improvement của NN cùng bộ) rồi lấy median: 0,36 / 4,56 / 4,40 / 4,87 / 6,01 điểm phần trăm với n = 4 / 5 / 6 / 8 / 10. (Hiệu giữa hai median trong bảng là 2,05 / 3,27 / 6,37 / 8,67 điểm, lớn hơn vì median của hiệu khác hiệu của median.) Thứ tự nhập ở đây là thứ tự sinh ngẫu nhiên, nên Improvement đo so với một thứ tự ngẫu nhiên, không phải so với cách người điều phối thật xếp tuyến.
- NN + 2-opt gần tối ưu: median gap 0–1,8%, p75 ≤ 5,1%. NN một mình kém hơn hẳn (median gap 1,7–14,1%).
- Thời gian: dựng ma trận (vài ms, n + 1 lần Dijkstra một-nguồn-nhiều-đích) gấp khoảng 128 lần (n = 4) đến 53 lần (n = 10) thời gian sắp thứ tự bằng NN + 2-opt (dưới 0,15 ms). Held–Karp tăng nhanh theo n (median 0,019 → 0,106 → 0,616 → 3,814 ms), cùng chiều với độ phức tạp lý thuyết O(2ⁿ·n²). Mỗi phương án chỉ đo một lần mỗi bộ, theo thứ tự cố định, không warm-up riêng, nên bốn điểm đo này không đủ để xác nhận bậc tăng; chỉ dùng chúng để nói Held–Karp đắt dần và vì vậy chỉ làm đối chứng tới 10 điểm giao.
- **Case demo không đại diện được bằng E5:** ở bộ "Kho + 5 điểm giao" của T55, NN + 2-opt kém tối ưu 43% (tối ưu là tour NN đi ngược chiều; 2-opt nhận nước cải thiện đầu tiên nên kẹt cực trị địa phương trên ma trận bất đối xứng; Minh thấy từ 31/10). Trong 20 bộ ngẫu nhiên cùng cỡ (n = 5, thêm ở R2), gap lớn nhất của NN + 2-opt chỉ 12,2% (p90 7,4%); trong cả 100 bộ (n = 4–10) lớn nhất là 14,1%. Vậy gap lớn như case demo không gặp trong 100 bộ ngẫu nhiên; case demo dùng để giải thích cực trị địa phương, không đại diện cho mức gap thường gặp. #122 thêm Or-opt (tùy chọn) và tìm được tối ưu ở case demo; **Or-opt chỉ dùng minh họa**: không nằm trong các phương án đo ở E5, nên không có số đo tổng quát nào về nó.

## E5b — Tour sau khi đóng đường: giữ thứ tự cũ so với sắp lại (R2)

Câu hỏi của proposal (slide 12): khi một đoạn đường trên tuyến bị đóng, nên đi tiếp đúng thứ tự cũ hay sắp lại thứ tự? Báo riêng hai phương án để thuật toán tìm đường không được tính công của việc sắp lại.

**Run:** `20261114-0517-tourclosure-04a0d7e` (thư mục `results/20261114-0517-tourclosure-04a0d7e/`) · lệnh `python scripts/run_tour_closure.py --graph data/processed/hcm-benthanh-r2000-20261024.json --sizes 5 --sets 20 --seed 42` · commit `04a0d7e`, `git_dirty: false` · đồ thị demo, kịch bản cơ sở · cùng máy với E5.

**Cách đo:** đúng 20 bộ n = 5 của run E5 n = 5 (cùng hàm sinh bộ, cùng seed). Mỗi bộ: tour cũ = phương án `/api/tour` chọn trên kịch bản cơ sở (`choose_tour`); đóng cạnh ở vị trí ⌊k/2⌋ trên tuyến của tour cũ, kèm cạnh đối nếu có (như "đóng đoạn" trên UI; 6/20 bộ có cạnh đối); trên snapshot mới tính **giữ thứ tự cũ** (cùng thứ tự, mỗi chặng tìm lại) và **sắp lại** (`choose_tour` lại). Không đo thời gian.

**Kiểm tính đúng (đạt hết):** giữ thứ tự cũ không rẻ hơn tour cũ ở mọi bộ; không tuyến nào đi qua cạnh đóng (kiểm trong script, không có `violations.json`).

| Chỉ số (20 bộ) | Kết quả |
|---|---|
| Bộ không còn tour khép kín sau khi đóng | 2/20 (có chặng không đi được sau khi đóng; cạnh đóng 2060 ở bộ 3, 1725 + 1707 ở bộ 10) |
| Giữ thứ tự cũ: chi phí tăng so với tour cũ (18 bộ còn khả thi) | median 1,42%, p90 4,04%, lớn nhất 13,66% |
| Sắp lại so với giữ thứ tự cũ | rẻ hơn ở 3/18 bộ, bằng ở 15/18, không bộ nào đắt hơn (quan sát trong mẫu này; `choose_tour` sau khi đóng không xét thứ tự cũ nên không bảo đảm điều này) |
| Phần sắp lại rẻ hơn giữ thứ tự cũ, `100·(C_giữ − C_sắp)/C_giữ` | median 0%, p90 2,53%, lớn nhất 7,25% |
| Sắp lại rẻ hơn cả tour cũ (trước khi đóng) | 1/18 bộ |

p90 nội suy tuyến tính như các bảng khác.

**Diễn giải (không phải số đo):**

- Đóng **một** đoạn giữa tuyến thường chỉ làm tour dài thêm ít (median 1,4%), có thể vì mạng đường trung tâm dày, có đường vòng gần (chưa kiểm); nhưng 2/20 bộ mất hẳn tour khép kín, nên hệ thống phải báo được "không còn tour đầy đủ" (R1) thay vì vẽ tour thiếu điểm.
- Sắp lại hiếm khi đổi thứ tự (3/18) và lợi tối đa 7,3% trong mẫu này. Case demo của DEMO bước 10 (đóng cạnh 1666: giữ thứ tự cũ 962,7 s, sắp lại 692,5 s, chênh 28%) nằm ngoài khoảng quan sát được ở đây; nó được chọn có chủ ý để minh họa và lợi lớn chủ yếu vì tour cũ của case đó là cực trị địa phương kém (gap 43%, xem E5), không phải vì đóng đường. Khi trình bày phải nói rõ.
- Chỉ một cách đóng (một đoạn giữa tuyến), một cỡ n và 20 bộ; không suy ra cho đóng nhiều đoạn, cho n lớn hơn, hay cho vùng thưa đường.
