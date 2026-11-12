# SaiGo — Project Brief

**Phiên bản:** 2.1 — 26/10/2026 (đồng bộ [đề xuất đổi phạm vi](proposals/2026-10-26-pham-vi.md) đã duyệt 26/10) · **Thay cho:** phần phạm vi/timeline của [TOPIC.md](TOPIC.md) (v1.0, 01/10/2026). TOPIC.md vẫn là đặc tả nền; khi hai tài liệu khác nhau, tài liệu này được ưu tiên.

Bộ tài liệu kế hoạch:

| File | Nội dung |
|---|---|
| PROJECT_BRIEF.md | Mục tiêu, phạm vi, quyết định, giả định, demo, câu hỏi bảo vệ |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc, công nghệ, module, luồng dữ liệu |
| [DATA_MODEL.md](DATA_MODEL.md) | Đồ thị, trọng số, snapshot, heuristic, I/O thuật toán, dữ liệu |
| [ROADMAP.md](ROADMAP.md) | Các mốc, mỗi mốc có một kết quả chạy được |
| [TASKS.md](TASKS.md) | Task theo buổi, phụ thuộc, lệnh kiểm tra |
| [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) | Thiết kế thực nghiệm A* vs Dijkstra, tăng quy mô, ùn tắc/đóng đường, tour |
| [PROGRESS.md](PROGRESS.md) | Tiến độ, phần đã/chưa kiểm chứng, lỗi tồn tại |

Quy ước nhãn trong toàn bộ tài liệu:

- **[Đã chốt]**: nhóm đã quyết định.
- **[Đề xuất]**: phương án mặc định; dùng nếu không ai phản đối, có thể đổi.
- **[Giả định]**: điều kiện mô hình hoặc thông tin chưa kiểm chứng.
- **[Chưa đo]**: số liệu sẽ có sau thực nghiệm. Không điền số khi chưa chạy.

---

## 1. Bối cảnh

| Mục | Nội dung | Nguồn |
|---|---|---|
| Môn | Introduction to AI — 261_72ITSE30303_01, Dr. Huy T. Nguyen | Project_Intructions_261.pdf |
| Hướng đề tài | Category 1 — *Pathfinding in Complex Environments*: cài đặt và so sánh thuật toán tìm kiếm trên bản đồ phức tạp, ví dụ "a city map with traffic"; mở rộng gợi ý: "dynamic obstacles" | PDF trang 1–2 |
| Đầu ra bắt buộc | Essay 10 trang (không tính bìa), double spaced, có introduction/discussion/conclusion; thuyết trình 15 phút | PDF |
| Mốc (tentative) | 12/11 final ready · 19/11 thuyết trình · 22/11 nộp ETC | PDF |
| Không bắt buộc | File `.exe`; PDF không yêu cầu | PDF |
| Đã trình bày | Proposal 02/10: Dijkstra + A* tự cài, NN + 2-opt có hướng, Held–Karp trên case nhỏ, ùn tắc mô phỏng + đóng đường, ~1.000 truy vấn benchmark, app local Windows | Slides + script proposal |

**Trạng thái thực tế ngày 23/10:** repo mới có khung (FastAPI `/api/health`, Vite + Leaflet trống, script rỗng). Chưa có dữ liệu, thuật toán hay kết quả. Mốc "scope gate 23/10" trong proposal **không đạt**, nên phạm vi được sắp lại dưới đây.

**Ngày 26/10:** Duy Anh vắng tuần 2 và chưa có ngày quay lại; ba người còn lại không đủ giờ cho phạm vi cũ. Nhóm duyệt [đề xuất đổi phạm vi](proposals/2026-10-26-pham-vi.md): cắt tour, rút gọn bản đồ, RQ1b còn 3 kích thước, điểm kiểm bằng chứng 05/11 và MVP tích hợp 08/11. **Chiều 26/10** Duy Anh quay lại và làm xong một phần lớn việc thuật toán, kể cả tour trên ma trận, nên tour được giữ lại; các thay đổi khác giữ nguyên (D10–D13 ở mục 4).

## 2. Mục tiêu

**Một câu:** SaiGo tìm đường trên mạng đường thật của trung tâm TP.HCM bằng Dijkstra và A* do nhóm tự cài, cho thấy A* tiết kiệm bao nhiêu công tìm kiếm mà vẫn ra cùng chi phí tối ưu, khi có ùn tắc hoặc đóng đường mô phỏng và khi bản đồ lớn dần.

### 2.1. Tối ưu cái gì? [Đã chốt]

**Tối ưu thời gian di chuyển mô phỏng, đơn vị giây.** Quãng đường (mét) vẫn được tính và hiển thị, nhưng không phải mục tiêu tối ưu.

