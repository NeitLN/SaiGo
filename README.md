# SaiGo

**Delivery Route Planning on Ho Chi Minh City Street Networks Using Heuristic Search**
Lập kế hoạch lộ trình giao hàng trên mạng đường TP.HCM bằng tìm kiếm heuristic.

Đồ án môn Introduction to AI (261_72ITSE30303_01) — Nhóm 4: Võ Việt Tiến, Bùi Duy Anh, Đỗ Quốc Bảo, Võ Hoàng Minh.

> **Trạng thái (26/10):** đã có bộ nạp đồ thị, Dijkstra, A*, đối chứng NetworkX, snapshot ùn tắc, đóng đường, thuật toán tour và khung benchmark, kiểm trên đồ thị mẫu và đồ thị ngẫu nhiên. Chưa có dữ liệu thật đã nạp, API tìm đường hay kết quả thực nghiệm. Chi tiết: [docs/STATUS.md](docs/STATUS.md).

SaiGo dùng **mạng đường thực** từ OpenStreetMap, nhưng **thời gian di chuyển và giao thông là mô phỏng**.
Không cung cấp ETA giao thông trực tiếp hay điều hướng thương mại.

## Phạm vi

- Tìm đường: Dijkstra và A* (tự cài đặt)
- Thứ tự giao: thứ tự nhập → Nearest Neighbor → 2-opt trên ma trận chi phí có hướng; Held–Karp làm đối chứng
- Thí nghiệm tăng quy mô bản đồ: A* so với Dijkstra trên 4 kích thước đồ thị
- Kịch bản giao thông mô phỏng và chặn đường, lập lại lộ trình
- Benchmark offline có thể tái lập

Đặc tả đầy đủ: [docs/TOPIC.md](docs/TOPIC.md).
Kế hoạch triển khai: [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) · **trạng thái hiện tại (đọc đầu tiên):** [docs/STATUS.md](docs/STATUS.md) · bằng chứng: [docs/PROGRESS.md](docs/PROGRESS.md).

## Theo dõi công việc nhóm

| | |
|---|---|
| Bảng công việc | [GitHub Project — SaiGo Delivery Plan](https://github.com/users/NeitLN/projects/3) |
| Burndown (cập nhật mỗi ngày) | Issue ghim có nhãn [`tracking`](https://github.com/NeitLN/SaiGGo/issues?q=label%3Atracking) |
| Mốc | [Milestones](https://github.com/NeitLN/SaiGGo/milestones) |
| Thành viên và phân công | [docs/team/TEAM.md](docs/team/TEAM.md) |
| Quy trình (branch, PR, review) | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Cách đọc số liệu theo dõi | [docs/tracking/README.md](docs/tracking/README.md) |

## Cấu trúc

| Đường dẫn | Nội dung |
|---|---|
| `backend/app/api/` | Endpoint FastAPI và schema |
| `backend/app/services/` | Điều phối route/tour/snapshot |
| `backend/app/algorithms/` | Dijkstra, A*, heuristic, NN, 2-opt, Held–Karp |
| `backend/app/graph/` | Adapter, geometry, snap, manifest |
| `frontend/` | TypeScript + Vite + Leaflet |
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

Nên clone vào thư mục không dấu (ví dụ `C:\dev\SaiGGo`): trên Windows, `pip install -e` lỗi khi đường dẫn có chữ tiếng Việt. Script ở trên không dùng `-e` nên vẫn chạy được ở đường dẫn có dấu.

## Dữ liệu và giấy phép

Dữ liệu đường phố © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), giấy phép ODbL.
Giấy phép mã nguồn chưa chọn; giấy phép mã nguồn không bao phủ dataset.
