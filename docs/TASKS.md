# SaiGo — Danh sách task

Mỗi task vừa sức một buổi (khoảng 2–4 giờ). Nếu một task kéo dài quá hai buổi, tách nhỏ và ghi lý do vào [PROGRESS.md](PROGRESS.md). Người phụ trách là **[Đề xuất]**: Tiến có thể vào làm cùng ở mọi task. Ngày 26/10, T01, T10, T11, T20 chuyển từ Duy Anh sang Tiến vì Duy Anh vắng tuần 2.

> **26/10: nhóm đã duyệt kế hoạch tuần 2** ([ROADMAP](ROADMAP.md) mục 6): T12 → Bảo, T13 → Minh, T21 → Bảo (dự phòng). Toàn bộ file đã đồng bộ với [đề xuất phạm vi đã duyệt](proposals/2026-10-26-pham-vi.md): cắt T32, RQ1b 3 kích thước chỉ fixed trips, T53/T54 rút gọn, G1 thành điểm kiểm bằng chứng 05/11, thêm T34. **Chiều 26/10:** Duy Anh quay lại và làm T13, T21, T22, T40, T41, T60 (khung), T64, T70, T71; tour (T72–T74) trở lại phạm vi cam kết (D10 ở PROJECT_BRIEF mục 4).

Ký hiệu: 👤 phụ trách · ⏱ ước lượng · ⛓ phụ thuộc · 📁 file · 📦 đầu ra · ✅ hoàn thành khi · ▶ kiểm tra · 🧠 kiến thức cần hiểu để giải thích.

Thứ tự gợi ý trong tuần đầu: **T00 → T01 → T03 → T10 → T11 → T12 → T20 → T21 → T22**, song song **T02 → T30 → T31 → T32**.

Mỗi task ở đây là một GitHub Issue (nhãn `task`). Trạng thái theo dõi trên GitHub Project, quy trình ở [CONTRIBUTING.md](../CONTRIBUTING.md). Khi sửa task ở file này, chạy lại `python scripts/tracking/create_backlog.py --sync` để cập nhật issue.

---

## M0 — Nền móng

### T-PLAN — Lập kế hoạch triển khai và hệ thống theo dõi
- 👤 Tiến · ⏱ 4 h · ⛓ —
- **Mục tiêu:** có kế hoạch, backlog và công cụ theo dõi trước khi viết code.
- **Việc cần làm:** viết bộ tài liệu kế hoạch trong `docs/`; tạo labels, milestones, issues, GitHub Project; viết template issue/PR, CONTRIBUTING, script burndown.
- 📁 `docs/*.md`, `docs/tracking/`, `.github/`, `scripts/tracking/`, `CONTRIBUTING.md`
- 📦 Kế hoạch + backlog trên GitHub + burndown tự động.
- ✅ Mọi task có issue; burndown hiện trên issue theo dõi.
- ▶ Mở tab Issues và Project của repo.
- 🧠 Vì sao chia nhỏ task; burndown đọc thế nào.

### T00 — Dựng môi trường và xác nhận khung chạy
- 👤 Tiến · ⏱ 1–2 h · ⛓ —
- **Mục tiêu:** chứng minh khung hiện có chạy trên Windows trước khi viết code mới.
- **Việc cần làm:**
  1. `python -m venv .venv`, kích hoạt, `pip install -e ".[dev]"`.
  2. Chạy `pytest -q`.
  3. Chạy backend: `uvicorn app.main:app --reload --app-dir backend`; mở `http://127.0.0.1:8000/api/health`.
  4. `cd frontend && npm install && npm run build && npm run dev`; mở `http://localhost:5173`.
  5. Ghi phiên bản Python, Node, FastAPI vào PROGRESS.md.
- 📁 PROGRESS.md (không đổi code)
- 📦 Môi trường chạy được; phiên bản được ghi lại.
- ✅ `pytest` báo `1 passed`; trang web hiện "Server chạy, chưa nạp dataset".
- ▶ `pytest -q` · `npm run build`
- 🧠 Vai trò venv; vì sao frontend gọi `/api` qua proxy của Vite (`vite.config.ts`).