Lý do:

1. Ùn tắc chỉ có nghĩa khi chi phí là thời gian: ùn tắc làm chậm xe, không làm đường dài ra.
2. Hai con đường dài bằng nhau có thể có tốc độ khác nhau theo loại đường.
3. Proposal đã trình bày trọng số là giây (`w = L / v · α`).

Hệ quả cần hiểu: heuristic của A* phải đổi mét sang giây bằng tốc độ lớn nhất `v_max` (xem [DATA_MODEL.md](DATA_MODEL.md) mục 5). Chế độ "tối ưu quãng đường" chỉ dùng làm phép kiểm tra phụ trong test, không đưa vào giao diện.

### 2.2. Câu hỏi nghiên cứu

| Mã | Câu hỏi | Trạng thái |
|---|---|---|
| RQ1 | A* có giảm số node mở rộng và thời gian truy vấn so với Dijkstra trong khi vẫn cho cùng chi phí tối ưu không? | Từ proposal |
| RQ1b | Mức chênh lệch đó thay đổi thế nào khi đồ thị lớn dần (số node tăng)? | **Mới** — theo yêu cầu thử nghiệm tăng quy mô; 4 kích thước lồng nhau, chỉ workload "fixed trips" (D11) |
| RQ2 | NN + 2-opt có hướng cải thiện tour bao nhiêu so với thứ tự nhập và NN đơn lẻ; cách tối ưu Held–Karp bao xa trên case nhỏ? | Từ proposal. Giữ trong phạm vi (D10): thuật toán đã có (T70, T71); ma trận từ đồ thị, API, UI, benchmark (T72–T74) trước 08/11 |
| RQ3 | Ùn tắc và đóng đường ảnh hưởng thế nào tới tính khả thi, chi phí tuyến, số node A* mở rộng và thời gian lập lại kế hoạch? | Từ proposal, thêm chỉ số A* |

Không đặt trước kết luận "A* luôn nhanh hơn". Nếu kết quả không cải thiện, báo cáo đúng như vậy.

## 3. Phạm vi

### 3.1. Bản tối thiểu (MVP) — bằng chứng ở điểm kiểm 05/11, tích hợp xong 08/11

| # | Chức năng | Ghi chú |
|---|---|---|
| 1 | Pipeline dữ liệu: OSM → đồ thị JSON của nhóm + manifest + hash | Chạy offline sau khi tải một lần |
| 2 | Dijkstra và A* tự cài, khôi phục tuyến theo **cạnh** | Không dùng hàm shortest path của thư viện trong sản phẩm |
| 3 | Kiểm thử đối chứng với NetworkX (chỉ trong test) | So chi phí và `no_path` |
| 4 | Snapshot: kịch bản ùn tắc theo vùng + danh sách cạnh bị đóng | Đồ thị gốc không bị sửa |
| 5 | API `/api/route`, `/api/dataset` | FastAPI. Không có `/api/network` (không vẽ toàn mạng đường, D12) |
| 6 | Bản đồ: chọn 2 điểm, xem tuyến Dijkstra và A*, bảng so sánh, chọn kịch bản và vẽ vùng ùn tắc, bấm vào một đoạn trên tuyến để đóng (đóng cả cạnh đối nếu có) rồi tìm lại, nút mở lại, báo "không có đường" | Leaflet, TypeScript thuần; nền tile OSM, chỉ vẽ tuyến và các cạnh của tuyến (D12) |
| 7 | Benchmark offline: 1.000 truy vấn trên vùng demo + thí nghiệm tăng quy mô 4 kích thước, chỉ "fixed trips" | CSV/JSON + biểu đồ |
| 8 | Tour nhiều điểm: NN, 2-opt có hướng, Held–Karp (n ≤ 10) trên ma trận chi phí tính từ đồ thị; `/api/tour`; UI kho + 5 điểm với 3 thẻ so sánh; benchmark tour | T70–T74; trở lại phạm vi chiều 26/10 (D10) |

### 3.2. Mở rộng — chỉ làm nếu sau 08/11 còn thời gian

| Phần | Ghi chú |
|---|---|
| Phát lại trace dạng animation | Không cam kết |

**Thứ tự cắt khi thiếu giờ** (đã duyệt 26/10, dùng ở điểm kiểm 01/11 và 05/11): xem [đề xuất phạm vi](proposals/2026-10-26-pham-vi.md) mục 4. Khoản 1–3 kích hoạt ở điểm kiểm khi thiếu giờ; khoản 4 (đóng đường qua API/CLI thay vì bản đồ) và 5 (RQ1b còn 2 kích thước) cần nhóm đồng ý riêng.

