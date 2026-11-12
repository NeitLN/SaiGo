# SaiGo — Roadmap

Lập ngày 23/10/2026. Mốc của giảng viên (tentative, theo Project_Intructions_261.pdf): **12/11 final ready · 19/11 thuyết trình 15 phút · 22/11 nộp ETC**.

> **26/10: đổi phạm vi đã duyệt** ([đề xuất](proposals/2026-10-26-pham-vi.md); D10–D13 ở [PROJECT_BRIEF](PROJECT_BRIEF.md) mục 4): bỏ vẽ toàn mạng đường (T32), RQ1b chỉ fixed trips (4 kích thước, chốt 28/10), **điểm kiểm bằng chứng 05/11** thay cổng G1, **MVP tích hợp 08/11**. Tour bị cắt sáng 26/10 rồi **giữ lại chiều 26/10** khi Duy Anh quay lại (D10). Mục 1–5 dưới đây đã sửa theo; bản trước nằm trong lịch sử git.

Nguyên tắc:

- Mỗi mốc kết thúc bằng **một kết quả chạy được** và một lệnh/thao tác để chứng minh.
- Hai track song song từ ngày đầu, gặp nhau ở M4:
  - **Track A (thuật toán):** đồ thị mẫu tính tay được → Dijkstra → A*.
  - **Track D (dữ liệu):** cài OSMnx trên Windows → tải dữ liệu thật một lần → đóng băng, dùng chung.
- Định dạng đồ thị `saigo-graph/1` ([DATA_MODEL.md](DATA_MODEL.md) mục 2) được chốt ở T01, nên hai track cùng nhắm một định dạng.
- Ngày trong bảng là kế hoạch đã duyệt 26/10. Mỗi mốc chừa thời gian dự phòng, vì cài đặt và gỡ lỗi thường lâu hơn dự kiến.

## 1. Tổng quan

```text
Ngày     23 24 25 26 27 28 29 30 31 01 02 03 04 05 06 07 08 09 10 11 12
Track A  M0 M1 M1 M1 M2 M2 M2 M2 M2 M2 M2 M2
Track D  M0 M3 M3 M3 M3 M3
Skeleton             MW MW MW
Chung                                     M4 M4 M5 M5 M5
Bản đồ                                    M6 M6 M6 M6 M6 M6
Bench                                        M7 M7 M7 M7 M7 M7
Tour     M8(T70, T71 xong 26/10)                     M8 M8 M8
Essay                                     ─────────────────────────────
Mốc                                                  05/11       08/11    12/11
                                                     điểm kiểm   MVP      final
Hoàn thiện                                                          M9 M9 M9 M9
```

Tour (M8): thuật toán trên ma trận đã xong 26/10; T72–T74 (ma trận từ đồ thị, API, UI, benchmark) 05–08/11.

## 2. Các mốc