### T01 — Chốt định dạng đồ thị, tạo fixture mẫu và bộ nạp Graph
- 👤 Tiến (Bảo review) · ⏱ 3 h · ⛓ T00 · ✅ đã merge 26/10 (#57); còn kiểm dữ liệu thật khi có Release
- **Mục tiêu:** có một đồ thị nhỏ tính tay được và một hàm nạp dùng chung cho mọi phần sau.
- **Việc cần làm:**
  1. Viết `tests/fixtures/mini.json` theo đúng `saigo-graph/1`, dựa trên ví dụ ở [DATA_MODEL.md](DATA_MODEL.md) mục 7. Đổi mét sang lat/lon quanh tâm (10.7725, 106.6980); mỗi node có thêm trường tùy chọn `"name": "S"`.
  2. Viết `Graph` (dataclass) và `load_graph(path)` trong `backend/app/graph/model.py`: đọc JSON, kiểm tra (DATA_MODEL mục 2.3), dựng `out_edges`, tính `base_time_s`, `v_max_mps`.
  3. Hàm `node_by_name(meta, "S")` để test và CLI dùng tên (tên node nằm trong `GraphMeta`).
  4. Test: số node/cạnh, đường một chiều (A→T có, T→A không), cạnh lỗi (tốc độ ≤ 0) bị từ chối.
- 📁 `backend/app/graph/model.py`, `tests/fixtures/mini.json`, `tests/test_graph_model.py`
- 📦 Bộ nạp đồ thị + fixture.
- ✅ Test xanh; định dạng JSON được Minh xác nhận là sẽ xuất ra được ở T31.
- ▶ `pytest tests/test_graph_model.py -q`
- 🧠 Đồ thị có hướng; adjacency list theo **edge id**; vì sao cần `key` cho cạnh song song; `base_time = length / (km/h ÷ 3,6)`.

### T02 — Thử OSMnx trên Windows
- 👤 Minh (Tiến hỗ trợ) · ⏱ 2 h · ⛓ T00
- **Mục tiêu:** phát hiện sớm rủi ro cài đặt thư viện địa lý.
- **Việc cần làm:**
  1. `pip install -e ".[data]"`. Nếu lỗi, tạo môi trường conda-forge riêng (`conda create -n saigo-data -c conda-forge osmnx`) và ghi lại.
  2. Thêm chế độ `--smoke` vào `scripts/prepare_data.py`: tải bbox ~500 m quanh Bến Thành với `network_type="drive"`, in số node/cạnh, số cạnh có `oneway=True`, rồi lưu GraphML vào `data/raw/smoke.graphml`.
  3. Ghi phiên bản OSMnx, NetworkX, geopandas, shapely vào PROGRESS.md.
- 📁 `scripts/prepare_data.py`, `pyproject.toml` (khóa phiên bản nếu cần)
- 📦 Lệnh smoke chạy được.
- ✅ In ra số node/cạnh > 0 trên máy Windows của nhóm.
- ▶ `python scripts/prepare_data.py --smoke`
- 🧠 OSMnx trả `MultiDiGraph`; `network_type="drive"` gồm những loại đường nào; vì sao không tải lại dữ liệu mỗi lần chạy.

### T03 — Bảng kết quả tính tay cho đồ thị mẫu
- 👤 Bảo (Tiến review) · ⏱ 2 h · ⛓ — (chỉ cần DATA_MODEL mục 7) · ✅ đã merge 26/10 (#54)
- **Mục tiêu:** có đáp án độc lập để kiểm tra code Dijkstra/A*.
- **Việc cần làm:**
  1. Với 6 tình huống ở DATA_MODEL mục 7, chạy tay Dijkstra: ghi bảng từng bước (heap, `g`, node pop).
  2. Làm tương tự cho A* tình huống cơ sở: tính `h`, `f` từng node.
  3. Ghi kết quả vào `tests/fixtures/mini_expected.json`: chi phí, tuyến, số node mở rộng.
- 📁 `tests/fixtures/mini_expected.json`, `docs/ALGORITHMS.md` (thêm bảng chạy tay)
- 📦 Đáp án + bảng giải thích.
- ✅ Tiến đối chiếu và xác nhận (thay Duy Anh); có ít nhất một bảng từng bước cho Dijkstra và một cho A*.
- ▶ Review thủ công; sau T11/T20 các test đọc file này phải xanh.
- 🧠 Thứ tự pop của Dijkstra; vì sao A* không pop C và D.

### T04 — Sửa hệ thống theo dõi sau review
- 👤 Tiến (Duy Anh review) · ⏱ 3 h · ⛓ T-PLAN
- **Mục tiêu:** số liệu theo dõi không bị viết lại, không bị "làm đẹp", và đồng bộ không xóa thông tin đang dùng.
- **Việc cần làm:** burndown lưu số cuối ngày vào `daily.csv` (chỉ ghi thêm); tách task hoàn thành qua PR/commit với task đóng thủ công và task bị cắt; kiểm tra ước lượng; đếm review theo cặp người–PR; bình luận tổng kết tuần không trùng; `create_backlog.py` giữ checkbox, nhãn `blocked` và tìm issue theo "Mã task"; `setup_project.py` xử lý issue mở lại; thêm Bảo vào CODEOWNERS; sửa phụ thuộc T80 và hạn T03.
- 📁 `scripts/tracking/*.py`, `.github/workflows/tracking.yml`, `.github/CODEOWNERS`, `docs/tracking/`, `docs/TASKS.md`
- 📦 Hệ thống theo dõi đã sửa.
- ✅ Chạy `burndown.py` tại máy ra cùng số với issue theo dõi; chạy `create_backlog.py --sync` hai lần liên tiếp không đổi gì.
- ▶ `python scripts/tracking/burndown.py --out build/tracking` · `python scripts/tracking/create_backlog.py --dry-run`
- 🧠 Vì sao lịch sử burndown phải chỉ ghi thêm; khác biệt giữa "đóng issue" và "hoàn thành có bằng chứng".

### T05 — Hướng dẫn bắt đầu cho từng thành viên
- 👤 Tiến (Duy Anh review) · ⏱ 3 h · ⛓ T04
- **Mục tiêu:** mỗi thành viên tự dựng được môi trường và bắt đầu task đầu tiên mà không phải hỏi lại.
- **Việc cần làm:** `scripts/setup_dev.ps1` dựng môi trường bằng một lệnh; `docs/team/ONBOARDING.md` (cài đặt, git đúng tên, quy trình PR/review, lỗi thường gặp); phiếu bắt đầu cho từng người trong `docs/team/start/`; chương trình họp khởi động `docs/team/KICKOFF.md`; README dùng script mới.
- 📁 `scripts/setup_dev.ps1`, `docs/team/`, `README.md`
- 📦 Bộ tài liệu bắt đầu + script.
- ✅ Script chạy tới `==> Xong` trên Windows PowerShell 5.1; mọi link trong tài liệu mở được.
- ▶ `powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1`
- 🧠 Vì sao commit phải mang tên đúng người; vì sao `pip install -e` lỗi với đường dẫn có dấu trên Windows.

### T06 — Bộ nhớ dự án, quyết định đắt nếu đổi, hàng rào kỹ thuật
- 👤 Tiến (Duy Anh review) · ⏱ 3 h · ⛓ T05
- **Mục tiêu:** session hoặc thành viên mới đọc một file là biết dự án đang ở đâu; các quyết định khó đổi được chốt trước task cần chúng; mọi máy và CI dùng cùng phiên bản thư viện.
- **Việc cần làm:** `docs/STATUS.md` (≤ 100 dòng, ghi đè mỗi cuối session); ROADMAP mục 5 (quyết định đắt nếu đổi Q1–Q8) và mục 6 (kế hoạch tuần 2, chờ nhóm duyệt); thêm mốc walking skeleton (T13–T15) và contract `/api/route` v1 (ARCHITECTURE mục 4.1); `requirements-lock.txt` + CI cài theo file này; job `audit` (pip-audit, npm audit); `setup_dev.ps1` dùng file khóa và nâng setuptools.
- 📁 `docs/STATUS.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/TASKS.md`, `requirements-lock.txt`, `.github/workflows/ci.yml`, `scripts/setup_dev.ps1`
- 📦 Bộ nhớ dự án + hàng rào.
- ✅ CI xanh với file khóa; `pip-audit -r requirements-lock.txt` không có lỗ hổng; `setup_dev.ps1 -Data` chạy tới `==> Xong`.
- ▶ `pip-audit -r requirements-lock.txt` · `powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1 -Data`
- 🧠 Vì sao khóa phiên bản là điều kiện để benchmark tái lập được; vì sao job audit không bắt buộc để merge.

---

## M1 — Dijkstra trên đồ thị mẫu

### T10 — Hàm địa lý
- 👤 Tiến (Bảo review) · ⏱ 1–2 h · ⛓ T00 · ✅ đã merge 26/10 (#58)
- **Mục tiêu:** có hàm khoảng cách dùng chung cho heuristic, snap và ùn tắc.
- **Việc cần làm:** `haversine_m(lat1, lon1, lat2, lon2)` với R = 6 371 009 m; `polyline_midpoint(coords)` (điểm ở 50% chiều dài); test với một cặp điểm có khoảng cách đã biết, test 2 điểm trùng nhau = 0 và test thứ tự `[lon, lat]` của GeoJSON.
- 📁 `backend/app/graph/geo.py`, `tests/test_geo.py`
- 📦 Module `geo`.
- ✅ Sai số < 0,5 m so với giá trị tham chiếu (tính bằng `osmnx.distance.great_circle` hoặc một công cụ trực tuyến, ghi nguồn trong test).
- ▶ `pytest tests/test_geo.py -q`
- 🧠 Công thức haversine; vì sao GeoJSON là `[lon, lat]` còn Leaflet là `[lat, lon]`.

### T11 — Dijkstra và SearchResult
- 👤 Tiến (Bảo review) · ⏱ 3–4 h · ⛓ T01, T03 · ✅ đã merge 26/10 (#59)
- **Mục tiêu:** cài Dijkstra đúng quy tắc ở DATA_MODEL mục 6.
- **Việc cần làm:**
  1. `SearchResult` + hàm dựng tuyến từ `pred_edge` trong `algorithms/result.py`.
  2. `dijkstra(graph, snap, source, target, trace_limit=0)` với heap `(g, counter, node)`, lazy deletion, dừng khi pop đích, đếm `expanded`, `relaxations`, `pushes`, `max_frontier`.
  3. `Snapshot` và `baseline_snapshot(graph)` trong `graph/scenario.py`. Đây là định nghĩa **duy nhất**; T40 thêm `Scenario` và `build_snapshot` vào cùng file, không tạo kiểu mới.
  4. Test: 6 tình huống trong `mini_expected.json`; `source == target`; cạnh song song (thêm vào bản sao fixture một cạnh S→A nhanh hơn → tuyến phải dùng đúng edge id đó); tổng `weights` theo `edge_ids` bằng `cost_s`.
- 📁 `backend/app/algorithms/result.py`, `dijkstra.py`, `backend/app/graph/scenario.py`, `tests/test_dijkstra.py`
- 📦 Dijkstra chạy trên fixture.
- ✅ Mọi test xanh; `expanded` = 5 ở tình huống cơ sở.
- ▶ `pytest tests/test_dijkstra.py -q`
- 🧠 Vì sao Dijkstra đúng khi trọng số không âm; lazy deletion; độ phức tạp `O((V+E) log V)`; vì sao lưu predecessor là **cạnh**.

### T12 — CLI tìm đường
- 👤 Bảo (Tiến review) · ⏱ 2 h · ⛓ T11 (bắt đầu), T13 (tích hợp, cho `--from-latlon`), T20 (chấp nhận)
- **Chuyển 26/10:** từ Tiến sang Bảo (giảm tải cho Tiến).
- **Mục tiêu:** chạy thuật toán từ dòng lệnh để kiểm tra và giải thích, chưa cần web.
- **Việc cần làm:** `python -m app.cli route --graph <file> --from S --to T --algo dijkstra|astar|both` (nhận tên node hoặc `--from-latlon lat,lon`); in tuyến (tên/ID), chi phí (s), quãng đường (m), số node mở rộng, thời gian chạy (ms).
- 📁 `backend/app/cli.py`
- 📦 Lệnh CLI.
- ✅ Kết quả in ra khớp `mini_expected.json` cho cả Dijkstra và A* (`--algo both`); chỉ tính là xong khi gọi được A*.
- ▶ `python -m app.cli route --graph tests/fixtures/mini.json --from S --to T --algo dijkstra` (chạy trong thư mục `backend/` hoặc với `PYTHONPATH=backend`)
- 🧠 Đo thời gian bằng `perf_counter_ns` chỉ quanh lời gọi thuật toán.

---

## MW — Walking skeleton

Đường mỏng nhất chạy xuyên mọi tầng của hành trình chính, xong trước **29/10**: bấm 2 điểm trên bản đồ → `/api/route` → Dijkstra trên `mini.json` → vẽ tuyến. Mục đích là để lỗi nối ghép (contract API, thứ tự lat/lon, chạy trên máy khác) lộ ra sớm, thay vì đến M6. Contract: [ARCHITECTURE.md](ARCHITECTURE.md) mục 4.1. T51 và T52 sau này mở rộng trên chính code này, không viết lại.

### T13 — Skeleton phía API: `/api/route` tối giản trên `mini.json`
- 👤 Duy Anh (Minh review) · ⏱ 3 h · ⛓ T11, T10 (đã merge) · ✅ đã merge 26/10 (#73)
- **26/10:** sáng chuyển từ Tiến sang Minh; chiều Duy Anh làm xong (#73), Minh review.
- **Mục tiêu:** API thật, mỏng nhất, trả tuyến Dijkstra theo đúng contract v1.
- **Việc cần làm:**
  1. Nạp đồ thị khi khởi động từ `SAIGO_GRAPH` (mặc định `tests/fixtures/mini.json`); `/api/health` báo `dataset_loaded: true`.
  2. `POST /api/route` theo contract v1: snap về node gần nhất bằng `nearest_node_naive(graph, meta, lat, lon)` (duyệt tuyến tính, chưa giới hạn 150 m, chỉ xét node có `meta.node_in_scc`), chạy `dijkstra()` của T11, trả geometry `[lon, lat]`, `cost_s`, `distance_m`, `expanded`, `runtime_ms`.
  3. Test bằng TestClient: S→T trả `cost_s = 80`; T→S trả 100; geometry bắt đầu ở S và kết thúc ở T.
- **Phụ thuộc:** T11 và T10 đã merge (#59, #58): dùng trực tiếp `dijkstra()` và `geo.haversine_m`.
- 📁 `backend/app/main.py`, `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/services/routing.py`, `tests/test_api_route.py`
- 📦 API skeleton.
- ✅ Test API xanh; gọi thử bằng `http://127.0.0.1:8000/docs` ra đúng contract.
- ▶ `pytest tests/test_api_route.py -q`
- 🧠 Vì sao làm API mỏng trước rồi mới mở rộng; ranh giới API / service / thuật toán.

### T14 — Skeleton phía bản đồ: bấm 2 điểm, vẽ tuyến
- 👤 Minh (Tiến review) · ⏱ 3 h · ⛓ T13
- **Mục tiêu:** trình duyệt gọi API thật và vẽ đúng tuyến trên nền OSM.
- **Việc cần làm:** bấm lần 1 = điểm đi, lần 2 = điểm đến; gọi `POST /api/route`; vẽ polyline (đổi `[lon, lat]` → `[lat, lon]`); hiện `cost_s` và `expanded`; hiện lỗi khi API lỗi. Kiểu dữ liệu response đặt trong `frontend/src/api.ts` theo contract v1.
- **Phụ thuộc theo mức:** contract v1 chặn ở mức *bắt đầu* (đã chốt); T13 chặn ở mức *tích hợp*: code trước với response mẫu trong contract, nối API thật khi T13 merge.
- 📁 `frontend/src/main.ts`, `frontend/src/api.ts`
- 📦 UI skeleton.
- ✅ Bấm gần S rồi gần T: tuyến đi S→A→T nằm đúng quanh chợ Bến Thành trên nền OSM, hiện 80 s; đảo lại hiện 100 s.
- ▶ Chạy backend + frontend, thao tác như trên; `npm run build` không lỗi.
- 🧠 Thứ tự `[lon, lat]` và `[lat, lon]`; luồng trình duyệt → proxy Vite → FastAPI.

### T15 — Chạy skeleton trên máy thứ hai
- 👤 Bảo (Tiến review) · ⏱ 2 h · ⛓ T13, T14
- **Mục tiêu:** chứng minh người khác chạy được app chỉ bằng tài liệu. Đây là bản sớm của T80.
- **Việc cần làm:** trên máy của Bảo: clone sạch, làm ONBOARDING mục 1–3, chạy backend + frontend, làm lại thao tác ✅ của T14, chụp màn hình; mọi bước vướng thì mở issue *Lỗi* và sửa tài liệu trong cùng PR.
- 📁 `docs/team/ONBOARDING.md` (nếu cần sửa), `docs/PROGRESS.md`, `docs/img/skeleton-bao.png`
- 📦 Biên bản chạy trên máy thứ hai.
- ✅ Thấy tuyến 80 s trên máy của Bảo mà không cần ai sửa tay; hoặc tài liệu đã được sửa cho tới khi chạy được.
- ▶ Thủ công, theo ONBOARDING.
- 🧠 Vì sao phải thử trên máy khác từ sớm, không đợi tới tuần cuối.

---

## M2 — A* và đối chứng

### T20 — A* với heuristic địa lý
- 👤 Tiến (Minh review) · ⏱ 3 h · ⛓ T10, T11 (đã merge); PR kiểm thứ tự ID cạnh trong `load_graph` merge trước
- **Mục tiêu:** A* cho cùng chi phí với Dijkstra nhưng mở rộng ít node hơn trên fixture.
- **Việc cần làm:**
  1. `astar(graph, snap, source, target, heuristic, trace_limit=0)`: ưu tiên `g + h`, cho phép mở lại, đếm `reopened`.
  2. `make_geo_heuristic(graph, target, c=1.0)` và `zero_heuristic`.
  3. Test: chi phí bằng Dijkstra ở cả 6 tình huống; `expanded` = 2 ở tình huống cơ sở; với `zero_heuristic` thì `expanded` giống hệt Dijkstra; `reopened == 0`.
- 📁 `backend/app/algorithms/astar.py`, `heuristics.py`, `tests/test_astar.py`; `tests/mini_cases.py` (`_dist_m` dùng `geo.haversine_m`) và `_comment` của `tests/fixtures/mini.json` (hằng số 111 320 m/độ), theo góp ý review T11
- 📦 A* chạy trên fixture.
- ✅ Mọi test xanh.
- ▶ `pytest tests/test_astar.py -q` · CLI `--algo both`
- 🧠 `f = g + h`; admissible và consistent; chứng minh phác thảo ở DATA_MODEL mục 5.2; vì sao `h = 0` biến A* thành Dijkstra.

### T21 — Đối chứng NetworkX trên đồ thị ngẫu nhiên
- 👤 Duy Anh (Minh review) · ⏱ 3 h · ⛓ T20
- **26/10:** sáng chuyển sang Bảo làm dự phòng; chiều Duy Anh quay lại và làm xong (#64).
- **Mục tiêu:** bằng chứng thực nghiệm rằng code đúng trên nhiều đồ thị, không chỉ fixture.
- **Việc cần làm:**
  1. Bộ sinh đồ thị ngẫu nhiên có seed: node có tọa độ, cạnh có hướng, `length ≥ haversine` (nhân một hệ số ≥ 1), có cạnh song song và cặp không tới được.
  2. Với 20 đồ thị × 50 cặp: so `cost_s` của Dijkstra và A* với `nx.dijkstra_path_length` trên `MultiDiGraph` cùng trọng số; so trường hợp `no_path` với `nx.NetworkXNoPath`.
  3. Kiểm tra tuyến: các cạnh nối tiếp nhau, đi đúng chiều, không dùng cạnh bị chặn.
- 📁 `tests/test_oracle_networkx.py`, `tests/helpers/random_graph.py`
- 📦 Test đối chứng.
- ✅ 1.000 truy vấn khớp với sai số `1e-9 · max(1, cost)`; chạy < 30 s trong CI.
- ▶ `pytest tests/test_oracle_networkx.py -q`
- 🧠 Vì sao so **chi phí** mà không so dãy node (có thể có nhiều tuyến cùng chi phí); test không phải chứng minh.

### T22 — Kiểm tra điều kiện heuristic trên dữ liệu
- 👤 Duy Anh · ⏱ 2 h · ⛓ T20, T12
- **26/10:** Duy Anh làm `heuristic_report` (#68). **Còn:** lệnh `check-heuristic` — Duy Anh thêm sau khi T12 có `cli.py`; chạy trên đồ thị thật khi có T34.
- **Mục tiêu:** báo cáo `c`, `v_max` trên dữ liệu thật và phát hiện dữ liệu làm heuristic sai.
- **Việc cần làm:** `geo_scale(graph)` (tính `c` theo DATA_MODEL mục 5.1) đã có từ T20 trong `algorithms/heuristics.py`, kèm test cạnh ngắn hơn khoảng cách thẳng. T22 thêm lệnh `python -m app.cli check-heuristic --graph <file>` in `v_max`, `c`, số cạnh có `length < haversine`, 5 cạnh tệ nhất.
- 📁 `backend/app/algorithms/heuristics.py`, `backend/app/cli.py`, `tests/test_heuristics.py`
- 📦 Báo cáo heuristic.
- ✅ Lệnh in đúng trên fixture (`c = 1`) và trên một fixture lỗi (`c < 1`); kết quả trên đồ thị thật ghi vào manifest.
- ▶ `pytest tests/test_heuristics.py -q`
- 🧠 Vì sao nhân `c` vẫn giữ consistency (bất đẳng thức tam giác).

---

## M3 — Dữ liệu thô đóng băng và đồ thị vùng demo (song song)

Từ 26/10 không vẽ toàn mạng đường (T32 đã cắt); mục tiêu của mốc là cả nhóm dùng chung đúng một bản dữ liệu.

### T30 — Chốt vùng và tải dữ liệu một lần
- 👤 Minh (Bảo hỗ trợ chọn tọa độ) · ⏱ 2–3 h · ⛓ T02
- **Mục tiêu:** có bản dữ liệu thô đóng băng cho mọi thực nghiệm.
- **Việc cần làm:**
  1. `data/config/areas.json`: tâm Bến Thành, nửa cạnh vùng tải 4,5 km + đệm 0,5 km **[Đề xuất]**, vùng demo nửa cạnh 2 km **[Đề xuất]**.
  2. `data/config/speeds.json` theo bảng DATA_MODEL mục 3.2.
  3. `python scripts/prepare_data.py download`: tải bbox vùng tải, lưu `data/raw/outer.graphml`, ghi `data/processed/raw_manifest.json` (ngày tải, bbox, phiên bản OSMnx, số node/cạnh, `sha256`).
- 📁 `data/config/areas.json`, `data/config/speeds.json`, `scripts/prepare_data.py`
- 📦 GraphML thô + manifest.
- ✅ Tải xong; số node/cạnh được ghi bằng số đo, không ước lượng.
- ▶ `python scripts/prepare_data.py download` · mở `raw_manifest.json`
- 🧠 Vì sao cần vùng đệm; vì sao đóng băng dữ liệu (tái lập kết quả).

### T31 — Chuyển GraphML thành `saigo-graph/1` và báo cáo kiểm tra
- 👤 Minh + Tiến · ⏱ 4 h (có thể 2 buổi) · ⛓ T01, T30
- **Mục tiêu:** đồ thị thật đọc được bằng `load_graph` của T01.
- **Việc cần làm:**
  1. `python scripts/prepare_data.py build --area demo`: cắt vùng (DATA_MODEL mục 8.2 bước 4), chuẩn hóa `way_ids`/`highway`, gán tốc độ, chọn SCC, đánh lại ID, xuất JSON + `manifest.json`.
  2. In báo cáo: số node/cạnh, % một chiều, cạnh song song, self-loop, kích thước SCC, số node ngoài SCC.
  3. Kiểm tra tay 2–3 đường một chiều đã biết ở Quận 1 (xem trên openstreetmap.org); ghi kết quả vào PROGRESS.md.
  4. Test (đánh dấu `realdata`, tự bỏ qua nếu không có file): `load_graph` đọc được, mọi ID hợp lệ.
- 📁 `scripts/prepare_data.py`, `data/processed/<dataset_id>.json` (gitignored), `data/processed/manifest.json` (commit), `tests/test_realdata.py`
- 📦 Đồ thị vùng demo.
- ✅ `load_graph` nạp được; báo cáo được dán vào PROGRESS.md; đường một chiều kiểm tra tay đúng chiều.
- ▶ `python scripts/prepare_data.py build --area demo` · `pytest -m realdata -q`
- 🧠 Simplify gộp nhiều đoạn thành một cạnh; `osmid` dạng list; SCC khác WCC thế nào; vì sao điểm ngoài SCC không được dùng.

### T34 — Đưa dữ liệu thô lên Release và kiểm hash trên 2 máy
- 👤 Minh (Tiến review) · ⏱ 2 h · ⛓ —
- **Thêm 26/10:** tải lại OSM ngày 25/10 đã ra dữ liệu khác (12.130 so với 12.131 node), nên phải chia sẻ đúng bản đã tải.
- **Mục tiêu:** cả nhóm dùng đúng một bản `outer.graphml` (sha256 `24a28327…`).
- **Việc cần làm:** merge #46 → #47 → #53 (trước khi merge #53, sửa `test_load_graph_reads_file` thành `g, _ = model.load_graph(...)`); tạo Release `data-raw-20261024`; thêm mục "Tải dữ liệu" vào ONBOARDING; sửa thông báo lỗi trong `prepare_data.py build`. Chi tiết: [tasks/T34-release-data.md](tasks/T34-release-data.md).
- 📁 Release `data-raw-20261024`, `docs/team/ONBOARDING.md`, `scripts/prepare_data.py`
- 📦 Dữ liệu thô dùng chung.
- ✅ Tiến tải từ Release ra đúng sha256, chạy `build --area demo` và ghi sha256 file JSON trên cả hai máy.
- ▶ `gh release view data-raw-20261024` · `Get-FileHash data\raw\outer.graphml -Algorithm SHA256`
- 🧠 Vì sao đóng băng dữ liệu; hash khác nhau cho biết điều gì.

### T32 — Vẽ mạng đường thật trên bản đồ *(đã cắt 26/10)*
- 👤 Minh · ⏱ 3 h · ⛓ T31
- **Đã cắt 26/10** (D12): dùng nền tile OSM, chỉ vẽ tuyến và các cạnh của tuyến; issue đóng *not planned*. Phần nạp đồ thị khi khởi động do T13 làm.
- **Mục tiêu:** nhìn thấy đồ thị trên Leaflet, đo được tốc độ vẽ.
- **Việc cần làm:**
  1. Backend nạp Graph khi khởi động (đường dẫn qua biến môi trường `SAIGO_GRAPH`); `/api/health` báo `dataset_loaded: true`; `/api/network` trả GeoJSON có `edge_id`.
  2. Frontend: `preferCanvas: true`, vẽ lớp mạng đường, căn khung theo vùng; giữ ghi nguồn OSM; tile OSM nền chỉ khi có mạng.
  3. Đo thời gian tải + vẽ trên laptop demo; ghi vào PROGRESS.md.
- 📁 `backend/app/main.py`, `api/routes.py`, `api/schemas.py`, `frontend/src/main.ts`, `api.ts`, `layers.ts`, `tests/test_health.py`
- 📦 Bản đồ có mạng đường thật.
- ✅ Mạng đường hiện đúng vị trí trên nền OSM (không lệch, không đảo lat/lon); kéo/zoom không giật rõ rệt.
- ▶ Chạy backend + frontend, mở `http://localhost:5173`; `pytest tests/test_health.py -q`
- 🧠 Luồng dữ liệu server → GeoJSON → Leaflet; vì sao không tải tile hàng loạt.

---

## M4 — Hợp nhất: tìm đường trên dữ liệu thật

### T33 — Dijkstra/A* trên đồ thị thật + đối chứng 200 cặp
- 👤 Duy Anh + Tiến · ⏱ 3 h · ⛓ T22, T31
- **Mục tiêu:** xác nhận thuật toán đúng trên dữ liệu thật trước khi làm tiếp.
- **Việc cần làm:** chạy `check-heuristic` trên đồ thị thật (điều tra nếu `c < 0,999`); CLI `route --from-latlon ... --to-latlon ...`; test `realdata`: 200 cặp ngẫu nhiên (seed) trong SCC, so với NetworkX; đăng ký marker `realdata` trong `pyproject.toml`.
- 📁 `tests/test_realdata.py`, `pyproject.toml`
- 📦 Bằng chứng đúng trên dữ liệu thật + giá trị `c`, `v_max` ghi vào manifest.
- ✅ 200/200 cặp khớp; `reopened == 0` ở mọi truy vấn A*.
- ▶ `pytest -m realdata -q` · `python -m app.cli check-heuristic --graph data/processed/<id>.json`
- 🧠 Nếu `reopened > 0` thì heuristic có vấn đề gì.

---

## M5 — Ùn tắc và đóng đường

### T40 — Snapshot và luật ùn tắc theo vùng
- 👤 Duy Anh (Minh review) · ⏱ 3–4 h · ⛓ T10, T11
- **26/10:** Duy Anh làm thay Tiến (#65). **Còn:** CLI `--scenario`, `--block` — Duy Anh thêm sau khi T12 có `cli.py`.
- **Mục tiêu:** chi phí thay đổi theo kịch bản mà đồ thị gốc không đổi.
- **Việc cần làm:** thêm `Scenario` và `build_snapshot(graph, scenario, blocked)` theo DATA_MODEL mục 4 vào `graph/scenario.py`, dùng lại `Snapshot` và `make_snapshot` của T11 (không tạo kiểu mới); đọc `data/config/scenarios.json`; CLI thêm `--scenario` và `--block`.
- **Test bắt buộc** (trên fixture): vùng tâm A, r = 220 m, α = 2 → tuyến S→B→T, 100 s; α = 2 cho mọi cạnh → tuyến không đổi, 160 s; α < 1 bị từ chối; đồ thị gốc không đổi sau khi tạo snapshot.
- 📁 `backend/app/graph/scenario.py`, `tests/test_scenario.py`, `backend/app/cli.py`
- 📦 Snapshot.
- ✅ Test xanh.
- ▶ `pytest tests/test_scenario.py -q`
- 🧠 Vì sao nhân đều không đổi tuyến; vì sao lấy `max` thay vì tích; vì sao `α ≥ 1` giữ heuristic đúng.

### T41 — Đóng đoạn đường (cả cạnh đối nếu có)
- 👤 Duy Anh (Minh review) · ⏱ 2–3 h · ⛓ T40, T31
- **26/10:** Duy Anh làm thay Tiến (#67); code có cả đóng một chiều và hai chiều, bản đồ chỉ dùng chế độ đóng cả hai chiều.
- **Mục tiêu:** đóng đúng cạnh, kể cả cạnh song song và cạnh đối. Từ 26/10 sản phẩm chỉ có **một chế độ**: đóng một đoạn là đóng cả cạnh đối nếu có (D12).
- **Việc cần làm:** `reverse_twins(graph_meta)` (DATA_MODEL mục 4.2); kiểm tra `blocked_edge_ids` hợp lệ; test: đóng A→T → S→B→T; đóng A→T + B→T → `no_path`; đóng một trong hai cạnh song song thì cạnh còn lại vẫn đi được; tuyến mới không chứa cạnh đóng.
- 📁 `backend/app/graph/closures.py`, `tests/test_closures.py`
- 📦 Đóng đường.
- ✅ Test xanh; trên đồ thị thật, ghi số cạnh có/không có cạnh đối.
- ▶ `pytest tests/test_closures.py -q`
- 🧠 Một con đường hai chiều là hai cạnh có hướng; dual carriageway.

### T42 — Kịch bản ùn tắc cho demo
- 👤 Bảo (Tiến review) · ⏱ 2 h · ⛓ T40, T33
- **Mục tiêu:** có 2–3 kịch bản dễ nhận ra trên bản đồ và thực sự làm đổi tuyến.
- **Việc cần làm:** chọn 1–2 vùng quanh các trục đường quen thuộc ở Quận 1; ghi vào `data/config/scenarios.json` (`baseline`, `peak-center`, …); với 3 cặp điểm demo, chạy CLI với và không có kịch bản, ghi lại tuyến có đổi không.
- 📁 `data/config/scenarios.json`, PROGRESS.md
- 📦 File kịch bản đã thử.
- ✅ Ít nhất một cặp điểm có tuyến **đổi** dưới `peak-center`.
- ▶ `python -m app.cli route --graph ... --from-latlon ... --to-latlon ... --scenario peak-center --algo both`
- 🧠 Kịch bản là mô phỏng; nhãn "Cao điểm mô phỏng".

---

## M6 — Bản đồ tương tác

### T50 — Snap điểm về node
- 👤 Minh (Tiến hỗ trợ) · ⏱ 2 h · ⛓ T10, T31
- **Việc cần làm:** thay hàm `nearest_node_naive(graph, meta, lat, lon)` của T13 bằng `nearest_node(graph, meta, lat, lon, max_m=150)` chỉ trên node có `meta.node_in_scc`; trả `node_id`, `snap_distance_m`; lỗi rõ ràng khi quá xa/ngoài vùng; test trên fixture.
- 📁 `backend/app/graph/snap.py`, `tests/test_snap.py`
- 📦 Hàm snap · ✅ Test xanh · ▶ `pytest tests/test_snap.py -q`
- 🧠 Vì sao node gần nhất có thể ở bên kia sông/cầu; ngưỡng 150 m là giả định.

### T51 — API `/api/route` và `/api/dataset`
- 👤 Tiến · ⏱ 3 h · ⛓ T13, T33, T40, T41, T50
- **Từ review #67, #73:** lúc khởi động tính sẵn `geo_scale(graph)` và `reverse_twins` một lần (không để trong đoạn đo giờ, không tính lại mỗi lần đóng đường); snap không lùi về node ngoài SCC.
- **Việc cần làm:** mở rộng API skeleton của T13, chỉ thêm trường, không đổi contract v1; schema Pydantic theo ARCHITECTURE mục 4; `services/routing.py` (snap → snapshot → chạy thuật toán → đo thời gian → gắn geometry); `costs_match`; lỗi 422 có thông báo tiếng Việt; test bằng TestClient với fixture.
- 📁 `backend/app/api/schemas.py`, `routes.py`, `backend/app/services/routing.py`, `tests/test_api_route.py`
- 📦 API tìm đường.
- ✅ Test: route bình thường, `no_path`, cạnh đóng không tồn tại → 422, điểm quá xa → 422.
- ▶ `pytest tests/test_api_route.py -q` · thử bằng `http://127.0.0.1:8000/docs`
- 🧠 Tách API / service / thuật toán; vì sao request không lưu trạng thái.

### T52 — UI: chọn hai điểm, vẽ hai tuyến, bảng so sánh
- 👤 Minh · ⏱ 3 h · ⛓ T14, T51
- **Việc cần làm:** mở rộng UI skeleton của T14; nút **Tìm đường**, **Đảo chiều**, **Xóa**; vẽ tuyến Dijkstra và A*; bảng: chi phí (s, phút), quãng đường (m), node mở rộng, thời gian tính (ms), "Chi phí trùng khớp: có/không"; hiển thị trạng thái đang tính/lỗi; bỏ qua response cũ nếu đã có request mới.
- 📁 `frontend/src/main.ts`, `panel.ts`, `layers.ts`, `api.ts`
- 📦 Tìm đường trên web.
- ✅ Checklist UI-1…UI-4 trong PROGRESS.md đạt.
- ▶ Thủ công theo checklist; `npm run build` không lỗi.
- 🧠 Hai nhãn thời gian khác nhau; vì sao phải bỏ response cũ.

### T53 — UI: kịch bản và vùng ùn tắc
- 👤 Minh (Tiến hỗ trợ) · ⏱ 2 h · ⛓ T52
- **Rút gọn 26/10** (D12): bỏ lớp chấm node mở rộng; số node mở rộng vẫn có trong bảng của T52.
- **Việc cần làm:** dropdown kịch bản từ `/api/dataset`; vẽ vùng ùn tắc; tìm lại khi đổi kịch bản.
- 📁 `frontend/src/*.ts`
- 📦 Kịch bản trên bản đồ.
- ✅ Checklist UI-6 đạt.
- ▶ Thủ công.
- 🧠 Kịch bản là mô phỏng; vì sao ùn tắc theo vùng làm đổi tuyến còn nhân đều thì không.

### T54 — UI: đóng đoạn đường và báo không có đường
- 👤 Minh + Tiến · ⏱ 3 h · ⛓ T52, T41
- **Việc cần làm (một chế độ, 26/10):** bấm vào một đoạn **trên tuyến** → đóng đoạn đó (cả cạnh đối nếu có); tô đỏ; tự tìm lại; khi `no_path` thì hiện thông báo, không vẽ đường; nút "Mở lại tất cả".
- 📁 `frontend/src/*.ts`
- 📦 Đóng đường trên web.
- ✅ Checklist UI-7, UI-8 đạt.
- ▶ Thủ công.
- 🧠 Chặn theo edge id, không theo tên đường.

### T55 — Case demo và kiểm thử thủ công
- 👤 Bảo · ⏱ 2–3 h · ⛓ T54
- **Việc cần làm:** `data/demo/cases.json` (cặp điểm, kịch bản, cạnh đóng) cho các bước 1–2, 4–9 ở PROJECT_BRIEF mục 7 (bước 3 đã cắt; case "Kho + 5 điểm" cho bước 9 kiểm sau T73, UI-9); UI nạp case từ file (Minh hỗ trợ nếu cần); chạy toàn bộ checklist UI, chụp màn hình, ghi lỗi vào PROGRESS.md.
- 📁 `data/demo/cases.json`, `docs/PROGRESS.md`, `docs/img/` (ảnh)
- 📦 Bộ case demo + biên bản kiểm thử.
- ✅ Mọi case chạy được và cho kết quả như mô tả; lỗi (nếu có) được ghi rõ.
- ▶ Thủ công theo checklist.
- 🧠 Mỗi case minh họa điều gì (RQ nào).

---

## M7 — Benchmark và tăng quy mô

### T60 — Bộ chạy benchmark và 1.000 truy vấn vùng demo
- 👤 Duy Anh (Tiến review) · ⏱ 4 h · ⛓ T33
- **26/10:** Duy Anh làm phần khung (#71); còn chạy 1.000 cặp trên dữ liệu thật.
- **Việc cần làm:** theo [EXPERIMENT_PLAN.md](EXPERIMENT_PLAN.md) mục 2–3: sinh cặp có seed và phân tầng; lưu `queries.csv` trước khi đo; warm-up; lặp R lần, đổi thứ tự thuật toán; ghi `measurements.csv` và `env.json`; tắt trace.
- 📁 `scripts/run_benchmarks.py`, `results/<run_id>/`
- 📦 CSV đo thật cho E2.
- ✅ 1.000 cặp chạy xong; 100% cặp khớp chi phí; file có đủ cột ở EXPERIMENT_PLAN mục 3.3.
- ▶ `python scripts/run_benchmarks.py --suite demo --pairs 1000 --seed 42`
- 🧠 Median và p95; vì sao không lấy trung bình các tỉ số.

### T61 — Cắt lồng nhau cho thí nghiệm tăng quy mô
- 👤 Minh (Tiến hỗ trợ) · ⏱ 3 h · ⛓ T31
- **Việc cần làm:** `scripts/make_crops.py`: từ `outer.graphml` cắt **4** hình vuông lồng nhau, nửa cạnh 1 / 2 / 3 / 4,5 km (chốt 28/10 sau pilot); chọn SCC lồng nhau (DATA_MODEL mục 8.4); xuất JSON + manifest từng kích thước. Chạy pilot 20 truy vấn dài ở kích thước lớn nhất: nếu median Dijkstra > ~1 s thì bỏ hoặc giảm kích thước đó.
- 📁 `scripts/make_crops.py`, `data/processed/crop_*.json`
- 📦 4 đồ thị lồng nhau + bảng `|V|`, `|E|` đo được.
- ✅ Bảng kích thước dán vào EXPERIMENTS.md; xác nhận SCC nhỏ nằm trong SCC lớn.
- ▶ `python scripts/make_crops.py` · kiểm tra bảng in ra
- 🧠 Vì sao cắt từ một lần tải thay vì tải nhiều lần; vì sao vẽ biểu đồ theo `|V|` đo được chứ không theo bán kính.

### T62 — Chạy thí nghiệm tăng quy mô
- 👤 Tiến · ⏱ 3 h · ⛓ T60, T61
- **Việc cần làm:** workload fixed trips (250 cặp dùng chung cho cả 4 kích thước) theo EXPERIMENT_PLAN mục 6. Growing trips đã cắt 26/10 (D11).
- 📁 `scripts/run_benchmarks.py`, `results/<run_id>/`
- 📦 CSV E3 · ✅ Đủ 4 kích thước (bỏ bớt chỉ khi nhóm đồng ý riêng, ghi rõ lý do) · ▶ `python scripts/run_benchmarks.py --suite scaling --seed 42`
- 🧠 Fixed trips đo ảnh hưởng của bản đồ lớn hơn khi chuyến đi giữ nguyên; không suy ra cho chuyến đi dài hơn.

### T63 — Thí nghiệm ùn tắc và đóng đường
- 👤 Tiến (Bảo chạy lại để kiểm tra) · ⏱ 3 h · ⛓ T60, T41, T42
- **Việc cần làm:** theo EXPERIMENT_PLAN mục 7: cùng tập cặp, chạy dưới từng kịch bản; đóng cạnh theo quy tắc cố định; ghi tính khả thi, chi phí, node mở rộng, thời gian.
- 📁 `scripts/run_benchmarks.py`, `results/<run_id>/`
- 📦 CSV E4 · ✅ Có cả case còn đường và case không còn đường · ▶ `python scripts/run_benchmarks.py --suite scenario --seed 42`
- 🧠 Vì sao cận dưới lỏng hơn khi có ùn tắc.

### T64 — Vẽ biểu đồ
- 👤 Duy Anh (Minh review) · ⏱ 2 h · ⛓ T60 (định dạng CSV)
- **26/10:** Duy Anh làm thay Bảo (#72).
- **Việc cần làm:** `scripts/plot_results.py <run_dir>` vẽ các hình ở EXPERIMENT_PLAN mục 10; thử trước bằng CSV nhỏ sinh từ fixture (ghi rõ là dữ liệu thử, không đưa vào báo cáo).
- 📁 `scripts/plot_results.py`, `results/<run_id>/fig_*.png`
- 📦 Biểu đồ · ✅ Trục có đơn vị; chú thích ghi số cặp và dataset · ▶ `python scripts/plot_results.py results/<run_id>`
- 🧠 Đọc biểu đồ log–log; boxplot.

### G1 — Điểm kiểm bằng chứng 05/11
- 👤 Tiến (cả nhóm họp) · ⏱ 1 h · ⛓ T33, T41, T60
- **Đổi 26/10** (D13): G1 không còn quyết định tích hợp tour (tour đã nằm trong phạm vi cam kết); thay bằng điểm kiểm bằng chứng.
- **Mục tiêu:** ngày 05/11 biết chắc MVP tích hợp có kịp 08/11 không.
- **Việc cần làm:** kiểm từng điều kiện ở [ROADMAP.md](ROADMAP.md) mục 3 (bằng chứng đúng đắn, CSV benchmark đầu tiên, đóng đường chạy trên bản đồ, giờ còn lại của từng người); không kịp thì kích hoạt cắt theo [đề xuất phạm vi](proposals/2026-10-26-pham-vi.md) mục 4; ghi quyết định vào issue và PROGRESS.md.
- 📁 `docs/PROGRESS.md`
- 📦 Quyết định có ghi lại.
- ✅ Mọi điều kiện được đánh dấu đạt/không đạt kèm bằng chứng (link PR, `run_id`).
- ▶ Review biên bản họp.
- 🧠 Quản lý phạm vi: vì sao cắt bớt tốt hơn trễ hạn.

### T65 — Ghi kết quả vào EXPERIMENTS.md
- 👤 Tiến + cả nhóm · ⏱ 3 h · ⛓ T62, T63, T64
- **Việc cần làm:** điền bảng ở EXPERIMENT_PLAN mục 9 bằng số đo thật; mỗi bảng ghi `run_id`, `dataset_id`, máy đo; viết phần diễn giải và các trường hợp A* không có lợi.
- 📁 `docs/EXPERIMENTS.md`
- 📦 Kết quả cho essay · ✅ Mọi số có `run_id` truy ngược được · ▶ Review chéo: một người khác chạy lại một bảng và ra số cùng bậc
- 🧠 Phân biệt số đo với diễn giải.

---

## M8 — Tour (E1)

Sáng 26/10 cắt, chiều 26/10 giữ lại (D10): T70, T71 đã xong; T72–T74 làm trong tuần 3 và phải xong trước MVP 08/11.

### T70 — Tour trên ma trận: chi phí, NN, 2-opt có hướng
- 👤 Duy Anh · ⏱ 3–4 h · ⛓ T00 (không cần dữ liệu thật) · bắt đầu sau T22 · ✅ đã merge 26/10 (#69)
- **Việc cần làm:** `tour_cost(D, order)` (kho cố định đầu/cuối); `nearest_neighbor(D)` với tie-break theo chỉ số; `two_opt(D, order)` tính lại **toàn bộ** chi phí cho mỗi ứng viên; chọn tour rẻ nhất trong {thứ tự nhập, NN, NN+2-opt}. Test: 1 điểm; ma trận bất đối xứng; một ma trận nhỏ tự dựng làm ví dụ phản chứng: công thức delta đối xứng dự đoán tour rẻ hơn nhưng chi phí tính lại toàn bộ lại đắt hơn (script proposal có ví dụ 17 → 13 → 20 ở backup slide B1, nhưng repo không có ma trận gốc nên phải dựng lại và kiểm tra); 2-opt không làm tăng chi phí; giữ đủ điểm.
- 📁 `backend/app/algorithms/tour.py`, `tests/test_tour.py`
- 📦 Thuật toán tour · ✅ Test xanh · ▶ `pytest tests/test_tour.py -q`
- 🧠 TSP bất đối xứng; vì sao 2-opt chỉ cho cực trị địa phương; vì sao đảo đoạn làm đảo chiều các chặng bên trong.

### T71 — Held–Karp làm đối chứng
- 👤 Duy Anh · ⏱ 2–3 h · ⛓ T70 · ✅ đã merge 26/10 (#70)
- **Việc cần làm:** `held_karp(D)` cho n ≤ 10; test so với duyệt mọi hoán vị khi n ≤ 7; đo thời gian n = 4, 6, 8, 10.
- 📁 `backend/app/algorithms/tour.py`, `tests/test_tour.py`
- 📦 Lời giải tối ưu cho case nhỏ · ✅ Khớp duyệt toàn bộ · ▶ `pytest tests/test_tour.py -q`
- 🧠 Công thức `DP[S, j]`; độ phức tạp `O(2^n · n²)`.

### T72 — Ma trận chi phí từ đồ thị và `/api/tour`
- 👤 Tiến · ⏱ 3–4 h · ⛓ T70, T51
- **Việc cần làm:** Dijkstra một nguồn tới nhiều đích (dừng khi đã pop đủ các đích) để xây từng hàng; kiểm tra mọi cặp hữu hạn, nếu không thì trả `infeasible_under_model` + danh sách điểm lỗi; ghép tuyến các chặng; endpoint `/api/tour`.
- 📁 `backend/app/services/tour.py`, `backend/app/api/*.py`, `tests/test_api_tour.py`
- 📦 API tour · ✅ Chi phí tour bằng tổng chi phí các chặng đã dựng · ▶ `pytest tests/test_api_tour.py -q`
- 🧠 Vì sao không dùng khoảng cách thẳng cho ma trận.

### T73 — UI tour tối giản
- 👤 Minh · ⏱ 3 h · ⛓ T72
- **Việc cần làm:** preset kho + 5 điểm từ `cases.json`; 3 thẻ Thứ tự nhập / NN / NN + 2-opt; marker đánh số theo thẻ được chọn.
- 📁 `frontend/src/*.ts` · 📦 Demo tour · ✅ Bước 9 của kịch bản demo chạy được · ▶ Thủ công
- 🧠 Hai tầng của bài toán giao hàng.

### T74 — Benchmark tour
- 👤 Tiến (Bảo chạy) · ⏱ 2–3 h · ⛓ T71, T72
- **Việc cần làm:** EXPERIMENT_PLAN mục 8; thêm biểu đồ E5 (mục 10, hình 6) vào `plot_results.py`.
- 📁 `scripts/run_benchmarks.py` · 📦 CSV E5 · ✅ Bảng improvement và gap có số đo · ▶ `python scripts/run_benchmarks.py --suite tour --seed 42`
- 🧠 Improvement % và gap %.

---

## M9 — Hoàn thiện

### T80 — Đóng băng tính năng và chạy trên máy thứ hai
- 👤 Bảo · ⏱ 2–3 h · ⛓ T54, T55, T73, G1
- **Việc cần làm:** từ 09/11 không thêm tính năng (D13); clone repo sạch trên máy khác, làm đúng theo README (tải dataset từ Release, kiểm tra hash), chạy demo; ghi mọi bước bị vướng.
- 📦 Biên bản chạy máy thứ hai · ✅ Chạy được mà không cần ai sửa tay; hoặc README đã được sửa · ▶ Thủ công
- 🧠 Tái lập là gì.

### T81 — Đồng bộ tài liệu
- 👤 Tiến · ⏱ 2 h · ⛓ T65
- **Việc cần làm:** cập nhật README (cách chạy, kết quả thật, giới hạn); kiểm DEMO.md (đã viết lại 26/10) khớp app; ghi trong TOPIC.md những điểm đã đổi (trỏ tới PROJECT_BRIEF mục 4); điền `docs/ALGORITHMS.md`.
- 📦 Tài liệu khớp code · ✅ Không còn mô tả chức năng chưa làm như đã làm · ▶ Review chéo
- 🧠 —

### T82 — Tập demo và quay video dự phòng
- 👤 Minh + Bảo · ⏱ 2 h · ⛓ T55, T80
- **Việc cần làm:** chạy kịch bản demo 3 lần với đồng hồ; quay màn hình bản tốt nhất; kiểm tra checklist DEMO.md mục 3.
- 📦 Video + checklist · ✅ Demo ≤ 4 phút · ▶ Thủ công
- 🧠 Mỗi bước demo trả lời câu hỏi nghiên cứu nào.

### T83 — Essay: phương pháp, kết quả, giới hạn
- 👤 Cả nhóm (Tiến điều phối) · ⏱ nhiều buổi · ⛓ T65
- **Bắt đầu từ tuần 3** (D13): phần dữ liệu và phương pháp (Bảo + Tiến) từ 02/11; phần kết quả viết sau khi có số đo đã kiểm (T65).
- **Việc cần làm:** theo khung TOPIC.md mục 21.1; mỗi người viết phần mình làm; mọi số liệu lấy từ EXPERIMENTS.md kèm `run_id`; chứng minh heuristic ở dạng phác thảo có trích dẫn.
- 📦 Bản nháp essay · ✅ 10 trang double spaced, có bìa đủ tên/MSSV · ▶ Review chéo
- 🧠 Toàn bộ.