**Không bao giờ cắt:** test đối chứng, Dijkstra = A* về chi phí, xử lý `no_path`, số liệu đo thật, phần ùn tắc của RQ3.

### 3.3. Ngoài phạm vi

ALT, Simulated Annealing, tìm kiếm hai chiều, nhiều shipper, time window, giao thông/GPS thật, cấm rẽ, đóng gói `.exe`, deploy web, editor kéo thả điểm giao, cache kết quả. Từ 26/10 thêm: vẽ toàn bộ mạng đường (T32), lớp chấm node đã mở rộng trên bản đồ, đóng đường hai chế độ, animation trace, workload "growing trips".

## 4. Quyết định so với TOPIC.md / proposal

| Mã | Quyết định | Lý do |
|---|---|---|
| D1 | Thêm thí nghiệm tăng quy mô bản đồ (RQ1b) | Yêu cầu mới; trả lời câu "A* có lợi hơn khi bản đồ lớn không" |
| D2 | Tour (NN, 2-opt, Held–Karp) chuyển thành mở rộng E1, làm sau lõi tìm đường | 23/10 chưa có code; tour đã hứa trong proposal nên giữ, nhưng không để nó chặn phần lõi |
| D3 | Ùn tắc là **theo vùng/loại đường**, không nhân đều toàn bản đồ | Nhân mọi cạnh cùng một hệ số α không đổi tuyến tối ưu, chỉ đổi con số; demo sẽ vô nghĩa |
| D4 | Bỏ cache tuyến/ma trận ở bản đầu; mỗi request tính lại | Tránh lỗi cache lỗi thời sau khi đóng đường; đồ thị nhỏ nên tính lại vẫn nhanh |
| D5 | Lưu đồ thị bằng JSON và list Python thường; không dùng NPZ/numpy trong thuật toán | Dễ đọc, dễ giải thích; tối ưu tốc độ không phải mục tiêu |
| D6 | Frontend TypeScript thuần, không React | Khung hiện có đã là TypeScript thuần; bớt một thứ phải học |
| D7 | Heuristic có hệ số an toàn `c` tính từ dữ liệu | Bảo đảm cận dưới ngay cả khi dữ liệu có cạnh ngắn hơn khoảng cách thẳng (xem DATA_MODEL mục 5) |
| D8 | Không cam kết `.exe`; app chạy local bằng lệnh trong README | PDF không yêu cầu; đóng gói geospatial tốn thời gian |
| D9 | Cài OSMnx bằng `pip install -e ".[data]"` trong cùng venv; nếu lỗi trên Windows thì dùng môi trường conda-forge riêng cho bước chuẩn bị dữ liệu | Ứng dụng demo chỉ đọc JSON, không cần OSMnx |
| D10 | Tour (RQ2, T70–T74): sáng 26/10 cắt khỏi phạm vi; **chiều 26/10 giữ lại** *(Tiến chốt)* | Sáng: Duy Anh vắng, tuần 3–4 thiếu 20–23 giờ. Chiều: Duy Anh quay lại và đã xong T70, T71 cùng nhiều task tuần 3, nên đủ giờ cho T72–T74 |
| D11 | RQ1b: **chỉ workload "fixed trips"** *(26/10)*; số kích thước: 26/10 chốt 3, **28/10 giữ đủ 4 (1 / 2 / 3 / 4,5 km)** *(Tiến chốt)* | Bỏ growing trips để bớt giờ làm. Pilot T61: vùng lớn nhất chỉ ~14 ms/truy vấn và script đã cắt sẵn cả 4, nên kích thước thứ 4 gần như không tốn thêm |
| D12 | Bản đồ rút gọn: không vẽ toàn mạng đường (T32), không có lớp chấm node mở rộng; đóng đường một chế độ *(26/10)* | Giữ đủ các bước demo cho RQ1, RQ3; `expanded` vẫn có trong bảng và benchmark |
| D13 | Mốc: **điểm kiểm bằng chứng 05/11**, **MVP tích hợp 08/11**, 09–12/11 không thêm tính năng; essay bắt đầu từ tuần 3 *(26/10)* | Thay cổng G1 "có tích hợp tour không", vì tour đã nằm trong phạm vi |

Không gửi thư riêng cho giảng viên (giảng viên xem repo khi nộp cuối kỳ). Các thay đổi so với proposal (D1, D11–D13) được giải thích ở mục này và ở phần giới hạn của essay.

## 5. Giả định

