# R1 — Lập lại tour sau khi đóng đường

**Mức Standard (14/11).** Đặc tả do Tiến ủy quyền chốt (D18, [ROADMAP](../ROADMAP.md) mục 7). Người làm: Tiến · Review: Minh · Nhánh: `r1-tour-closure`
Phụ thuộc: T72 (`/api/tour`, **đã merge** #102), T56 (giao diện React, **đã merge** #103), T54 (`edge_geometries`, `edge_twin_ids` của `/api/route`, **đã merge** #100, #86)
Ước lượng: 6–10 giờ

## Khảo sát (14/11)

- **Hiện tại:** `services/tour.plan_tour()` đã dựng snapshot từ `scenario_id` + `blocked_edge_ids` và trả `infeasible_under_model` kèm các cặp `unreachable` khi có chặng không đi được. Nhưng ở chế độ tour, UI (`App.tsx`) **không gửi** `blocked_edge_ids`, `layers.drawTour()` chỉ vẽ một nét không bấm được, và response không có phương án "giữ thứ tự cũ". Banner không khả thi liệt kê từng cặp, chưa nói gọn điểm nào hỏng.
- **Mong muốn:** đúng câu chuyện của proposal (slide 3, 7, 12): một kho, 5 điểm giao, một đường bị đóng → lập lại tour, báo riêng **giữ thứ tự cũ** và **sắp lại**, hoặc nói rõ không còn tour đầy đủ và điểm nào hỏng.
- **Phải giữ nguyên:** contract `/api/tour` hiện có (chỉ **thêm** trường); request không có trường mới thì response giống hệt trước; chế độ tìm đường hai điểm không đổi; `chosen` vẫn chỉ chọn trong `input`, `nearest_neighbor`, `nearest_neighbor_2opt` (và Or-opt khi bật), không chọn phương án giữ thứ tự cũ; mọi số lấy từ API; không vẽ tour thiếu điểm.
- **Chưa biết:** không có (đóng đoạn trên tuyến đã chạy ở chế độ tìm đường; logic chọn cạnh gần con trỏ dùng lại được).

## Quy tắc

| ID | Quy tắc |
|---|---|
| C1 | `TourRequest` thêm `keep_order: list[str] \| None` (mặc định `null`): thứ tự id điểm giao của tour trước khi đóng. Phải là hoán vị đúng của các id trong `stops`; sai (thiếu, thừa, trùng, id lạ) → 422 tiếng Việt |
| C2 | WHEN `keep_order` có giá trị và tour khả thi THE SYSTEM SHALL thêm ứng viên `kept_order` vào `candidates`: đúng thứ tự đó, mỗi chặng lấy từ ma trận dựng trên **snapshot mới**; `improvement_pct` so với thứ tự nhập như các ứng viên khác. `chosen` và `optimal.gap_pct` **không** tính `kept_order` |
| C3 | Mỗi `TourCandidate` thêm `edge_geometries` (hình học từng cạnh, cùng thứ tự `edge_ids`) và `edge_twin_ids` (cạnh đối hoặc `null`), cùng định nghĩa với `/api/route` |
| C4 | IF tour không khả thi THEN response như hiện tại (`infeasible_under_model`, `unreachable`), không có `candidates`; UI báo **tên** các điểm giao không tới được từ kho hoặc không quay về được kho, rồi mới đến danh sách cặp; không vẽ tour |
| C5 | Ở chế độ tour, bấm một đoạn trên tour đang vẽ → đóng đoạn đó và cạnh đối (giống chế độ tìm đường), tô đỏ nét đứt, gọi lại `/api/tour` với `blocked_edge_ids` và `keep_order` = thứ tự của thẻ đang xem trước khi đóng. Nút "Mở lại tất cả" xóa cạnh đóng và lập lại tour ban đầu (không gửi `keep_order`) |
| C6 | Thẻ "Giữ thứ tự cũ" hiện cạnh ba thẻ hiện có khi response có `kept_order`; ghi rõ đây là thứ tự trước khi đóng đường |
| C7 | `data/demo/cases.json` thêm case `tour-khong-kha-thi`: kho + 5 điểm của `kho-5-diem`, kèm cạnh đóng sẵn làm một điểm giao không tới được; UI nạp case thì gửi cạnh đóng sẵn |

## Ví dụ chấp nhận (đồ thị demo `hcm-benthanh-r2000-20261024`; số cụ thể ghi lại khi chạy, nguồn là response API)

| Thao tác | Phải ra | Nguồn |
|---|---|---|
| `/api/tour` case `kho-5-diem`, không có trường mới | Giống hệt trước: 1.066,0 / 1.003,3 / 898,1 s; không có `kept_order` | Phải giữ nguyên, T72 |
| Như trên, đóng một cạnh giữa của tour NN + 2-opt (kèm cạnh đối), `keep_order` = thứ tự NN + 2-opt cũ | `status = ok`; không ứng viên nào chứa cạnh đóng; `kept_order.stop_order` = thứ tự cũ; `kept_order.cost_s` ≥ 898,1 s (đóng cạnh chỉ làm đường dài ra); `chosen` ∈ {input, NN, NN + 2-opt} | C1, C2; bất biến đơn điệu |
| `keep_order` thiếu một id / có id lạ / trùng id | 422, thông báo tiếng Việt | C1 |
| Trên `mini.json`: đóng A→T, tour S, A, T, B | `infeasible_under_model`; `unreachable` có cặp đi ra từ A; không có `candidates` | C4, test T72 sẵn có |
| `edge_geometries` của mỗi ứng viên | Nối lại ra đúng `geometry`; `edge_twin_ids` cùng độ dài `edge_ids` | C3 |
| UI: case `kho-5-diem` → bấm một đoạn trên tour | Đoạn đỏ; xuất hiện thẻ "Giữ thứ tự cũ"; số trên 4 thẻ khớp response; tour vẽ không đi qua đoạn đỏ | C5, C6 |
| UI: "Mở lại tất cả" | Về đúng 1.066,0 / 1.003,3 / 898,1 s; mất thẻ "Giữ thứ tự cũ" | C5 |
| UI: case `tour-khong-kha-thi` | Banner nêu tên điểm giao hỏng; không vẽ tour | C4, C7 |
| `pytest -q`, `tsc --noEmit`, `npm run build` | Đạt | — |

Kiểm UI bằng Playwright (bấm thật, đọc số trên trang), ghi bảng bằng chứng trong PR.

## Plan

- **Backend:** `schemas.py` thêm `keep_order` (validator hoán vị), `edge_geometries`, `edge_twin_ids`; `services/tour.plan_tour()` thêm ứng viên `kept_order` sau khi có ma trận, dùng chung `legs`; hình học từng cạnh qua `routing.edge_coords`, cạnh đối qua bảng `twins` dựng lúc khởi động (truyền vào như `/api/route`).
- **Frontend:** `api.ts` thêm kiểu; `layers.drawTour()` nhận ứng viên, vẽ vùng bấm từng cạnh, dùng lại cách chọn cạnh gần con trỏ của `drawRoutes`; `App.tsx` chế độ tour có `closed` riêng, gửi `blocked_edge_ids` + `keep_order`; `TourResults.tsx` thêm thẻ và tóm tắt điểm hỏng.
- **Test:** `tests/test_api_tour.py` thêm ví dụ C1–C4 trên `mini.json`; test `realdata` cho case `kho-5-diem` đóng một cạnh; Playwright cho C5–C7.

## Kết quả kiểm chứng (14/11, Tiến)

Backend nhánh `r1-tour-closure` với `SAIGO_GRAPH` = `hcm-benthanh-r2000-20261024`, Vite dev, Chromium điều khiển bằng Playwright (bấm chuột thật lên nét bấm của cạnh, đọc số trên trang và response).

| Ví dụ | Kết quả | |
|---|---|---|
| Không gửi trường mới | Đúng ba ứng viên; `kho-5-diem` 1.066,0 / 1.003,3 / 898,1 s như trước | Đạt |
| `mini.json`, đóng S→B, thứ tự cũ B, A, T | `kept_order` 360 s (tính tay: 130 + 90 + 40 + 100); NN 180 s vẫn được chọn; mọi ứng viên nối tiếp đúng chiều, chi phí = tổng trọng số, không qua S→B | Đạt |
| `kept_order` không được chọn, không tính gap | `chosen` ∈ ba phương án cũ; `gap_pct` tính theo phương án được chọn | Đạt |
| `keep_order` sai (thiếu, thừa, trùng, id lạ, rỗng) | 422, thông báo nêu `keep_order` | Đạt (5 dạng) |
| Không khả thi kèm `keep_order` | `infeasible_under_model`, không có ứng viên | Đạt |
| `edge_geometries`, `edge_twin_ids` | Nối lại đúng `geometry`; cạnh đối của S→B là B→S | Đạt |
| Đồ thị thật, đóng cạnh giữa tour NN + 2-opt (cạnh 2789) | `kept_order` 898,8 s ≥ 898,1 s, giữ đúng thứ tự cũ; không ứng viên nào qua cạnh đóng | Đạt |
| UI: bấm cạnh giữa tour | Một request có `blocked_edge_ids` [2789] và `keep_order` = thứ tự thẻ đang xem; đoạn đỏ; "Đang đóng 1 cạnh"; số 4 thẻ khớp response | Đạt |
| UI: bước 10 của demo, bấm cạnh 1666 | Giữ thứ tự cũ 962,7 s; sắp lại NN + 2-opt 692,5 s (Tao Đàn → Nhà thờ → Nhà hát → Bạch Đằng → Bảo tàng); khớp `cases.json` và test `realdata` | Đạt |
| UI: Mở lại tất cả | Về 1.066,0 / 1.003,3 / 898,1 s; không gửi `keep_order`; mất thẻ giữ thứ tự cũ | Đạt |
| UI: case `tour-khong-kha-thi` | "Không tới được từ kho: Nhà hát Thành phố"; không vẽ tour, không còn vùng bấm | Đạt |
| Hồi quy chế độ tìm đường | Case "Hai điểm qua trung tâm" 186,1 s | Đạt |
| `pytest -q`, `tsc --noEmit`, `npm run build` | 442 passed, 6 skipped; tsc sạch; build OK | Đạt |

**Giới hạn và ghi chú:**
- Sau khi đóng cạnh 1666, phương án sắp lại (692,5 s) rẻ hơn cả tour trước khi đóng (898,1 s). Không phải vì đóng đường có lợi: tour NN + 2-opt cũ là cực trị địa phương kém (tối ưu 627,8 s, gap 43%); ma trận đổi làm NN xuất phát theo hướng khác. Khi trình bày phải nói rõ điều này.
- Ở khung nhìn mặc định, vài cạnh của tour nằm ngoài vùng bản đồ (bị cột kết quả che); khi demo cần thu nhỏ một mức trước khi bấm cạnh 1666.
- Cạnh đóng sẵn của case (`tour-khong-kha-thi`) không tô đỏ, vì UI chỉ có id, không có hình học (giống case "Không còn đường" của T56).

## Ngoài phạm vi

Đóng đường giữa chừng khi shipper đã đi được một phần tour; tour mở; nhiều shipper. Thí nghiệm hàng loạt "giữ thứ tự cũ / sắp lại" thuộc R2.
