# SaiGo

**Delivery Route Planning on Ho Chi Minh City Street Networks Using Heuristic Search**
Lập kế hoạch lộ trình giao hàng trên mạng đường TP.HCM bằng tìm kiếm heuristic.

Đồ án môn Introduction to AI (261_72ITSE30303_01) — Nhóm 4: Võ Việt Tiến, Bùi Duy Anh, Đỗ Quốc Bảo, Võ Hoàng Minh.

> **Trạng thái (14/11):** chạy trên đồ thị thật vùng trung tâm (1.889 node): Dijkstra, A* (khớp NetworkX), ùn tắc theo vùng, đóng đoạn đường, tour NN / 2-opt có hướng / Held–Karp, API và giao diện React; kết quả thực nghiệm E2–E5 ở [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md). Chế độ tour lập lại được sau khi đóng đường, so giữ thứ tự cũ với sắp lại (R1). Chi tiết: [docs/STATUS.md](docs/STATUS.md).

SaiGo dùng **mạng đường thực** từ OpenStreetMap, nhưng **thời gian di chuyển và giao thông là mô phỏng**.
Không cung cấp ETA giao thông trực tiếp hay điều hướng thương mại.

## Phạm vi

- Tìm đường: Dijkstra và A* (tự cài đặt, đối chứng với NetworkX)
- Thứ tự giao: thứ tự nhập → Nearest Neighbor → 2-opt trên ma trận chi phí có hướng; Held–Karp làm đối chứng
- Thí nghiệm tăng quy mô bản đồ: A* so với Dijkstra trên 4 kích thước đồ thị
- Kịch bản giao thông mô phỏng và chặn đường, lập lại lộ trình; với tour: so "giữ thứ tự cũ" với "sắp lại"
- Benchmark offline có thể tái lập
- Mở rộng ngoài proposal (D17): Dijkstra hai chiều, ALT (A* với landmark), Or-opt

Đặc tả đầy đủ: [docs/TOPIC.md](docs/TOPIC.md) · thuật toán: [docs/ALGORITHMS.md](docs/ALGORITHMS.md).
Kế hoạch triển khai: [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) · **trạng thái hiện tại (đọc đầu tiên):** [docs/STATUS.md](docs/STATUS.md) · bằng chứng: [docs/PROGRESS.md](docs/PROGRESS.md).

## Kết quả chính

Tóm tắt từ [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md); mỗi dòng ghi `run_id` trong `results/`. Thời gian đo trên laptop của nhóm, chỉ để so tương đối giữa các thuật toán.

- **A* đúng nhưng chưa nhanh hơn rõ trên vùng demo.** A* cho cùng chi phí với Dijkstra ở 1.000/1.000 cặp và chỉ mở khoảng 40% số node (median r = 0,398), nhưng median tỉ số thời gian chỉ 1,03; A* nhanh hơn rõ ở chuyến trung bình (s = 1,22) (`20261031-1556-demo-054f300`, kiểm chéo trên máy thứ hai).
- **Heuristic mạnh hơn giúp ở bản đồ lớn và chuyến dài.** Trên vùng 4,5 km, tầng dài, ALT nhanh hơn Dijkstra 2,67 lần (A* 1,27 lần); ở tầng ngắn ALT lại chậm hơn, có thể vì mỗi node tốn thêm thời gian tính heuristic (chưa đo tách) (`20261113-1327-compare-871bf02`).
- **Ùn tắc và đóng đường chỉ ảnh hưởng chuyến đi qua vùng đó.** Ùn tắc đổi tuyến ở 16–19% số cặp (median tăng chi phí 0%, p90 10–16%). Khi không còn đường, A* phải duyệt hết vùng tới được như Dijkstra nên mất lợi thế (`20261113-0444-scenario-c1cd80b`).
- **NN + 2-opt gần tối ưu ở median nhưng là tìm kiếm cục bộ.** So với thứ tự nhập, NN + 2-opt rẻ hơn median 11,6% (4 điểm) đến 41,0% (10 điểm); median gap so với Held–Karp 0–1,8%, gap lớn nhất trong 100 bộ ngẫu nhiên 14,1% (`20261113-0448-tour-12dd1e0`, `20261114-0517-tour-04a0d7e`). Case demo 5 điểm kẹt ở gap 43% vì ma trận chi phí bất đối xứng.
- **Đóng một đoạn trên tour thường chỉ làm tour dài thêm ít.** Giữ thứ tự cũ tăng median 1,4%; sắp lại chỉ đổi thứ tự ở 3/18 bộ; 2/20 bộ không còn tour khép kín và app báo rõ điểm không tới được (`20261114-0517-tourclosure-04a0d7e`).

## Theo dõi công việc nhóm

| | |
|---|---|
| Bảng công việc | [GitHub Project — SaiGo Delivery Plan](https://github.com/users/NeitLN/projects/3) |
| Burndown (cập nhật mỗi ngày) | Issue ghim có nhãn [`tracking`](https://github.com/NeitLN/SaiGo/issues?q=label%3Atracking) |
| Mốc | [Milestones](https://github.com/NeitLN/SaiGo/milestones) |
| Thành viên và phân công | [docs/team/TEAM.md](docs/team/TEAM.md) |
| Quy trình (branch, PR, review) | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Cách đọc số liệu theo dõi | [docs/tracking/README.md](docs/tracking/README.md) |

## Cấu trúc

| Đường dẫn | Nội dung |
|---|---|
| `backend/app/api/` | Endpoint FastAPI và schema |
| `backend/app/services/` | Điều phối route/tour/snapshot |
| `backend/app/algorithms/` | Dijkstra, A*, heuristic, NN, 2-opt, Held–Karp; mở rộng: Dijkstra hai chiều, ALT, Or-opt |
| `backend/app/graph/` | Adapter, geometry, snap, manifest |
| `frontend/` | React + Astryx + Vite + Leaflet |
| `scripts/` | Chuẩn bị dữ liệu, benchmark, vẽ biểu đồ |
| `tests/` | pytest |
| `data/config/`, `data/demo/` | Cấu hình và case demo |
| `results/` | Kết quả benchmark |
| `docs/` | Đề tài, thuật toán, thực nghiệm, demo |

## Chạy local (Windows)

Yêu cầu: Git, **Python 3.11.9** ([bộ cài Windows](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe); CI và file khóa phiên bản dùng 3.11), Node.js 20+. Thành viên mới: đọc [docs/team/ONBOARDING.md](docs/team/ONBOARDING.md).

```powershell
# Dựng môi trường một lần: tạo .venv, cài thư viện, chạy test, build frontend
powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1          # thêm -Data để cài OSMnx

# Backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --app-dir backend

# Frontend (terminal khác)
cd frontend
npm run dev
```

Mở http://localhost:5173. Frontend gọi backend qua proxy `/api` → `http://127.0.0.1:8000`.

Chạy test: `.venv\Scripts\python.exe -m pytest -q`.

Nên clone vào thư mục không dấu (ví dụ `C:\dev\SaiGo`): trên Windows, `pip install -e` lỗi khi đường dẫn có chữ tiếng Việt. Script ở trên không dùng `-e` nên vẫn chạy được ở đường dẫn có dấu.

## Dữ liệu và giấy phép

Dữ liệu đường phố © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), giấy phép ODbL.
Giấy phép mã nguồn chưa chọn; giấy phép mã nguồn không bao phủ dataset.
