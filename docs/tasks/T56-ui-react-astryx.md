# T56 — Giao diện React + Astryx (gộp T54, T73)

**Đặc tả đã duyệt 13/11 (Tiến).** Giao cho: Tiến · Review: Minh · Người tích hợp: Tiến · Nhánh: `t56-ui-astryx`
Phụ thuộc: T51 (#86, **tích hợp**: kịch bản, cạnh đóng, `edge_twin_ids`, `/api/dataset`) · T72 (**tích hợp**: `/api/tour`)
Ước lượng: 8 giờ

## Khảo sát (13/11)

- **Hiện tại:** Vite + TypeScript thuần + Leaflet (~680 dòng, T14, T52, T53): chọn 2 điểm; Tìm đường (Dijkstra + A*), Đảo chiều, Xóa; dropdown kịch bản từ `/api/dataset` (404 thì chỉ có "Bình thường") và vẽ vùng ùn tắc; 2 tuyến (trùng thì một nét có viền); bảng so sánh, "Chi phí trùng khớp", cảnh báo; marker tại node đã snap; báo không có đường; lỗi API; bỏ response cũ; trạng thái server.
- **Mong muốn:** cùng hành vi, giao diện bằng component và theme của Astryx (React 19); thêm đóng đoạn đường (T54) và chế độ tour (T73).
- **Phải giữ nguyên:** backend và contract API; `[lon, lat]` → `[lat, lon]`; không vẽ đường thẳng khi `no_path`; hai nhãn thời gian tách riêng; ghi nguồn OSM; mọi số lấy từ API; `npm run build` chạy trên Windows; proxy `/api` của Vite.
- **Chưa biết:** Astryx (0.7.x) sống chung với `leaflet.css`; kích thước bundle; hiển thị tiếng Việt.

## Quy tắc

| ID | Quy tắc |
|---|---|
| R1 | React 19 + `@astryxdesign/core` (khóa đúng phiên bản) + theme `neutral`. Bản đồ dùng Leaflet trực tiếp bọc trong một component (không thêm `react-leaflet`), giữ logic vẽ đã kiểm của `layers.ts` |
| R2 | Bố cục 3 cột theo DEMO mục 1 (điều khiển / bản đồ / kết quả), dựng từ template của Astryx; ngoài khung bản đồ không dùng `div` thô hay mã màu cứng |
| R3 | Giữ đủ mọi hành vi ở mục "Hiện tại" |
| R4 | T54: bấm một đoạn **trên tuyến** → đóng đoạn đó và cạnh đối (`edge_twin_ids`) → tìm lại; đoạn đóng tô đỏ nét đứt; nút "Mở lại tất cả"; `no_path` thì báo, không vẽ đường thẳng |
| R5 | T73: chế độ **Tour**: bấm đặt kho rồi các điểm giao (tối đa 14); gọi `/api/tour`; 3 thẻ Thứ tự nhập / NN / NN + 2-opt, chọn thẻ thì vẽ tuyến và đánh số điểm theo thẻ; `infeasible_under_model` thì báo các cặp lỗi |
| R6 | Ghi quyết định **D15** (đảo D6, dùng React) vào PROJECT_BRIEF |
| R7 | Dropdown **Case demo** nạp điểm, kịch bản và cạnh đóng sẵn từ `data/demo/cases.json` (DEMO mục 1.1) rồi chạy luôn; số hiển thị vẫn lấy từ API |

**Contract:** R4 cần biết đoạn nào của tuyến thuộc cạnh nào. T56 dùng trường `edge_geometries` mà T54 (#100, Minh) đã thêm vào `/api/route` (hình học từng cạnh, có test ở `tests/test_api_edge_geometries.py`); T56 không thêm trường backend nào.

## Ví dụ chấp nhận (đồ thị thật vùng demo, `data/demo/cases.json` của T55)

| Thao tác | Phải ra |
|---|---|
| Dinh Độc Lập → Bitexco, Tìm đường | 186,1 s; Dijkstra mở 404 node, A* 106; "Chi phí trùng khớp: có" |
| Đảo chiều | 193,0 s, tuyến khác (đường một chiều) |
| Kịch bản `peak-center` | Hiện vùng ùn tắc; 246,1 s, tuyến đổi |
| Bấm đoạn giữa tuyến cơ sở (cạnh 1613) | Đoạn đỏ; 204,7 s; tuyến mới không đi qua cạnh 1613 |
| Case "Không còn đường" (đóng 1029, 3123) | Báo không có đường; không vẽ đường thẳng |
| Mở lại tất cả | Về đúng 186,1 s |
| Tour "Kho + 5 điểm" (case `kho-5-diem`) | 3 thẻ có chi phí khớp API; chọn thẻ thì số thứ tự trên bản đồ đổi theo |
| Bấm 2 lần liền khi request cũ còn chạy | Chỉ hiện kết quả của lần sau |
| Tắt backend rồi tìm đường | Báo lỗi, không vẽ tuyến |
| `npm run build`; checklist UI-1…UI-9 (PROGRESS mục 5) | Đạt |

Kiểm bằng trình duyệt tự động (bấm thật, đọc số trên trang, chụp màn hình), ghi bảng bằng chứng trong PR.

## Kết quả kiểm chứng (13/11, Tiến)

Backend T51 + T72 với `SAIGO_GRAPH` = `hcm-benthanh-r2000-20261024`, Vite dev, Chromium điều khiển bằng Playwright; số đọc từ trang.

| Ví dụ | Kết quả trên trang | |
|---|---|---|
| Dinh Độc Lập → Bitexco | 186,1 s; 1.565 m; Dijkstra 404 / A* 106; trùng khớp: có | Đạt |
| Đảo chiều | 193,0 s; 1.417 m | Đạt |
| `peak-center` | 2 vùng có nhãn; 246,1 s; 1.748 m | Đạt |
| Bấm cạnh 1613 (chuột thật lên nét bấm của cạnh đó) | Đoạn đỏ nét đứt; 204,7 s; API xác nhận tuyến mới không có 1613; dòng kịch bản ghi "đóng thêm 1 cạnh" | Đạt |
| Mở lại tất cả | 186,1 s; hết đoạn đỏ | Đạt |
| Bấm vào điểm giữa từng cạnh của tuyến (review của Minh: đoạn ngắn hay bị đóng nhầm đoạn kế bên) | Trước khi sửa: 9/21 cạnh đóng nhầm ở zoom 16, 11/21 ở zoom 15 (các cạnh 2–6 px, vùng bấm 18 px của cạnh kề đè lên). Sau khi sửa (chọn cạnh gần con trỏ nhất theo pixel, tô đỏ xem trước đoạn sẽ đóng kèm chấm ở giữa cạnh): 0/21 ở cả hai mức zoom | Đạt |
| "Không còn đường" | Cả hai "Không có đường"; banner; không có nét tuyến nào | Đạt |
| Tour `kho-5-diem` | 1.066,0 / 1.003,3 / 898,1 s, tối ưu 627,8 s: khớp API đến 0,1 s; thẻ NN + 2-opt số 1,2,4,3,5 → thẻ NN số 4,3,1,2,5 | Đạt |
| Request đầu bị làm chậm 1,5 s, bấm Đảo chiều ngay | Chỉ hiện 193,0 s (cả lúc 0,4 s và sau 2,9 s) | Đạt |
| Tắt backend (cả khi mở trang lúc backend tắt) | "Không kết nối được server. Kiểm tra backend (uvicorn)…"; badge đỏ; không vẽ tuyến. Bật lại rồi bấm → 186,1 s, badge xanh, đủ 3 kịch bản, không cần tải lại trang | Đạt |
| UI-4 (điểm ngoài vùng) | "Điểm đi cách mạng đường 7674 m, quá ngưỡng 150 m…"; không vẽ tuyến | Đạt |
| `npm run build`; `tsc --noEmit`; `pytest` | Build OK; tsc sạch; 327 passed | Đạt |
| UI-1 (nền OSM) | **Chưa kiểm được trên máy này**: mạng chặn `tile.openstreetmap.org` (curl cũng lỗi). URL tile và dòng ghi nguồn giữ nguyên bản Minh đã đạt 29/10; Minh kiểm khi review (chạy trên máy mình) | Chờ |

Phát hiện khi kiểm, đã sửa: dòng kịch bản ghi "không đóng đường" dù đang đóng cạnh; lỗi backend tắt chỉ hiện "HTTP 502"; badge vẫn báo "sẵn sàng" khi backend đã tắt và không tự hồi phục.

**Giới hạn:**
- Bundle JS 1,05 MB (332 KB gzip): Vite cảnh báo chunk > 500 KB. Chạy local nên chấp nhận.
- Cạnh đóng sẵn của case ("Không còn đường") không tô đỏ, vì UI chỉ có id, không có hình học; vẫn hiện "Đang đóng 2 cạnh".
- Case tour cho thấy NN + 2-opt cách tối ưu 43% (Minh phát hiện trước, 31/10, khi làm UI tour ở #101). Tour tối ưu chính là tour NN đi ngược chiều; 2-opt nhận nước cải thiện đầu tiên nên kẹt ở cực trị địa phương trên ma trận bất đối xứng (đường một chiều). Đúng thuật toán, nên đưa vào essay (T83).

## Quy tắc merge

Chỉ merge vào `main` nếu **mọi** ví dụ chấp nhận đạt và Minh (reviewer) chạy lại được trên máy mình **trước 17/11** (phân công D14). Không kịp thì demo 19/11 bằng giao diện cũ, bản này để trên nhánh.

## Sở hữu

`frontend/*` (thay toàn bộ giao diện TS thuần của T14, T52, T53).
