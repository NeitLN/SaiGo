# Phiếu bắt đầu — Võ Hoàng Minh (@Jayson135724)

> **Từ 26/10 phân công đã đổi** (cắt T32; Duy Anh vắng sáng 26/10 rồi quay lại chiều 26/10). Danh sách task dưới đây là của tuần 1; việc hiện tại xem [phiếu giao việc](../../tasks/README.md), [ROADMAP](../../ROADMAP.md) mục 6 và tab Issues.

**Vai trò:** pipeline dữ liệu OpenStreetMap, bản đồ, giao diện.
Làm xong [ONBOARDING.md](../ONBOARDING.md) mục 1–5 trước; chạy `scripts\setup_dev.ps1` **với `-Data`** để cài OSMnx.

## Task của bạn theo thứ tự

| Thứ tự | Issue | Task | Dự kiến | Review bởi |
|---|---|---|---|---|
| 1 | [#4](https://github.com/NeitLN/SaiGo/issues/4) | T02 · Thử OSMnx trên Windows | 23–24/10 | Tiến |
| 2 | [#12](https://github.com/NeitLN/SaiGo/issues/12) | T30 · Chốt vùng và tải dữ liệu một lần | 24–25/10 | Tiến |
| 3 | [#13](https://github.com/NeitLN/SaiGo/issues/13) | T31 · GraphML → `saigo-graph/1` + báo cáo kiểm tra (cùng Tiến) | 25–27/10 | Duy Anh |
| 4 | [#14](https://github.com/NeitLN/SaiGo/issues/14) | T32 · Vẽ mạng đường thật trên bản đồ | 27–28/10 | Tiến |
| 5 | [#19](https://github.com/NeitLN/SaiGo/issues/19) | T50 · Snap điểm về node | 31/10–01/11 | Tiến |
| 6 | [#21](https://github.com/NeitLN/SaiGo/issues/21) | T52 · UI chọn 2 điểm, 2 tuyến, bảng so sánh | 01–03/11 | Tiến |
| 7 | [#26](https://github.com/NeitLN/SaiGo/issues/26) | T61 · Cắt lồng nhau cho thí nghiệm tăng quy mô | 02–03/11 | Tiến |
| 8 | [#22](https://github.com/NeitLN/SaiGo/issues/22) | T53 · UI node mở rộng + kịch bản | 02–04/11 | Tiến |
| 9 | [#23](https://github.com/NeitLN/SaiGo/issues/23) | T54 · UI đóng đường + báo không có đường (cùng Tiến) | 03–04/11 | Duy Anh |
| 10 | [#35](https://github.com/NeitLN/SaiGo/issues/35) | T73 · UI tour (chỉ khi qua cổng G1) | 06–08/11 | Tiến |
| 11 | [#39](https://github.com/NeitLN/SaiGo/issues/39) | T82 · Tập demo + video dự phòng (cùng Bảo) | 10–12/11 | Tiến |

Thêm: phần của mình trong [#31](https://github.com/NeitLN/SaiGo/issues/31) (T65) và [#40](https://github.com/NeitLN/SaiGo/issues/40) (T83).
Danh sách luôn cập nhật: [issue được giao cho bạn](https://github.com/NeitLN/SaiGo/issues?q=is%3Aopen+assignee%3AJayson135724).

**Bạn review:** [#15](https://github.com/NeitLN/SaiGo/issues/15) T33 (Duy Anh + Tiến); mọi PR đụng `frontend/`, `data/`, `scripts/prepare_data.py`, `scripts/make_crops.py` (CODEOWNERS tự gửi yêu cầu).

## Đọc trước

- [DATA_MODEL.md](../../DATA_MODEL.md) mục 2 (định dạng file bạn sẽ xuất) và mục 8 (pipeline, đường một chiều, điểm không kết nối, snap).
- [ARCHITECTURE.md](../../ARCHITECTURE.md) mục 4 (`/api/network`) và mục 6 (giao diện).
- [TOPIC.md](../../TOPIC.md) mục 7 (dữ liệu, giấy phép, không tải tile hàng loạt).

## Task đầu tiên: T02 (#4) từng bước

**Branch:** `t02-osmnx-smoke`

1. Cài: `powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1 -Data`. Script in phiên bản OSMnx nếu cài được.
2. **Nếu OSMnx cài lỗi trên Windows** (thường do geopandas/shapely/pyproj):
   - Cài [Miniforge](https://github.com/conda-forge/miniforge).
   - `conda create -n saigo-data -c conda-forge python=3.11 osmnx`, rồi `conda activate saigo-data`.
   - Chỉ dùng môi trường này cho `scripts/prepare_data.py`; app vẫn dùng `.venv`.
   - Ghi lại cách đã làm vào PROGRESS.md.
3. Thêm chế độ `--smoke` vào `scripts/prepare_data.py` (dùng `argparse`). Gợi ý phần lõi:

   ```python
   import osmnx as ox
   CENTER = (10.7725, 106.6980)          # (lat, lon) chợ Bến Thành
   G = ox.graph_from_point(CENTER, dist=250, network_type="drive")
   oneway = sum(1 for _, _, d in G.edges(data=True) if d.get("oneway"))
   print(f"nodes={G.number_of_nodes()} edges={G.number_of_edges()} oneway_edges={oneway}")
   ox.save_graphml(G, "data/raw/smoke.graphml")
   ```

4. Chạy `python scripts/prepare_data.py --smoke`. Ghi vào [PROGRESS.md](../../PROGRESS.md): số node/cạnh in ra; phiên bản OSMnx, NetworkX, geopandas, shapely; cài bằng pip hay conda.
5. PR `Closes #4`. Không commit file trong `data/raw/` và `cache/`; hai thư mục này đã nằm trong `.gitignore`.

**Bẫy cần biết cho các task sau:**

- OSMnx 2.x đổi cách gọi `graph_from_bbox`: nhận `bbox=(west, south, east, north)`, tức (lon trái, lat dưới, lon phải, lat trên). Đảo thứ tự là tải nhầm vùng.
- Sau `simplify`, thuộc tính `osmid` và `highway` có thể là **list**; phải chuẩn hóa (DATA_MODEL mục 8.2 bước 3).
- OSMnx mặc định chỉ giữ thành phần liên thông **yếu** lớn nhất; phải tự chọn thành phần liên thông **mạnh** (mục 8.4).
- Leaflet nhận `[lat, lon]`, GeoJSON là `[lon, lat]`. Kiểm tra bằng mắt: mạng đường phải nằm đúng trên nền OSM, không lệch hay lộn ngược.
- Ghi nguồn "© OpenStreetMap contributors" trên bản đồ; không tải tile hàng loạt.

## Phải giải thích được trước giảng viên

- Dữ liệu nào thật (hình học, chiều đường, loại đường), dữ liệu nào mô phỏng (tốc độ, ùn tắc, đóng đường).
- Vì sao đường một chiều sinh 1 cạnh, đường hai chiều sinh 2 cạnh; vì sao A→B khác B→A.
- Thành phần liên thông mạnh khác yếu thế nào; vì sao điểm ngoài SCC không được dùng làm điểm snap.
- Vì sao tải dữ liệu một lần rồi đóng băng (manifest, hash, tái lập kết quả).
