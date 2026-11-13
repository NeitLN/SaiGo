# T14 — Skeleton phía bản đồ: bấm 2 điểm, vẽ tuyến

Tuần mục tiêu: 2 (27–28/10) · Giao cho: Minh · Nhánh: `t14-map-skeleton` · Issue: [#50](https://github.com/NeitLN/SaiGo/issues/50)
Review: Tiến · Người tích hợp: Tiến
Phụ thuộc: contract v1 (**bắt đầu**, đã chốt) · T13 (**tích hợp**: code trước với response mẫu, nối API thật khi T13 xong; Minh làm cả T13) · Ước lượng: 3 giờ

## Mục tiêu
Trình duyệt gọi API thật và vẽ đúng tuyến trên nền OSM.

## Việc cần làm
1. **`frontend/src/api.ts`:** kiểu `RouteRequest` / `RouteResponse` đúng theo contract v1; hàm `postRoute()`. Trong lúc T13 chưa merge, dùng một response mẫu (`cost_s` 80, tuyến S→A→T theo tọa độ của `mini.json`) để vẽ.
2. **`frontend/src/main.ts`:**
   - bấm lần 1 là điểm đi, lần 2 là điểm đến, lần 3 bắt đầu lại;
   - gọi `postRoute()`;
   - vẽ polyline, đổi `[lon, lat]` sang `[lat, lon]`;
   - hiện "Thời gian di chuyển ước tính" (s) và "Số node mở rộng";
   - API lỗi thì hiện lỗi;
   - bỏ qua response cũ nếu đã có request mới.
3. Căn bản đồ quanh Bến Thành; giữ ghi nguồn OSM.

## Sở hữu (chỉ task này được tạo/sửa) trong tuần 2
- `frontend/src/main.ts`, `api.ts`, `style.css`
- `frontend/src/layers.ts` (nếu tạo)

## Dùng (chỉ đọc)
- Contract v1
- Tọa độ trong `tests/fixtures/mini.json` (T01)

## Tiêu chí chấp nhận
- [ ] **28/10 tối:** chạy cùng API của T13 trên máy Minh, Tiến làm lại khi review; bấm gần S rồi gần T thấy tuyến S→A→T nằm đúng quanh chợ Bến Thành, hiện 80 s; đảo lại hiện 100 s
- [ ] `npm run build` không lỗi
- [ ] Không vẽ đường thẳng khi API trả `no_path`

## Ngoài phạm vi
Bảng so sánh Dijkstra/A* (T52); chọn kịch bản, đóng đường (tuần 3); vẽ toàn bộ mạng đường (T32, đã cắt 26/10).