| Mã | Giả định | Ảnh hưởng nếu sai |
|---|---|---|
| A1 | **[Giả định]** Phương tiện mô phỏng gần với xe máy, nhưng dùng mạng `network_type="drive"` của OSMnx làm xấp xỉ | Thiếu một số hẻm xe máy đi được; ghi vào giới hạn |
| A2 | **[Giả định]** Tốc độ theo loại đường lấy từ file cấu hình, không phải số đo thực tế | ETA chỉ là ước tính theo mô hình |
| A3 | **[Giả định]** Chi phí cố định trong suốt một lần tìm kiếm | Không mô hình ùn tắc thay đổi theo giờ |
| A4 | **[Giả định]** Không mô hình cấm rẽ và đèn tín hiệu | Tuyến có thể rẽ ở chỗ thực tế cấm |
| A5 | **[Đề xuất]** Vùng demo: hình vuông nửa cạnh 2 km quanh chợ Bến Thành; vùng tải: nửa cạnh 4,5 km + đệm 0,5 km | Kích thước cuối chốt sau thử nghiệm sơ bộ (task T61) |
| A6 | **[Đề xuất]** Điểm người dùng chọn được ánh xạ về node gần nhất trong thành phần liên thông mạnh, tối đa 150 m | Điểm xa hơn bị từ chối, có thông báo |
| A7 | **[Giả định]** Dữ liệu OSM tải một lần rồi đóng băng; mọi thực nghiệm dùng cùng bản có hash | Tải lại có thể ra số node/cạnh khác |

## 6. Phân công (cập nhật 26/10)

| Người | Vai trò chính | Ghi chú |
|---|---|---|
| Võ Việt Tiến | Điều phối và tích hợp; Dijkstra, A*, heuristic (nhận từ Duy Anh 26/10); API; benchmark; ma trận chi phí và `/api/tour` | Có thể vào làm cùng ở phần dữ liệu/bản đồ |
| Bùi Duy Anh | API skeleton (T13), đối chứng (T21), heuristic (T22), ùn tắc và đóng đường (T40, T41), khung benchmark và biểu đồ (T60, T64), tour (T70, T71) | Vắng sáng 26/10, quay lại chiều 26/10 |
| Võ Hoàng Minh | Pipeline dữ liệu, Release dữ liệu thô (T34), bản đồ, giao diện, UI tour | |
| Đỗ Quốc Bảo | Ca kiểm thử tính tay, CLI (T12), file case demo, kiểm thử thủ công, chạy thử trên máy thứ hai, ảnh chụp, tài liệu, hỗ trợ demo | Thư ký các buổi họp |

Mỗi người phải giải thích được toàn bộ mô hình, không chỉ phần mình làm. Mỗi module được ít nhất một người khác review.

## 7. Kịch bản demo (~4 phút trong 15 phút thuyết trình)

Mọi case được chạy thử trước trên đúng snapshot dùng để demo, lưu trong `data/demo/cases.json` và gọi là "case minh họa". Kết luận tổng quát chỉ lấy từ benchmark.

| Bước | Thao tác | Màn hình | Người xem hiểu | RQ |
|---|---|---|---|---|
| 1 | Mở app, chọn case "Hai điểm qua trung tâm" | Nền bản đồ OSM vùng demo, 2 marker đã snap | Bài toán: đồ thị có hướng thật, chi phí là giây | — |
| 2 | Bấm **Tìm đường** (chạy cả hai thuật toán) | Hai tuyến trùng nhau; bảng: chi phí bằng nhau, số node mở rộng, thời gian tính | A* cho cùng chi phí tối ưu | RQ1 |
| ~~3~~ | *Đã cắt 26/10 (D12): lớp "Node đã mở rộng". Số node mở rộng vẫn có trong bảng ở bước 2* | | | |
| 4 | Đảo chiều đi/đến | Tuyến và chi phí khác chiều ban đầu | Đường một chiều: A→B ≠ B→A | — |
| 5 | Chọn kịch bản "Cao điểm mô phỏng — trung tâm" | Vùng ùn tắc tô màu; tuyến đổi sang đường vòng; chi phí tăng | Ùn tắc theo vùng làm đổi lựa chọn | RQ3 |
| 6 | Bấm vào một đoạn trên tuyến → **Đóng đoạn đường** | Đoạn đỏ; tuyến mới; nhật ký "Đóng cạnh …"; nút mở lại | Lập lại tuyến, không dùng cạnh bị đóng | RQ3 |
| 7 | Chọn case "Không còn đường" | Thông báo không có đường; không vẽ đường thẳng | Hệ thống báo đúng giới hạn | RQ3 |
| 8 | Chuyển sang slide biểu đồ tăng quy mô | Node mở rộng / thời gian theo số node đồ thị | Lợi thế của A* khi bản đồ lớn — số đo thật | RQ1b |
| 9 | Chuyển sang chế độ tour, case "Kho + 5 điểm": thẻ Thứ tự nhập / NN / NN + 2-opt | Thứ tự giao đổi, chi phí trước/sau | Tầng thứ hai của bài toán | RQ2 |

