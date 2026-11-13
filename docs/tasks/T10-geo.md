# T10 — Hàm địa lý

**Trạng thái: ✅ đã merge 26/10 ([#58](https://github.com/NeitLN/SaiGo/pull/58)).**

Tuần mục tiêu: 2 (26–27/10) · Giao cho: Tiến (thay Duy Anh; đã chuyển 26/10) · Nhánh: `t10-geo` · Issue: [#6](https://github.com/NeitLN/SaiGo/issues/6)
Review: Bảo · Người tích hợp: Tiến
Phụ thuộc: — (làm độc lập) · Ước lượng: 2 giờ

## Mục tiêu
Một module khoảng cách dùng chung cho heuristic A* (T20), snap (T13/T50) và ùn tắc (T40).

## Việc cần làm
1. **`backend/app/graph/geo.py`:**
   ```python
   EARTH_R_M = 6_371_009          # cùng bán kính OSMnx dùng để tính length

   def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float: ...
   def polyline_length_m(coords: list[list[float]]) -> float: ...       # coords dạng [[lon, lat], ...] (GeoJSON)
   def polyline_midpoint(coords: list[list[float]]) -> tuple[float, float]:   # trả (lat, lon) tại 50% chiều dài
       ...
   ```
   Có thể tham khảo `haversine_m` đã có trong `scripts/prepare_data.py` (T31). Hàm trong `geo.py` phải ra cùng kết quả.
2. **`tests/test_geo.py`:**
   - 2 điểm trùng nhau → 0.
   - Một cặp điểm có khoảng cách đã biết; tính đối chứng bằng `osmnx.distance.great_circle` và ghi giá trị vào test. Sai số < 0,5 m.
   - Đối xứng: `haversine_m(a, b) == haversine_m(b, a)`.
   - `polyline_midpoint` của đoạn thẳng 2 điểm là trung điểm.
   - Polyline 3 điểm hình chữ L: trung điểm nằm đúng ở 50% chiều dài, không phải ở điểm giữa danh sách.
   - **Thứ tự tọa độ:** đầu vào polyline là `[lon, lat]`, đầu ra là `(lat, lon)`. Có một test cố ý đổi chỗ để thấy kết quả sai.

## Sở hữu (chỉ task này được tạo/sửa)
- `backend/app/graph/geo.py`
- `tests/test_geo.py`

## Dùng (chỉ đọc)
- DATA_MODEL mục 4.1 (trung điểm cạnh), mục 5.1 (bán kính)

## Tiêu chí chấp nhận
- [x] `pytest tests/test_geo.py -q` → PASS (13 test)
- [x] Cùng kết quả với `haversine_m` trong `scripts/prepare_data.py` cho 3 cặp điểm bất kỳ (lệch 0 m trên 1.000 cặp điểm quanh TP.HCM, kiểm 26/10)

## Ngoài phạm vi
Snap (T50); vùng ùn tắc (T40).

## Kiến thức cần giải thích được
Công thức haversine; vì sao GeoJSON dùng `[lon, lat]` còn Leaflet dùng `[lat, lon]`.
