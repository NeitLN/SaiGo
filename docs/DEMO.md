# Kịch bản demo

Cập nhật 26/10 theo [đề xuất đổi phạm vi](proposals/2026-10-26-pham-vi.md) đã duyệt: bản đồ rút gọn (D12); tour giữ lại chiều 26/10 (D10) nhưng là chế độ phụ, chỉ ở bước 9. Kịch bản ngắn nằm ở [PROJECT_BRIEF](PROJECT_BRIEF.md) mục 7; file này mô tả giao diện và checklist. Bản trước (xoay quanh tour, theo [TOPIC.md](TOPIC.md) mục 13 và 19) không còn dùng.

**Cập nhật 14/11 (D15, D18):** giao diện là React + Astryx (T56, #103). Bỏ nhật ký snapshot (không thêm bằng chứng cho RQ nào; dòng "Kịch bản: …" trong khối kết quả ghi kịch bản và số cạnh đang đóng). Thêm bước 10–11: lập lại tour sau khi đóng đường, đúng câu chuyện "một kho, 5 điểm giao, một đường bị đóng" của proposal. Hai bước này làm ở R1 ([phiếu R1](tasks/R1-tour-closure.md)).

**Cập nhật 15/11 (test lại toàn app, 6 tester):** mục 1 viết lại theo giao diện hiện tại (tên nút, ô chọn, thẻ Held–Karp, công tắc Phần mở rộng, bố cục theo độ rộng). Mục 2: bước 5 làm ở chiều ban đầu (sau bước 4 phải bấm Đảo chiều lần nữa, nếu không tuyến không đổi); bước 6 đóng một đoạn cố định để số lặp lại được; thêm thời lượng từng bước. Số trong file đo trên `hcm-benthanh-r2000-20261024`.

Mọi số hiển thị đều lấy từ response của backend; không có số viết tay.

## 1. Bố cục giao diện

Bố cục đổi theo độ rộng cửa sổ:

| Độ rộng | Bố cục |
|---|---|
| ≥ 1440 px | Ba cột: điều khiển (300 px) · bản đồ · kết quả (360 px) |
| 768–1439 px (máy chiếu 1024/1280, laptop 1366) | Hai cột: cột trái 360 px gồm điều khiển rồi kết quả, bản đồ bên phải. Có **dòng tóm tắt kết quả** ngay dưới chọn chế độ (vd. "Tìm xong: 186,1 giây, 1.565 mét. Dijkstra mở 404 node, A* mở 106 node. So với lần trước: …"), nên người xem thấy số mà không cần cuộn |
| < 768 px | Bản đồ ở trên, điều khiển và kết quả xếp dưới |

```
≥ 1440 px
┌──────────────┬──────────────────────────────────┬────────────────┐
│ Chế độ       │                                  │ Kết quả        │
│ Lộ trình mẫu │   Bản đồ Leaflet (nền Esri xám,  │ đo được        │
│ Điểm, điều   │   OSM hoặc nền rút gọn)          │ Dijkstra / A*  │
│ Địa danh     │   điểm, tuyến, vùng ùn tắc,      │ Thẻ tour       │
│ Nút, công tắc│   đoạn đóng, chú giải nổi        │ So với lần trước│
└──────────────┴──────────────────────────────────┴────────────────┘
```

### 1.1. Bảng điều khiển

- Chế độ: **Tìm đường** (mặc định) / **Tour**.
- **Lộ trình mẫu** (5 mẫu; trước 15/11 gọi là "Case demo"): "Hai điểm qua trung tâm", "Không còn đường", "Kho + 5 điểm giao", "Kho + 5 điểm, đóng đường gần Bến Bạch Đằng" (bước 10), "Tour không còn khả thi" (bước 11). Chọn mẫu là app tự chạy, tự thu phóng, và đặt kịch bản về cơ sở. Ô case nhớ riêng theo chế độ; Đảo chiều hay Mở lại tất cả làm ô về trống vì kết quả không còn là case đó.
- **Điều kiện giao thông** (3; trước 15/11 gọi là "Kịch bản"): **Cơ sở — không ùn tắc, không đóng đường**, **Cao điểm mô phỏng — trung tâm** (`peak-center`), **Cao điểm mô phỏng — vòng xoay Bến Thành**. Điều kiện giữ nguyên khi bấm Xóa.
- **Đặt điểm từ địa danh**: chọn Dinh Độc Lập, Chợ Bến Thành, Nhà thờ Đức Bà… thay vì bấm bản đồ. Mỗi điểm (bấm hay chọn) được kiểm ngay (`/api/snap`): xa đường quá 150 m thì bị từ chối kèm khoảng cách; trong lúc kiểm có dòng "Đang kiểm điểm vừa chọn…" và các nút tìm/lập bị khoá.
- Tìm đường: nút **Tìm đường** (chạy Dijkstra và A*), **Đảo chiều**, **Xóa**. Tour: **Lập tour**, **Bỏ điểm cuối**, **Xóa**.
- Khi có cạnh đóng: dòng "Đang đóng N cạnh" và nút **Mở lại tất cả**.
- Ô **Đóng một đoạn trên tuyến / tour**: liệt kê từng đoạn ("Đoạn 10/18: … m, bắt đầu cách điểm đi … m"); chọn một đoạn như bấm vào nó trên bản đồ. Dùng được bằng bàn phím.
- Khối thu gọn **Phân tích thuật toán** (đóng sẵn) chứa công tắc **Hiện node đã mở rộng** (chế độ Tìm đường, mặc định tắt) và **Phần mở rộng** (mặc định tắt; thêm ALT, Dijkstra hai chiều vào bảng phụ, và thẻ NN + 2-opt + Or-opt cho tour). Phần mở rộng **giữ trạng thái khi đổi chế độ**: nhớ tắt trước bước 9 nếu đã bật khi hỏi đáp.

### 1.2. Bản đồ

| Thành phần | Cách hiển thị |
|---|---|
| Điểm đi, điểm đến | Pin xanh "Đi", pin đỏ "Đến" tại node đã snap; nhãn chỉ ghi khoảng cách snap khi lớn hơn 15 m |
| Tuyến | Dijkstra và A* trùng nhau: một nét xanh có viền xanh đậm, chevron trắng chỉ chiều (chú giải ghi "Dijkstra và A* trùng tuyến"); khác nhau: Dijkstra nét xanh liền, A* nét cam đứt |
| Tuyến lần trước | Nét "rỗng" (viền xám, lõi trắng) khi cùng hai điểm mà đổi điều kiện giao thông hoặc cạnh đóng; khi lần này không còn đường, đó là tuyến cũ nay không đi được |
| Vùng ùn tắc | Hình tròn viền nâu liền, tô vàng rất nhạt; nhãn ngắn "Cao điểm mô phỏng ×2" ở mép trên; hệ số và loại đường đầy đủ ghi ở chú giải |
| Đoạn đang đóng | Đỏ nét đứt có viền sáng, nằm trên tuyến và dưới marker; hiện ngay khi bấm, không chờ kết quả |
| Tour | Nét tím có viền, chevron trắng chỉ chiều; kho là ô vuông xanh "K"; điểm giao là vòng tím đánh số theo thẻ đang xem, tên đặt cạnh số |
| Điểm không đi được | Marker tô đỏ (tour không khả thi); app tự thu phóng vào điểm hỏng và đoạn đóng |
| Vùng có dữ liệu | Phần ngoài khung phủ mờ, viền mảnh; đặt điểm trong khung mới snap được; bản đồ không kéo xa khỏi vùng |
| Chú giải và nút | Chú giải có tiêu đề ở góc dưới trái, chỉ liệt kê những gì đang vẽ; dưới nút zoom có nút "Về toàn tuyến" (thu phóng lại vừa kết quả) |
| Nền bản đồ | Thứ tự: Esri Light Gray (xám nhạt, có tên đường; ảnh tới zoom 16, phóng to từ đó) → OSM → **nền rút gọn** tự vẽ từ `/api/network` (đường trắng ba cấp theo loại đường, nhãn nhỏ "Nền rút gọn từ dữ liệu đồ thị" góc trên phải; không có tên đường). Nguồn nào lỗi cả lượt tải hoặc treo 6 s thì sang nguồn kế; tile tải lại được thì nền rút gọn tự gỡ. Luôn ghi "Dữ liệu tuyến © OpenStreetMap contributors" cùng nguồn của nền đang dùng |

Rê chuột lên tuyến thì đoạn sẽ đóng tô đỏ kèm "Bấm để đóng đoạn đang tô đỏ"; **bấm một lần là đóng** (không có nút xác nhận), cả cạnh đối nếu có, rồi tìm lại. Bấm trượt ra ngoài tuyến khi đang có kết quả không xoá gì (chỉ hiện gợi ý bấm Xóa). Bản đồ luôn dùng màu sáng, kể cả khi máy để chế độ tối. Không vẽ đường thẳng nối hai điểm khi không có đường.

### 1.3. Kết quả đo được

**Ô số chính** (đợt UI 15/11): thời gian di chuyển ước tính (phút, dòng phụ ghi giây và "theo điều kiện giao thông") và quãng đường (km, dòng phụ ghi mét); với tour là của phương án **đang xem**. Ở 768–1439 px có dải ô số này ngay dưới chọn chế độ. **Bảng so sánh thuật toán** (RQ1): khi Dijkstra và A* cùng chi phí, bảng chỉ còn số node mở rộng và thời gian tính toán (1 lần chạy), vì thời gian di chuyển và quãng đường đã ở ô số chính; khác chi phí thì bảng ghi đủ cả bốn dòng; dòng "Chi phí trùng khớp: có/không" và "Ở truy vấn này, A* mở …% số node của Dijkstra". Khi bật Phần mở rộng có bảng phụ ALT / Hai chiều.

**So với lần trước** (cùng điểm, khác điều kiện giao thông hoặc cạnh đóng): "186,1 s → 246,1 s: +60,0 s (+32,2%)", dòng phụ ghi điều kiện lần trước và lần này. Lưu ý: so với **lần ngay trước**, không phải với Cơ sở.

**Kết quả tour** (RQ2): khung **Đang xem** ở đầu: tên phương án, nhãn "Được chọn" hoặc "Đối chứng", ô số chính, dòng "N điểm giao · gồm chặng về kho · nhanh hơn thứ tự nhập X%", và **lịch trình** Kho → 1 … n → về kho, đánh số khớp marker (không có giờ đến từng điểm: API chỉ trả tổng). Dưới là **Các phương án**: Thứ tự nhập · Nearest Neighbor · NN + 2-opt (phương án được chọn) · Held–Karp (tham chiếu tối ưu, chỉ để đối chứng) khi tổng số điểm ≤ 11 · NN + 2-opt + Or-opt khi bật Phần mở rộng; mỗi phương án một dòng phút · km, nút **Xem trên bản đồ**. Badge "Thời gian ước tính thấp nhất" gắn mọi phương án có chi phí thấp nhất, nên Held–Karp cũng có thể mang badge. Sau khi đóng đường có thêm **Giữ thứ tự cũ** (đứng đầu) và dòng "Cùng thứ tự, trước khi đóng" (chỉ khi lần này cùng điều kiện giao thông và chỉ đóng thêm đoạn). Dòng cuối: "Tham chiếu tối ưu (Held–Karp): …; phương án được chọn chậm hơn tối ưu X%".

**Dòng điều kiện**: "Điều kiện giao thông: <tên>", thêm "; đóng N cạnh" khi đang đóng cạnh.

### 1.4. Nhãn bắt buộc

- Tách **Thời gian di chuyển ước tính (theo điều kiện giao thông)** và **Thời gian tính toán**; không có nhãn "Time" chung.
- Kịch bản cao điểm ghi "Cao điểm mô phỏng".
- Ghi tên thuật toán cụ thể (Dijkstra, A*, NN, 2-opt, Held–Karp).

### 1.5. Không đưa vào

- Số liệu không do hệ thống đo (độ tin cậy dự báo, % giảm ùn tắc, …).
- Giao thông thời gian thực, điều khiển đèn tín hiệu, bản tin giao thông.
- Animation trace (đã cắt 26/10). Lớp chấm node đã mở rộng ở dạng tĩnh, có công tắc, mặc định tắt.

## 2. Kịch bản demo khoảng 4 phút

Giữ đúng số bước của [PROJECT_BRIEF](PROJECT_BRIEF.md) mục 7; bước 3 đã cắt. Mọi case phải chạy thử trước trên đúng snapshot sẽ dùng và được ghi rõ là case minh họa. Máy chiếu 1280 × 800 dùng bố cục hai cột: số chính nằm ở dòng tóm tắt đầu cột trái; bảng chi tiết phải cuộn cột trái xuống.

| Bước | Thao tác | Giao diện hiển thị | Người xem hiểu | Thời lượng |
|---|---|---|---|---|
| 1–2 | Chọn lộ trình mẫu "Hai điểm qua trung tâm" (app tự chạy) | 2 marker đã snap, tuyến; 186,1 s, 1.565 m; Dijkstra 404 node, A* 106 node; "Chi phí trùng khớp: có" | Đồ thị có hướng thật, chi phí là giây; A* cùng chi phí tối ưu, mở ít node hơn (RQ1) | ~45 s |
| 4 | Bấm **Đảo chiều** | 193,0 s, 1.417 m; 477 / 108 node | Đường một chiều: A→B ≠ B→A | ~20 s |
| 5 | Bấm **Đảo chiều** lần nữa (về Dinh Độc Lập → Bitexco), rồi chọn điều kiện giao thông "Cao điểm mô phỏng — trung tâm" | Vùng ùn tắc; tuyến đổi sang đường vòng, tuyến cũ vẽ xám; "186,1 s → 246,1 s: +60,0 s (+32,2%)", 1.748 m | Ùn tắc theo vùng làm đổi lựa chọn (RQ3). Nếu quên đảo lại thì tuyến chiều ngược không đổi (193,0 → 300,0 s) | ~35 s |
| 6 | Ở ô **Đóng một đoạn trên tuyến**, chọn "Đoạn 10/18" (hoặc bấm đoạn đó trên bản đồ) | Đoạn đỏ; tuyến mới 302,3 s, 2.118 m; "246,1 s → 302,3 s"; "Đang đóng 1 cạnh" | Lập lại tuyến, không dùng cạnh bị đóng (RQ3) | ~25 s |
| 7 | Chọn lộ trình mẫu "Không còn đường" | Thông báo không có đường; không vẽ đường thẳng; Dijkstra và A* cùng mở 1.762 node | Hệ thống báo đúng giới hạn (RQ3); khi không còn đường, A* duyệt như Dijkstra | ~20 s |
| 8 | Chuyển sang slide biểu đồ tăng quy mô | `expanded` và thời gian theo `|V|` (4 kích thước, fixed trips) | Số đo thật (RQ1b) | ~30 s |
| 9 | Chế độ **Tour**, lộ trình mẫu "Kho + 5 điểm giao"; bấm **Xem trên bản đồ** ở thẻ Thứ tự nhập rồi NN + 2-opt | 1.066,0 s → 898,1 s, thứ tự giao đổi; thẻ Held–Karp 627,8 s mang "Thời gian ước tính thấp nhất", NN + 2-opt "chậm hơn tối ưu 43,0%" | Tầng thứ hai của bài toán (RQ2). Câu chuẩn bị sẵn: "Held–Karp chỉ để đối chứng, không dùng để chọn tour" | ~45 s |
| 10 | Chọn lộ trình mẫu "Kho + 5 điểm, đóng đường gần Bến Bạch Đằng" (đóng sẵn cạnh 1666, gửi kèm thứ tự trước khi đóng) | Đoạn đỏ; thẻ "Giữ thứ tự cũ" 962,7 s đứng đầu, "Cùng thứ tự, trước khi đóng: 898,1 → 962,7 s (+7,2%)"; NN + 2-opt sắp lại 692,5 s (p5 p1 p2 p4 p3) | Đóng đường làm đổi cả tuyến lẫn thứ tự (RQ3). Sắp lại rẻ hơn tour cũ vì tour cũ là cực trị địa phương kém, không phải vì đóng đường có lợi | ~40 s |
| 11 | Chọn lộ trình mẫu "Tour không còn khả thi" | "Không điểm nào đi tới được Nhà hát Thành phố."; bản đồ phóng vào Nhà hát, marker đỏ, đoạn đóng đỏ; không vẽ tour một phần | Hệ thống không bỏ điểm giao âm thầm (RQ3) | ~20 s |

Tổng khoảng 4 phút 40 giây nếu nói đủ; để vừa 4 phút: ở bước 9 chỉ bấm hai thẻ như trên, bước 10 nói hai câu, bước 6 làm liền sau bước 5 (không mở lại). Đổi lại bước 8 sang cuối nếu cần cắt.

Mẹo khi trình bày:
- Một người cầm chuột. Lăn chuột trên cột trái là cuộn cột, trên bản đồ là thu phóng.
- Bấm trượt lên tuyến là đóng đoạn ngay; lỡ tay thì bấm **Mở lại tất cả**.
- Chọn lại lộ trình mẫu là điều kiện giao thông về Cơ sở; bấm Xóa thì điều kiện giữ nguyên.
- Lớp node đã mở rộng: ở mức thu phóng của case, vùng Dijkstra lan ra ngoài khung, thu nhỏ một mức thì thấy rõ.

Khoản cắt 4 của đề xuất phạm vi 26/10 (đóng đường qua API/CLI thay vì bản đồ) không còn cần: đóng đoạn trên bản đồ đã có (T54, T56).

## 3. Checklist trước buổi demo

- [ ] Năm lộ trình mẫu đã chạy trên đúng snapshot sẽ dùng và cho kết quả như mục 2.
- [ ] Số trong ô số chính, bảng Dijkstra/A* và kết quả tour khớp với response API, không có số viết tay.
- [ ] Đóng đoạn rồi bấm **Mở lại tất cả** trả về đúng tuyến ban đầu.
- [ ] Khối "Phân tích thuật toán" đóng, hai công tắc trong đó đang tắt khi bắt đầu.
- [ ] Ghi nguồn hiển thị trên bản đồ: dữ liệu tuyến © OpenStreetMap contributors và nguồn của nền (Esri hoặc OSM).
- [ ] Có bản quay màn hình dự phòng nếu máy demo lỗi.
- [ ] Đã mở app trên mạng của phòng chiếu: nền Esri hiện; nếu bị chặn cả Esri lẫn OSM thì nền rút gọn hiện và demo vẫn chạy trọn.
- [ ] `/api/dataset` trả đúng `hcm-benthanh-r2000-20261024` (lộ trình mẫu khóa theo dataset này).