| Mốc | Thời gian | Kết quả chạy được | Lệnh / cách chứng minh | Task |
|---|---|---|---|---|
| **M0** Nền móng | 23–24/10 (trễ; phần lớn xong 26/10) | Khung chạy trên Windows; fixture `mini.json` nạp được; OSMnx tải được một vùng nhỏ | `pytest -q` xanh; `python scripts/prepare_data.py --smoke` in số node/cạnh | T00–T06 |
| **M1** Dijkstra trên đồ thị mẫu | 24–31/10 | Dijkstra khớp bảng tính tay; CLI in tuyến, chi phí, số node mở rộng cho cả hai thuật toán | `python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo both` → Dijkstra `80 s, expanded 5`; A* `80 s, expanded 2` | T10–T12 |
| **MW** Walking skeleton | 27–29/10 | Bấm 2 điểm trên bản đồ → `/api/route` → Dijkstra trên `mini.json` → vẽ tuyến; chạy được trên máy thứ hai | `pytest tests/test_api_route.py`; thao tác ✅ của T14 trên máy Minh và máy Bảo | T13–T15 |
| **M2** A* + đối chứng | 26/10–03/11 | A* cho cùng chi phí, ít node hơn; test ngẫu nhiên khớp NetworkX; báo cáo heuristic trên dữ liệu thật | `pytest tests/test_astar.py tests/test_oracle_networkx.py -q` xanh; `check-heuristic` (T22) | T20–T22 |
| **M3** Dữ liệu thô đóng băng, dùng chung | 23–28/10 | `outer.graphml` trên Release, hai máy cùng sha256; JSON vùng demo + manifest | `gh release view data-raw-20261024`; `python scripts/prepare_data.py build --area demo`; `pytest -m realdata` | T30, T31, T34 (T32 đã cắt) |
| **M4** Tìm đường trên dữ liệu thật | 02–03/11 | Dijkstra/A* trên đồ thị thật; 200 cặp khớp NetworkX; `c`, `v_max` ghi vào manifest | `pytest -m realdata`; CLI `--from-latlon ... --to-latlon ...` | T33 |
| **M5** Ùn tắc & đóng đường | 02–04/11 | Snapshot với vùng ùn tắc và cạnh đóng; tuyến đổi, `no_path` khi cần | `pytest tests/test_scenario.py tests/test_closures.py -q`; CLI `--scenario peak-center --block 123` | T40–T42 |
| **M6** Bản đồ tương tác (rút gọn) | 02–07/11 | Bấm 2 điểm → tuyến + bảng Dijkstra/A*; chọn kịch bản, vẽ vùng ùn tắc; bấm đoạn trên tuyến để đóng, mở lại; báo không có đường | Checklist UI trong [PROGRESS.md](PROGRESS.md); `pytest tests/test_api_route.py` | T50–T55 |
| **M7** Benchmark & tăng quy mô | 02–08/11 | CSV đo thật + biểu đồ: 1.000 cặp vùng demo, 4 kích thước đồ thị (fixed trips), thí nghiệm ùn tắc/đóng đường | `python scripts/run_benchmarks.py --suite all`; `python scripts/plot_results.py results/<run_id>` | T60–T65 |
| **G1** Điểm kiểm bằng chứng | **05/11** | Biết chắc MVP có kịp 08/11 không; nếu không thì cắt theo thứ tự đã duyệt | Điều kiện ở mục 3 | G1 |
| **MVP** tích hợp | **08/11** | Demo rút gọn chạy trọn ([DEMO.md](DEMO.md)) + bằng chứng thực nghiệm đã chốt | Chạy kịch bản demo; mọi số trong EXPERIMENTS.md có `run_id` | — |
| **M8** Tour (E1) | 26/10 · 05–08/11 | NN, 2-opt có hướng, Held–Karp trên ma trận (xong 26/10); ma trận chi phí từ đồ thị, `/api/tour`, UI kho + 5 điểm, benchmark tour | `pytest tests/test_tour.py`; `python scripts/run_benchmarks.py --suite tour`; bước 9 của demo | T70–T74 |
| **M9** Hoàn thiện | 09–12/11 | Không thêm tính năng; chạy lại trên máy thứ hai theo README; video demo dự phòng; số liệu vào essay. Essay bắt đầu từ 02/11 | Checklist ở T80–T83 | T80–T83 |

Sau 12/11: 13–18/11 làm slide và tập dượt; 19/11 thuyết trình; 20–22/11 nộp theo thông báo cuối.

## 3. Điểm kiểm bằng chứng 05/11 (G1)

Từ 26/10 G1 không còn quyết định tích hợp tour (tour đã nằm trong phạm vi). Ngày 05/11 cả nhóm kiểm:

- [ ] **Đúng đắn:** Dijkstra và A* khớp NetworkX trên fixture, trên đồ thị ngẫu nhiên và trên 200 cặp dữ liệu thật.
- [ ] **CSV benchmark đầu tiên:** ít nhất bộ 1.000 cặp vùng demo (E2) đã có số đo thật.
- [ ] **Đóng đường chạy trên bản đồ:** không bao giờ dùng cạnh bị đóng (có test); `no_path` hiển thị đúng.
- [ ] **Giờ còn lại của từng người** tới 08/11 đủ cho phần còn thiếu.

