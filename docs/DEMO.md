# Kịch bản demo

Cập nhật 26/10 theo [đề xuất đổi phạm vi](proposals/2026-10-26-pham-vi.md) đã duyệt: bản đồ rút gọn (D12); tour giữ lại chiều 26/10 (D10) nhưng là chế độ phụ, chỉ ở bước 9. Kịch bản ngắn nằm ở [PROJECT_BRIEF](PROJECT_BRIEF.md) mục 7; file này mô tả giao diện và checklist. Bản trước (xoay quanh tour, theo [TOPIC.md](TOPIC.md) mục 13 và 19) không còn dùng.

Mọi số hiển thị đều lấy từ response của backend; không có số viết tay.

## 1. Bố cục giao diện

```
┌──────────────┬──────────────────────────────────┬────────────────┐
│ Bảng điều    │                                  │ Kết quả        │
│ khiển        │   Bản đồ Leaflet (nền tile OSM)  │ đo được        │
│              │                                  │                │
│ Chế độ       │  điểm đi, điểm đến, tuyến,       │ Dijkstra / A*  │
│ Case demo    │  kho + điểm giao (chế độ tour),  │ Thẻ tour       │
│ Kịch bản     │  vùng ùn tắc, đoạn bị đóng       │                │
│ [Tìm đường]  │                                  │ Nhật ký        │
│ [Mở lại hết] │                                  │ snapshot       │
└──────────────┴──────────────────────────────────┴────────────────┘
```

### 1.1. Cột trái — bảng điều khiển

- Chế độ: **Tìm đường hai điểm** (mặc định) / **Tour**.
- Case demo chọn sẵn: "Hai điểm qua trung tâm", "Không còn đường", "Kho + 5 điểm giao".
- Kịch bản: Bình thường / Cao điểm mô phỏng — trung tâm (`peak-center`).
- Nút **Tìm đường** (chạy cả Dijkstra và A*), nút **Mở lại các đoạn đã đóng**.

### 1.2. Giữa — bản đồ

| Thành phần | Cách hiển thị |
|---|---|
| Điểm đi, điểm đến | Marker tại node đã snap; tooltip ghi khoảng cách snap |
| Tuyến | Đường xanh theo hình học thật của cạnh (`[lon, lat]` đổi sang `[lat, lon]`) |
| Vùng ùn tắc | Hình tròn tô màu nhạt khi chọn kịch bản cao điểm |
| Đoạn bị đóng | Đỏ, nét đứt; tooltip "Đoạn đường bị đóng do người dùng đánh dấu" |

Bấm vào một đoạn **trên tuyến** để đóng (đóng cả cạnh đối nếu có), rồi tìm lại. Không vẽ toàn bộ mạng đường và không có lớp chấm node đã mở rộng (D12). Không vẽ đường thẳng nối hai điểm khi không có đường.

### 1.3. Cột phải — kết quả đo được

**Khối Dijkstra / A\*** (trả lời RQ1): thời gian di chuyển ước tính, quãng đường, số node mở rộng, thời gian tính toán, và dòng "Chi phí trùng khớp: có/không".

**Thẻ so sánh tour** (chế độ tour, RQ2): Thứ tự nhập / Nearest Neighbor / NN + 2-opt; mỗi thẻ có thời gian di chuyển ước tính, quãng đường, mức cải thiện so với thứ tự nhập. Marker điểm giao đánh số theo thẻ đang chọn.

**Nhật ký snapshot**: mỗi dòng là một sự kiện thật của backend, ví dụ "Tạo snapshot `peak-center`", "Đóng cạnh (u, v, key)", "Không có đường".

### 1.4. Nhãn bắt buộc

- Tách **Thời gian di chuyển ước tính theo kịch bản** và **Thời gian tính toán**; không có nhãn "Time" chung.
- Kịch bản cao điểm ghi "Cao điểm mô phỏng".
- Ghi tên thuật toán cụ thể (Dijkstra, A*, NN, 2-opt).

### 1.5. Không đưa vào

- Số liệu không do hệ thống đo (độ tin cậy dự báo, % giảm ùn tắc, …).
- Giao thông thời gian thực, điều khiển đèn tín hiệu, bản tin giao thông.
- Animation trace, lớp chấm node đã mở rộng (đã cắt 26/10).

## 2. Kịch bản demo khoảng 4 phút

Giữ đúng số bước của [PROJECT_BRIEF](PROJECT_BRIEF.md) mục 7; bước 3 đã cắt. Mọi case phải chạy thử trước trên đúng snapshot sẽ dùng và được ghi rõ là case minh họa.

| Bước | Thao tác | Giao diện hiển thị | Người xem hiểu |
|---|---|---|---|
| 1 | Chọn case "Hai điểm qua trung tâm" | Nền OSM vùng demo, 2 marker đã snap | Bài toán: đồ thị có hướng thật, chi phí là giây |
| 2 | Bấm **Tìm đường** | Tuyến; khối Dijkstra/A*: chi phí bằng nhau, A* mở rộng ít node hơn | A* cho cùng chi phí tối ưu (RQ1) |
| 4 | Đảo chiều đi/đến | Tuyến và chi phí khác chiều ban đầu | Đường một chiều: A→B ≠ B→A |
| 5 | Chọn kịch bản "Cao điểm mô phỏng — trung tâm" | Vùng ùn tắc; tuyến đổi sang đường vòng; chi phí tăng | Ùn tắc theo vùng làm đổi lựa chọn (RQ3) |
| 6 | Bấm vào một đoạn trên tuyến → **Đóng đoạn đường** | Đoạn đỏ; tuyến mới; dòng nhật ký mới | Lập lại tuyến, không dùng cạnh bị đóng (RQ3) |
| 7 | Chọn case "Không còn đường" | Thông báo không có đường; không vẽ đường thẳng | Hệ thống báo đúng giới hạn (RQ3) |
| 8 | Chuyển sang slide biểu đồ tăng quy mô | `expanded` và thời gian theo `|V|` (4 kích thước, fixed trips) | Số đo thật (RQ1b) |
| 9 | Chuyển sang chế độ tour, case "Kho + 5 điểm giao"; chọn lần lượt 3 thẻ | Thứ tự giao đổi; chi phí trước/sau | Tầng thứ hai của bài toán (RQ2) |

Nếu khoản cắt 4 của đề xuất phạm vi được nhóm đồng ý (đóng đường qua API/CLI thay vì bản đồ), bước 6 đổi theo; hiện **chưa** kích hoạt.

## 3. Checklist trước buổi demo

- [ ] Ba case demo đã chạy trên đúng snapshot sẽ dùng và cho kết quả như kịch bản.
- [ ] Số trong khối Dijkstra/A* và thẻ tour khớp với response API, không có số viết tay.
- [ ] Đóng đoạn rồi bấm **Mở lại** trả về đúng tuyến ban đầu.
- [ ] Ghi nguồn © OpenStreetMap contributors hiển thị trên bản đồ.
- [ ] Có bản quay màn hình dự phòng nếu máy demo lỗi.
