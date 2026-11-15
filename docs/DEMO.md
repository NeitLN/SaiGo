# Kịch bản demo

Cập nhật 26/10 theo [đề xuất đổi phạm vi](proposals/2026-10-26-pham-vi.md) đã duyệt: bản đồ rút gọn (D12); tour giữ lại chiều 26/10 (D10) nhưng là chế độ phụ, chỉ ở bước 9. Kịch bản ngắn nằm ở [PROJECT_BRIEF](PROJECT_BRIEF.md) mục 7; file này mô tả giao diện và checklist. Bản trước (xoay quanh tour, theo [TOPIC.md](TOPIC.md) mục 13 và 19) không còn dùng.

**Cập nhật 14/11 (D15, D18):** giao diện là React + Astryx (T56, #103). Bỏ nhật ký snapshot (không thêm bằng chứng cho RQ nào; dòng "Kịch bản: …" trong khối kết quả ghi kịch bản và số cạnh đang đóng). Thêm bước 10–11: lập lại tour sau khi đóng đường, đúng câu chuyện "một kho, 5 điểm giao, một đường bị đóng" của proposal. Hai bước này làm ở R1 ([phiếu R1](tasks/R1-tour-closure.md)).

**Cập nhật 15/11 (test lại toàn app, 6 tester):** mục 1 viết lại theo giao diện hiện tại (tên nút, ô chọn, thẻ Held–Karp, công tắc Phần mở rộng, bố cục theo độ rộng). Mục 2: bước 5 làm ở chiều ban đầu (sau bước 4 phải bấm Đảo chiều lần nữa, nếu không tuyến không đổi); bước 6 đóng một đoạn cố định để số lặp lại được; thêm thời lượng từng bước. Số trong file đo trên `hcm-benthanh-r2000-20261024`.

Mọi số hiển thị đều lấy từ response của backend; không có số viết tay.

## 1. Bố cục giao diện

**Cập nhật 16/11 (đợt UI "Bàn điều phối", họp thiết kế 9 vai):** một bố cục cho mọi độ rộng từ 768 px.

| Độ rộng | Bố cục |
|---|---|
| ≥ 768 px (máy chiếu 1024/1280, laptop, màn lớn) | Header nền mực có chọn chế độ **Tìm đường / Tour**. Panel trái 360 px ba tầng: **Kết quả đo được** (ô số chính, "So với lần trước", luôn thấy) / phần giữa cuộn được (lộ trình mẫu, điểm, đóng đoạn) / đáy dính (**Điều kiện giao thông** và nút chính). Bản đồ bên phải, **khay phân tích** 220 px dưới bản đồ (bảng thuật toán hoặc các phương án tour), nút **Ẩn khay / Hiện khay**; thu gọn thì bản đồ cao lên và tự thu phóng lại vừa tuyến |
| < 768 px | Bản đồ ở trên, rồi kết quả, điều kiện giao thông và nút chính, điều khiển, khay phân tích xếp dọc |

```
≥ 768 px (vd. 1280 × 800)
┌──────────────────────────────────────────────────────────────────┐
│ SaiGo  [Tìm đường | Tour]                           ● Đã kết nối │
├──────────────┬───────────────────────────────────────────────────┤
│ Kết quả đo   │                                                   │
│ được (số)    │   Bản đồ Leaflet (Esri Đường phố / Xám, OSM hoặc  │
├──────────────┤   nền rút gọn): điểm, tuyến, vùng ùn tắc, đoạn    │
│ Lộ trình mẫu │   đóng, chú giải nổi                              │
│ Điểm, địa    │                                                   │
│ danh, đóng   ├───────────────────────────────────────────────────┤
│ đoạn (cuộn)  │ Phân tích thuật toán / So sánh phương án  [Thu gọn]│
├──────────────┤ bảng Dijkstra / A*, hoặc thẻ tour và các phương án│
│ Điều kiện GT │                                                   │
│ [Tìm đường]  │                                                   │
└──────────────┴───────────────────────────────────────────────────┘
```

### 1.1. Bảng điều khiển

- Chế độ: **Tìm đường** (mặc định) / **Tour**, ở header.
- **Lộ trình mẫu** (16/11: danh sách bấm một lần ở cuối phần giữa của panel, chỉ các mẫu của chế độ đang dùng; trước 15/11 gọi là "Case demo"): Tìm đường có "Hai điểm qua trung tâm", "Không còn đường"; Tour có "Kho + 5 điểm giao", "Kho + 5 điểm, đóng đường gần Bến Bạch Đằng" (bước 10), "Tour không còn khả thi" (bước 11). Bấm là app tự chạy, tự thu phóng, và đặt điều kiện giao thông theo mẫu; mẫu đang mở có dấu chọn. Đảo chiều hay Mở lại tất cả làm mẫu bỏ chọn vì kết quả không còn là mẫu đó. Lúc chưa có kết quả, khay phân tích cũng có nút "Mở lộ trình mẫu".
- **Điều kiện giao thông** (16/11: nhóm chip một lựa chọn ở đáy panel, cạnh nút chính; trước 15/11 gọi là "Kịch bản"): **Cơ sở**, **Cao điểm — trung tâm** (`peak-center`), **Cao điểm — Bến Thành**; rê chuột lên chip thấy tên đầy đủ ("Cao điểm mô phỏng — vòng xoay Bến Thành"). Đã có kết quả thì đổi chip là tính lại ngay. Dùng bàn phím: Tab tới nhóm, phím mũi tên chuyển chip. Nhiều hơn 4 điều kiện thì trở lại ô chọn. Điều kiện giữ nguyên khi bấm Xóa.
- **Đặt điểm từ địa danh**: chọn Dinh Độc Lập, Chợ Bến Thành, Nhà thờ Đức Bà… thay vì bấm bản đồ. Mỗi điểm (bấm hay chọn) được kiểm ngay (`/api/snap`): xa đường quá 150 m thì bị từ chối kèm khoảng cách; trong lúc kiểm có dòng "Đang kiểm điểm vừa chọn…" và các nút tìm/lập bị khoá.
- Tìm đường: nút **Tìm đường** (chạy Dijkstra và A*) và **Xóa** ở đáy panel, **Đảo chiều** dưới hai điểm. Tour: **Lập tour** và **Xóa** ở đáy, **Bỏ điểm cuối** dưới danh sách điểm.
- Khi có cạnh đóng: dòng "Đang đóng đường (N cạnh có hướng)" (một đoạn hai chiều là 2 cạnh) và nút **Mở lại tất cả**.
- Ô **Đóng một đoạn trên tuyến / tour**: liệt kê từng đoạn, có tên đường khi dữ liệu OSM có (16/11; khoảng 82% cạnh của vùng demo, hẻm và đường nhánh thường không tên), ví dụ ("Đoạn 10/18: <tên đường>, … m, bắt đầu cách điểm đi … m"); chọn một đoạn như bấm vào nó trên bản đồ. Dùng được bằng bàn phím.
- Đầu khay phân tích có công tắc **Hiện node đã mở rộng** (chế độ Tìm đường, mặc định tắt) và **Phần mở rộng** (mặc định tắt; thêm ALT, Dijkstra hai chiều vào bảng phụ, và thẻ NN + 2-opt + Or-opt cho tour). Phần mở rộng **giữ trạng thái khi đổi chế độ**: nhớ tắt trước bước 9 nếu đã bật khi hỏi đáp.

### 1.2. Bản đồ

| Thành phần | Cách hiển thị |
|---|---|
| Điểm đi, điểm đến | Điểm đi là vòng tròn xanh chữ **A**, điểm đến là pin đỏ chữ **B**, tại node đã snap (16/11). Tên địa danh in cạnh ký hiệu bằng chữ có quầng trắng (điểm bấm trên bản đồ thì ghi "Điểm đi" / "Điểm đến"); khoảng cách snap chỉ ghi khi lớn hơn 15 m |
| Tuyến | Dijkstra và A* trùng nhau: một nét xanh có viền xanh đậm, chevron trắng chỉ chiều (chú giải ghi "Dijkstra và A* trùng tuyến"); khác nhau: Dijkstra nét xanh liền, A* nét cam đứt |
| Tuyến lần trước | Nét "rỗng" (viền xám, lõi trắng) khi cùng hai điểm mà đổi điều kiện giao thông hoặc cạnh đóng; khi lần này không còn đường, đó là tuyến cũ nay không đi được |
| Vùng ùn tắc | Hình tròn viền nâu nét đứt mảnh, tô vàng rất nhạt; nhãn ngắn "Cao điểm ×2" ở mép trên; hệ số và loại đường đầy đủ ghi ở chú giải |
| Đoạn đang đóng | Đỏ nét đứt có viền sáng, nằm trên tuyến và dưới marker; hiện ngay khi bấm, không chờ kết quả |
| Tour | Nét tím có viền, chevron trắng chỉ chiều; kho là ô vuông màu mực có hình nhà kho; điểm giao là vòng tím đánh số theo thẻ đang xem. Tour tối đa 6 điểm thì luôn in tên cạnh số (chữ có quầng trắng); nhiều hơn thì tên chỉ hiện khi rê chuột |
| Điểm không đi được | Marker tô đỏ (tour không khả thi); app tự thu phóng vào điểm hỏng và đoạn đóng |
| Vùng có dữ liệu | Phần ngoài khung phủ xám rõ (16/11), viền đậm hơn; bấm ra ngoài khung thì báo "Điểm này nằm ngoài vùng có dữ liệu", bấm vào công viên hay sông trong khung thì báo khoảng cách tới đường gần nhất; đặt điểm trong khung mới snap được; bản đồ không kéo xa khỏi vùng |
| Chú giải và nút | Chú giải ở góc dưới trái, chỉ liệt kê những gì đang vẽ; bấm tiêu đề "Chú giải" để thu gọn hay mở lại; bản đồ hẹp (điện thoại) thì chú giải thu gọn sẵn. Nút bản đồ gom một cột ở góc dưới phải: chọn nền, "Về toàn tuyến" (thu phóng lại vừa kết quả), phóng to / thu nhỏ |
| Nền bản đồ | Nút "Đường phố / Xám" ở cột nút góc dưới phải (nhớ theo trình duyệt). **Đường phố** (mặc định, 16/11): Esri World Street Map, ảnh gốc tới zoom 19 nên sắc nét, có tên đường và mũi tên đường một chiều; lớp ảnh được làm dịu màu để tuyến nổi hơn nền. **Xám**: Esri Light Gray, sạch kiểu dashboard nhưng chỉ có ảnh tới zoom 16 nên phóng to bị nhoè. Mỗi lựa chọn có dự phòng: Esri → OSM → **nền rút gọn** tự vẽ từ `/api/network` (đường trắng ba cấp theo loại đường, nhãn nhỏ "Nền rút gọn từ dữ liệu đồ thị"; không có tên đường). Nguồn nào lỗi cả lượt tải hoặc treo 6 s thì sang nguồn kế; tile tải lại được thì nền rút gọn tự gỡ. Luôn ghi "Dữ liệu tuyến © OpenStreetMap contributors" cùng nguồn của nền đang hiện |

**Chặn trên bản đồ** (16/11): đóng đoạn bằng chuột chỉ khi bật nút "Chặn trên bản đồ" (dưới mục điểm, cạnh ô "Đóng một đoạn"), nên chạm nhầm vào tuyến lúc trình bày không đóng mất đường; Esc hoặc bấm lại nút để tắt. Khi bật: rê chuột lên tuyến thì đoạn sẽ đóng tô đỏ kèm "Bấm để đóng đoạn đang tô đỏ"; **bấm một lần là đóng** (không có nút xác nhận), cả cạnh đối nếu có, rồi tìm lại. Bấm trượt ra ngoài tuyến khi đang có kết quả không xoá gì (chỉ hiện gợi ý bấm Xóa). Bản đồ luôn dùng màu sáng, kể cả khi máy để chế độ tối. Không vẽ đường thẳng nối hai điểm khi không có đường.

### 1.3. Kết quả đo được

**Dải "Kết quả đo được"** (đầu panel trái, 16/11): tên lần chạy ("Dinh Độc Lập → Bitexco" hoặc "Tour từ Chợ Bến Thành · 5 điểm giao"), nhãn điều kiện giao thông của **request đã chạy** (vàng khi cao điểm, xám khi cơ sở; thêm nhãn "Đóng N cạnh" nếu có), ô số chính: thời gian di chuyển ước tính (phút, dòng phụ ghi giây và "theo điều kiện giao thông") và quãng đường (km, dòng phụ ghi mét); với tour là của phương án **đang xem**. Dòng "So với lần trước" chữ hổ phách có mũi tên lên khi chậm hơn, chữ xanh mũi tên xuống khi nhanh hơn; đỏ chỉ dành cho lỗi. Khi lần chạy không phải Cơ sở hoặc có đường đóng, có thêm dòng **"So với Cơ sở (không ùn tắc, không đóng đường)"**: app tính thêm cùng các điểm ở điều kiện Cơ sở (với tour: cùng thứ tự giao của phương án được chọn, để phần chênh chỉ do điều kiện giao thông), nên đổi từ cao điểm này sang cao điểm khác không còn đọc nhầm thành "nhanh hơn" (đánh giá 16/11). Nhãn trạng thái góc phải: Đang tính… / Lỗi / **Không có đường** / **Không lập được** (đỏ) / Đã tính (xanh). Đổi điều kiện giao thông thì bản đồ tự thu phóng lại vừa tuyến hoặc tour mới.

**Khay "Phân tích thuật toán"** (RQ1, 16/11): ba khối cạnh nhau. **Node đã mở rộng (trên 1.889 node của đồ thị)**: hai thanh cùng trục, Dijkstra xám, A* cam (cùng màu chấm node trên bản đồ), số in cạnh thanh ("442 node · 23,4%"), dòng kết luận "A* mở ít hơn 74,9% node so với Dijkstra mà vẫn ra cùng chi phí"; số node của đồ thị lấy từ `/api/dataset`. **Chi phí trùng khớp**: nhãn "Có" và "Cùng 246,1 s · 1.748 m"; khác chi phí thì hiện thêm bảng so sánh đủ bốn dòng; không có đường thì "Cả hai thuật toán cùng báo không có đường", thanh node vẫn hiện. **Thời gian tính toán (1 lần chạy)**: số ms từng thuật toán, ghi rõ chỉ là một lần chạy. Khi bật Phần mở rộng có bảng phụ ALT / Hai chiều.

**So với lần trước** (cùng điểm, khác điều kiện giao thông hoặc cạnh đóng): "186,1 s → 246,1 s: +60,0 s (+32,2%)", dòng phụ ghi điều kiện lần trước và lần này. Lưu ý: so với **lần ngay trước**, không phải với Cơ sở.

**Kết quả tour** (RQ2, 16/11): **lịch trình** của phương án đang xem nằm ở panel trái, dưới "Kho và điểm giao": Kho → 1 … n → về kho, số trong vòng tím khớp marker, cột phải ghi thứ tự nhập ("nhập #4"); không có giờ đến từng điểm (API chỉ trả tổng). Rê chuột hoặc Tab tới một dòng thì marker đó nổi lên trên bản đồ và hiện tên. **Khay "So sánh phương án"**: mỗi phương án một dòng (Thứ tự nhập, Nearest Neighbor, NN + 2-opt có nhãn "Được chọn", Tối ưu (Held–Karp, đối chứng) khi tổng số điểm ≤ 11, NN + 2-opt + Or-opt khi bật Phần mở rộng) với thanh thời gian cùng trục, vạch dọc "Tối ưu (Held–Karp)", phút · giây và "chậm hơn tối ưu X%"; nút **Xem trên bản đồ** / **Đang hiển thị**. Chữ "tối ưu" chỉ dùng khi Held–Karp chạy trong cùng lần lập tour (cùng điều kiện); không có Held–Karp thì ghi "chậm hơn phương án tốt nhất đã tính X%". Sau khi đóng đường có thêm **Giữ thứ tự cũ** (đứng đầu); xem dòng đó thì có câu "Cùng thứ tự, trước khi đóng: …" (chỉ khi lần này cùng điều kiện giao thông và chỉ đóng thêm đoạn). Dòng cuối ghi thời gian tính ma trận và sắp thứ tự (1 lần chạy).

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
| 5 | Bấm **Đảo chiều** lần nữa (về Dinh Độc Lập → Bitexco), rồi bấm chip điều kiện giao thông "Cao điểm — trung tâm" | Vùng ùn tắc; tuyến đổi sang đường vòng, tuyến cũ vẽ xám; "186,1 s → 246,1 s: +60,0 s (+32,2%)", 1.748 m | Ùn tắc theo vùng làm đổi lựa chọn (RQ3). Nếu quên đảo lại thì tuyến chiều ngược không đổi (193,0 → 300,0 s) | ~35 s |
| 6 | Ở ô **Đóng một đoạn trên tuyến**, chọn "Đoạn 10/18" (hoặc bật **Chặn trên bản đồ** rồi bấm đoạn đó trên bản đồ) | Đoạn đỏ; tuyến mới 302,3 s, 2.118 m; "246,1 s → 302,3 s"; "Đang đóng 1 cạnh" | Lập lại tuyến, không dùng cạnh bị đóng (RQ3) | ~25 s |
| 7 | Chọn lộ trình mẫu "Không còn đường" | Thông báo không có đường; không vẽ đường thẳng; Dijkstra và A* cùng mở 1.762 node | Hệ thống báo đúng giới hạn (RQ3); khi không còn đường, A* duyệt như Dijkstra | ~20 s |
| 8 | Chuyển sang slide biểu đồ tăng quy mô | `expanded` và thời gian theo `|V|` (4 kích thước, fixed trips) | Số đo thật (RQ1b) | ~30 s |
| 9 | Chế độ **Tour**, lộ trình mẫu "Kho + 5 điểm giao"; bấm **Xem trên bản đồ** ở dòng Thứ tự nhập rồi NN + 2-opt | 1.066,0 s → 898,1 s, thứ tự giao đổi (lịch trình ở panel trái đổi theo); Held–Karp 627,8 s là vạch tối ưu trên mọi thanh, NN + 2-opt "chậm hơn tối ưu 43,0%" | Tầng thứ hai của bài toán (RQ2). Câu chuẩn bị sẵn: "Held–Karp chỉ để đối chứng, không dùng để chọn tour" | ~45 s |
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