Không đạt thì kích hoạt cắt theo [đề xuất phạm vi](proposals/2026-10-26-pham-vi.md) mục 4. Khoản 4 (đóng đường qua API/CLI) và 5 (RQ1b còn 2 kích thước) cần nhóm đồng ý riêng. Ghi quyết định vào PROGRESS.md.

## 4. Đường găng và rủi ro

| Rủi ro | Phát hiện sớm ở | Phương án |
|---|---|---|
| OSMnx không cài được trên Windows | T02 (ngày 23–24/10) | Môi trường conda-forge riêng cho bước dữ liệu; app không cần OSMnx |
| Dữ liệu thô không tái lập được (tải lại ra số khác) | T34 | Chỉ dùng bản trên Release, kiểm sha256; không ai tải lại OSM |
| Đảo lat/lon, sai đơn vị → A* sai | T22, T31 (`c < 0,999`) | `geo_scale` tự giảm `c`; điều tra cạnh vi phạm |
| Python quá chậm ở đồ thị lớn | T61 (pilot) | Dừng ở kích thước có median Dijkstra ≈ 1 s; chỉ báo cáo các kích thước đã đo |
| Thiếu người (Duy Anh vắng sáng 26/10) | Đã hết: Duy Anh quay lại chiều 26/10 | Rà lại ngân sách tuần 3 ở buổi họp 01/11, gồm cả T72–T74 |
| Làm song song nhiều PR lớn, review vội | Mỗi PR | Người review chạy test và để lại ít nhất một nhận xét cụ thể; PR lớn tách nhỏ |
| Trễ sau 05/11 | Điểm kiểm G1 | Thứ tự cắt đã duyệt ([đề xuất phạm vi](proposals/2026-10-26-pham-vi.md) mục 4) |

## 5. Quyết định đắt nếu đổi

Đổi những quyết định này sau khi đã có code hoặc số liệu dựa trên chúng thì phải làm lại nhiều task. Mỗi mục phải chốt **trước task đầu tiên** cần nó, kể cả khi chưa tới tuần đó. Trạng thái và bằng chứng của từng mục cập nhật ở [STATUS.md](STATUS.md).