Dự phòng: quay màn hình toàn bộ kịch bản trước buổi thuyết trình.

## 8. Câu hỏi giảng viên có thể hỏi

Người trả lời là phân công tạm; chia lại ở buổi họp tuần 3 theo người đã làm từng phần.

| # | Câu hỏi | Ý chính để trả lời | Người trả lời |
|---|---|---|---|
| 1 | Vì sao tối ưu thời gian mà không phải quãng đường? | Ùn tắc chỉ đổi thời gian; tốc độ khác nhau theo loại đường; quãng đường vẫn hiển thị | Tiến |
| 2 | Vì sao heuristic của A* không đánh giá quá cao? | Không tuyến nào ngắn hơn đường thẳng; không cạnh nào nhanh hơn `v_max`; `α ≥ 1` chỉ làm chậm thêm; hệ số `c` xử lý cạnh lệch dữ liệu | Tiến |
| 3 | Admissible khác consistent thế nào? Heuristic của nhóm là loại nào? | Consistent: `h(u) ≤ w(u,v) + h(v)`; chứng minh bằng bất đẳng thức tam giác; consistent suy ra admissible và không cần mở lại node | Tiến |
| 4 | Vì sao ít node mở rộng hơn chưa chắc nhanh hơn? | A* tốn thêm phép tính heuristic cho mỗi node; truy vấn ngắn thì phần tiết kiệm nhỏ | Tiến |
| 5 | Nếu ùn tắc làm `v_max` thay đổi thì sao? | Ùn tắc chỉ nhân `α ≥ 1` → chậm hơn → cận dưới cũ vẫn đúng; nếu có kịch bản làm nhanh hơn thì phải tính lại `v_max` | Tiến |
| 6 | Vì sao A→B khác B→A? | Đồ thị có hướng; đường một chiều chỉ có cạnh một phía | Minh |
| 7 | Dữ liệu nào thật, dữ liệu nào mô phỏng? | Thật: hình học, chiều đường, loại đường từ OSM. Mô phỏng: tốc độ, ùn tắc, đóng đường | Minh |
| 8 | Điểm người dùng bấm không nằm trên đường thì sao? | Ánh xạ về node gần nhất trong thành phần liên thông mạnh, tối đa 150 m; xa hơn thì từ chối | Minh |
| 9 | Xử lý cạnh song song và đóng đường thế nào? | Mỗi cạnh có ID riêng `(u, v, key)`; predecessor lưu cạnh; đóng đường loại đúng ID cạnh | Tiến |
| 10 | Ùn tắc được mô phỏng thế nào? Vì sao không nhân đều toàn bản đồ? | Luật theo vùng + loại đường, lấy α lớn nhất; nhân đều không đổi tuyến tối ưu | Tiến |
| 11 | Khi tăng quy mô, nhóm so sánh công bằng thế nào? | Cùng một lần tải, cắt lồng nhau; bộ cặp cố định dùng lại ở mọi kích thước; đo theo số node thực | Tiến |
| 12 | Thời gian đo có bị ảnh hưởng bởi vẽ bản đồ không? | Benchmark chạy CLI riêng, tắt trace, warm-up, lặp nhiều lần, lấy median/p95 | Tiến |
| 13 | Phần nào nhóm tự viết, phần nào dùng thư viện? | Tự viết: Dijkstra, A*, heuristic, snapshot, snap, benchmark, tour (NN, 2-opt, Held–Karp). Thư viện: OSMnx tải dữ liệu; NetworkX chỉ đối chứng trong test; FastAPI/Leaflet là lớp web | Tiến |
| 14 | Vì sao 2-opt không bảo đảm tối ưu toàn cục? Vì sao tính lại toàn bộ chi phí tour? | Tìm kiếm cục bộ dừng ở cực trị địa phương; với ma trận bất đối xứng, đảo đoạn làm đảo chiều các chặng bên trong | Duy Anh |
| 15 | Độ phức tạp của Dijkstra với binary heap? | `O((V + E) log V)`; nhóm dùng lazy deletion nên heap có thể chứa entry trùng, bỏ qua entry lỗi thời khi pop | Tiến |
| 16 | Giới hạn lớn nhất của kết quả? | Một khu vực, tốc độ giả định, không cấm rẽ, ETA không phải thực tế | Tiến |