| # | Quyết định | Việc phải chờ (chốt trước việc này) | Hạn chốt | Nếu thiếu bằng chứng thì kiểm bằng | Trạng thái |
|---|---|---|---|---|---|
| Q1 | Định dạng `saigo-graph/1` và cách đánh ID cạnh `(u, v, key)` ([DATA_MODEL](DATA_MODEL.md) mục 2) | T11 (bắt đầu), T31 (bắt đầu), T41, T51 | 24/10 | `mini.json` nạp được bằng `load_graph` (T01) | **Đã chốt**: T01 merge (#57); kiểm thứ tự `(u, v, key)` khi nạp ở #61 |
| Q2 | Bản dữ liệu thô dùng chung (sha256 `24a28327…`) và nơi lưu cho cả nhóm | T31, T61, mọi benchmark | 26/10 | Hai máy tải từ Release ra cùng sha256 | **Đã duyệt 26/10** (Release `data-raw-20261024`); chờ T34 tạo Release |
| Q3 | Vùng demo (nửa cạnh 2 km) và các kích thước của thí nghiệm tăng quy mô | T31, T61, T62 | 27/10 (T61 chốt sau pilot) | Pilot T61: đo median Dijkstra ở kích thước lớn nhất | Vùng demo **đã duyệt 26/10**; **4 kích thước 1 / 2 / 3 / 4,5 km, chốt 28/10** sau pilot T61 (#82) |
| Q4 | Bảng tốc độ `speeds.json` (cũng quyết định `v_max`) | T22, T33, T60 | 28/10 | `check-heuristic` trên đồ thị thật (T22) | **Đã duyệt 26/10**, đóng băng (`v_max` 40 km/h); tốc độ vẫn là giả định mô phỏng. Đổi sau 02/11 thì chạy lại toàn bộ benchmark |
| Q5 | Mô hình ùn tắc (`max α`, trung điểm cạnh) và cách đóng đoạn (cạnh đối) ([DATA_MODEL](DATA_MODEL.md) mục 4) | T40, T41, T63 | 29/10 | Test trên `mini.json`: vùng ùn tắc đổi tuyến, nhân đều không đổi | **Đã duyệt 26/10**; chưa có code |
| Q6 | Contract `/api/route` (request/response, [ARCHITECTURE](ARCHITECTURE.md) mục 4) | T13, T51 và T52 (T52 code trước được với contract này) | 30/10 | Test API với fixture (T13, T51) | **Đã chốt 25/10** (v1, chỉ được thêm trường); T13 hiện thực |
| Q7 | Môi trường đo: phiên bản Python và thư viện được khóa; quy trình đo ([EXPERIMENT_PLAN](EXPERIMENT_PLAN.md) mục 3) | T60, T62, T63 | 01/11 | Chạy lại một bộ nhỏ trên máy thứ hai ra cùng chi phí | **Đã duyệt 26/10**: máy Tiến, Python 3.11.9 + `requirements-lock.txt`; chưa có benchmark tái lập |
| Q8 | Có tích hợp tour vào API/UI hay không | T72, T73, T74 | 05/11 | — | **Đã quyết 26/10: có** (D10; sáng cắt, chiều giữ lại khi Duy Anh quay lại) |

## 6. Kế hoạch tuần 2 (26/10–01/11) — **Đã duyệt 26/10**

Chương trình họp: [team/meetings/2026-10-26-agenda.md](team/meetings/2026-10-26-agenda.md) · Đề xuất đổi phạm vi: [proposals/2026-10-26-pham-vi.md](proposals/2026-10-26-pham-vi.md) · Phiếu giao việc từng task: [tasks/](tasks/).

> **Ghi nhận ngày 26/10/2026:** theo xác nhận của Tiến, Tiến, Minh và Bảo đã đồng ý các đề xuất mặc định tại Quyết định 1–3, Q1–Q5, Q7 (xem [agenda](team/meetings/2026-10-26-agenda.md#các-quyết-định-cần-chốt)) và phân công T13 → Minh, T12 → Bảo.
> - S1 là cơ sở kế hoạch khi chưa có lịch quay lại của Duy Anh, gồm dự kiến mỗi người thêm khoảng 2 giờ/tuần.
> - Tour được loại khỏi phạm vi cam kết; Tiến còn phải báo giảng viên.
> - Các khoản cắt có yêu cầu đồng ý riêng ([đề xuất](proposals/2026-10-26-pham-vi.md) mục 4, khoản 4 và 5) chưa được coi là đã kích hoạt. Ngân sách tuần 3–4 vẫn thiếu và được rà lại ngày 01/11.
> - Biên bản/ghi nhận chính thức: sẽ do Bảo (thư ký) đăng trên issue *Biên bản họp*.

> **Cập nhật chiều 26/10:** Duy Anh quay lại và đã merge T13, T21, T22, T40, T41, T60 (khung), T64, T70, T71. Tiến chốt: tour (T72–T74) trở lại phạm vi; không gửi thư riêng cho giảng viên. Bảng 6.2–6.5 dưới đây là kế hoạch sáng 26/10; phần việc đã làm ghi ở [PROGRESS](PROGRESS.md), ngân sách tuần 3 rà lại ở buổi họp 01/11.

**Điều kiện của tuần (sáng 26/10):** Duy Anh **không tham gia** tuần 2. T01, T10, T11, T20 của Duy Anh đã chuyển sang Tiến (26/10). Mọi phép tính coi sức làm của Duy Anh là 0 cho tới khi có ngày cụ thể. Sức làm: Tiến ~15 giờ (kiêm người tích hợp), Minh ~11 giờ, Bảo ~11 giờ. Review, tích hợp và họp đều được tính vào số giờ này.

### 6.1. Mục tiêu tuần (mỗi mục kiểm được bằng lệnh hoặc thao tác)

1. **Walking skeleton (MW) chạy trên 2 máy trước hết 29/10:** bấm 2 điểm → `/api/route` → Dijkstra trên `mini.json` → vẽ tuyến. Minh làm cả hai phía (T13, T14); Bảo làm lại được trên máy mình từ code đã merge (T15).
2. **M1 + M2 trên đồ thị mẫu:** Dijkstra **đã đạt** (T11, #59: khớp 6/6 tình huống tính tay của T03). Còn A* (T20) và CLI chạy được cả hai thuật toán (T12).
3. **Dữ liệu đóng băng dùng chung (thay cho M3 cũ):** `outer.graphml` lên Release, hai máy kiểm cùng sha256; `load_graph` (T01) đọc được đồ thị vùng demo của T31.
4. **Quyết định phạm vi và Q1–Q5, Q7: đã chốt 26/10**, tài liệu đã đồng bộ (mục 6.6). Còn: cập nhật GitHub sau khi PR đồng bộ merge.

Không thuộc tuần 2, dời sang tuần 3: snap có ngưỡng (T50), đối chứng NetworkX trên dữ liệu thật (T22, T33), ùn tắc và đóng đường (T40–T42). Vẽ toàn bộ mạng đường (T32) **đã cắt** khỏi phạm vi cam kết.

### 6.2. Phân công đã duyệt và tình hình ngày 26/10

| Người | Task (ước lượng giờ, ngày mục tiêu) | Review, họp, tích hợp | Dự phòng |
|---|---|---|---|
| **Tiến** | ✅ [T01](tasks/T01-graph-format.md) 3 (#57) · ✅ [T10](tasks/T10-geo.md) 2 (#58) · ✅ [T11](tasks/T11-dijkstra.md) 4 (#59) · kiểm thứ tự ID cạnh trong `load_graph`, góp ý review T11 của Bảo, 0,5 (27/10) · [T20](tasks/T20-astar.md) A* 3 (30–31/10) | Review T13, T14, T12, T34; họp; merge, PR đồng bộ phạm vi, STATUS | — |
| **Minh** | [T34](tasks/T34-release-data.md) Release + merge #46→#47→#53 2 (26/10) · [T14](tasks/T14-map-skeleton.md) bản đồ skeleton 3 (27–28/10) · [T13](tasks/T13-api-skeleton.md) API skeleton 3 (28–29/10) | Review T20; họp | 1 |
| **Bảo** | [T15](tasks/T15-second-machine.md) chạy MW trên máy thứ hai 2 (29/10) · [T12](tasks/T12-cli.md) CLI có cả A* 2 (30–31/10) | Đã review T01, T10, T11 (25–26/10); thư ký; review #56 | 3: chỉ dùng cho [T21](tasks/T21-oracle.md) (31/10–01/11) **khi MW đã đạt và T20 đã merge** |
| Duy Anh | — | — | 0 |

**Giảm tải đã duyệt:** T13 chuyển từ Tiến sang **Minh**, nên Minh làm trọn lát dọc của skeleton (API + bản đồ), Tiến review. T12 chuyển sang **Bảo**. T20 giữ ngày 30–31/10.

Ước lượng của T01, T10, T11 là giờ kế hoạch; giờ thực tế Tiến ghi trên PR. Tiến còn khoảng 3,5 giờ task cộng phần review, tích hợp và PR đồng bộ; số này sẽ rà lại ở buổi họp 01/11 cùng ngân sách tuần 3.

### 6.3. Phụ thuộc và mức chặn

Mức chặn:
- **bắt đầu**: phải có tiền đề trước khi viết code;
- **tích hợp**: code trước được theo interface/contract, chờ bên kia merge mới ghép;
- **chấp nhận**: chỉ được tính xong sau khi kiểm chung.

| Task | Phụ thuộc (mức chặn) |
|---|---|
| T01, T10, T11 | ✅ Đã merge (#57, #58, #59). T11 đã đối chiếu với T03 (#54) |
| Kiểm thứ tự ID cạnh | — (làm trước T20) |
| T13 | T11, T10 đã có: dùng trực tiếp `dijkstra()` và `geo.haversine_m` |
| T14 | Contract `/api/route` v1 (bắt đầu, đã chốt) · T13 (tích hợp, cùng người làm) |
| T15 | T13 và T14 đã merge (bắt đầu) |
| T20 | T11 và T10 đã có · PR kiểm thứ tự ID cạnh (bắt đầu: merge trước T20) |
| T12 | T11 đã có (bắt đầu) · T13 (tích hợp: `--from-latlon` dùng `nearest_node_naive` của T13) · T20 (chấp nhận: phải gọi được cả A* mới tính là xong) |
| T21 | T20 đã merge và MW đã đạt (bắt đầu) |
| T34 | — |

### 6.4. Ai sở hữu file nào trong tuần 2

Hai task song song không sửa cùng một file. Khi cần sửa file của người khác, ghi vào PR: "cần đổi X ở file Y, nhờ <chủ file>".

| File / tài nguyên | Chủ sở hữu tuần 2 | Ghi chú |
|---|---|---|
| `backend/app/graph/model.py`, `tests/fixtures/mini.json`, `tests/mini_cases.py` | Tiến (T01 đã xong; kiểm thứ tự cạnh; T20) | Minh và Bảo chỉ đọc |
| `backend/app/graph/geo.py` | Tiến (T10 đã xong) | |
| `backend/app/algorithms/*`, `backend/app/graph/scenario.py` | Tiến (T11 đã xong, T20) | `Snapshot` chỉ có **một** định nghĩa, trong `graph/scenario.py` (đã có cùng `baseline_snapshot()`); T40 (tuần 3) thêm `Scenario` và `build_snapshot` vào cùng file, không tạo kiểu mới |
| `backend/app/main.py`, `api/*`, `services/routing.py` | **Minh (T13)** | Tiến review. Snap tạm là hàm `nearest_node_naive(graph, meta, lat, lon)` trong `services/routing.py`; T50 (tuần 3) thay đúng hàm này |
| `backend/app/cli.py` | Bảo (T12) | Sang tuần 3, T22 rồi T40 lần lượt sửa |
| `frontend/src/*` | Minh (T14) | Thứ tự tiếp theo: T14 → T52 → T54 |
| Release `data-raw-20261024`, `data/processed/*manifest.json` | Minh (T34) | Không ai tải lại OSM để thay thế |
| `docs/STATUS.md`, `ROADMAP.md`, `TASKS.md`, `tracking/schedule.csv` | Tiến (người tích hợp) | Người làm ghi bằng chứng trong PR; chỉ sửa dòng PROGRESS của task mình |

### 6.5. Các mốc kiểm trong tuần

| Ngày | Phải có | Ai kiểm | Nếu không đạt |
|---|---|---|---|
| **26/10** | ✅ 3 quyết định phạm vi đã chốt; ✅ interface `Graph`/`Snapshot`/`SearchResult` đã merge (#57, #59). Còn: Release có file, Tiến tải về ra đúng sha256 `24a28327…`; hàng chờ PR (#46, #47, #53, #55, #60) được merge; #56 merge | Tiến | Dời việc phụ thuộc, ghi vào STATUS |
| **27/10** tối | Kiểm thứ tự ID cạnh merge; `load_graph` đọc được đồ thị vùng demo của T31 (cần Release của T34) | Bảo (review), Tiến | Tiến và Minh gỡ ngay sáng 28/10 |
| **28/10** tối | Đường mỏng API → UI chạy được trên máy Minh (dù test chưa đủ) | Minh, Tiến | Thu gọn T14: chỉ vẽ tuyến, chưa hiện bảng |
| **29/10** tối | T13 + T14 merge; Bảo làm lại thao tác ✅ của T14 trên máy mình (T15) | Bảo | Ghi lỗi thành issue *Lỗi* giao Minh; MW chưa đạt thì T21 không bắt đầu |
| **01/11** (họp tuần) | T20 có bằng chứng (`expanded = 2` trên `mini.json`); T12 chạy được cả hai thuật toán; rà ngân sách tuần 3 và chọn phần nghiên cứu sẽ cắt theo S1; xác nhận Duy Anh có quay lại không, từ ngày nào, bao nhiêu giờ | Cả nhóm | Kích hoạt cắt theo thứ tự đã duyệt ([đề xuất phạm vi](proposals/2026-10-26-pham-vi.md) mục 4); khoản 4 và 5 cần nhóm đồng ý riêng |

**Quy tắc merge tuần 2:** PR có approve **còn hiệu lực** và CI xanh thì tác giả merge ngay trong ngày. Với PR xếp chồng: sau khi PR bên dưới merge, bấm *Update branch*; nếu approve bị hủy thì nhờ approve lại ngay, không để qua ngày.

### 6.6. Dời việc so với `schedule.csv`

| Task | Tuần gốc | Kế hoạch đã duyệt | Lý do |
|---|---|---|---|
| T01, T10, T11 | 1–2 (Duy Anh) | 2 (Tiến) — ✅ đã merge 26/10 | Duy Anh không tham gia tuần 2 |
| T20 | 2 (Duy Anh) | 2 (Tiến), 30–31/10 | Như trên |
| T12 | 2 (Tiến) | 2 (Bảo) | Giảm tải cho Tiến |
| T13 | 2 (Tiến) | 2 (Minh) | Giảm tải cho Tiến; Minh làm trọn lát dọc skeleton |
| T21 | 2 (Duy Anh) | 2 nếu Bảo còn dự phòng, không thì 3 | Không để T21 chiếm phần dự phòng sửa lỗi |
| T22, T33 | 2 | 3 (02–03/11); **người làm cần phân bổ lại** ở buổi họp 01/11 | Phụ thuộc T20 và dữ liệu đóng băng; Duy Anh = 0 |
| T50 | 2 | 3 | T13 đã nạp đồ thị khi khởi động; snap tạm đủ cho skeleton |
| T40, T41, T42 | 2 | 3 | Phụ thuộc T11; tuần 2 ưu tiên MW và A* |
| T32 | 2 | **Cắt** (Quyết định 1) | Dùng nền tile OSM, chỉ vẽ tuyến |
| T70–T74 (tour) | 2–3 | Sáng 26/10 cắt; chiều 26/10 giữ lại: T70, T71 đã xong, T72–T74 05–08/11 | Duy Anh quay lại |

**PR đồng bộ (Tiến, 26/10).** Mục 1–4 đã làm trong PR đồng bộ; mục 4 (GitHub) và 5 làm ngay khi PR đó merge. Cập nhật nguồn dữ liệu trước, chạy `--sync` sau cùng:
1. ROADMAP mục 1–5 (mốc, G1 thành điểm kiểm bằng chứng, M8, Q8); TASKS phần ngoài tuần 2 (M3, T32, T50–T55, T61–T64, G1, T70–T74, T80–T83, người làm T22/T33).
2. PROJECT_BRIEF, EXPERIMENT_PLAN (E3 chỉ fixed trips, 3 kích thước; E5 giữ lại), DEMO, PROGRESS (bảng trạng thái và checklist UI; giữ nguyên nhật ký).
3. Mô tả milestone trong `scripts/tracking/create_backlog.py` và `tracking/schedule.csv`; thêm T34.
4. Đóng T32 với lý do *not planned*; rồi chạy `create_backlog.py --sync` và `setup_project.py --sync`.
5. Không gửi thư riêng cho giảng viên (quyết định chiều 26/10); lý do đổi phạm vi ghi trong PROJECT_BRIEF mục 4 và essay.
