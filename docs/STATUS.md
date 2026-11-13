# STATUS
Cập nhật: 14/11/2026 · Người tích hợp: Tiến · Đọc file này đầu mỗi session; giữ ≤ 100 dòng, ghi đè mỗi cuối session.

Bộ nhớ dự án: mục tiêu, phạm vi, quyết định ở [PROJECT_BRIEF.md](PROJECT_BRIEF.md) mục 4 (D1–D18) · kiến trúc và API ở [ARCHITECTURE.md](ARCHITECTURE.md) · **kế hoạch phần còn lại ở [ROADMAP.md](ROADMAP.md) mục 7 (R0–R4)** · trạng thái từng task và bằng chứng ở [PROGRESS.md](PROGRESS.md) · số đo ở [EXPERIMENTS.md](EXPERIMENTS.md).

## Tóm tắt
- **Hiện tại (main, 14/11):** đủ lõi của proposal: dữ liệu OSM đóng băng (Release `data-raw-20261024`), Dijkstra, A*, đối chứng NetworkX (fixture, đồ thị ngẫu nhiên, 200 cặp đồ thị thật), ùn tắc theo vùng, đóng đoạn đường, tour NN / 2-opt có hướng / Held–Karp, API `/api/route`, `/api/tour`, `/api/dataset`, `/api/network`, giao diện React + Astryx (T56), kết quả E2–E5 và E2b. Mở rộng sau kế hoạch: ALT, Dijkstra hai chiều, Or-opt (D17).
- **Mong muốn:** làm trọn như bản cuối (essay 10 trang, thuyết trình 15 phút có demo), dù không còn nộp chính thức (D18).
- **Phải giữ nguyên:**
  - `main` chỉ nhận PR có review + CI xanh (`backend`, `frontend`, `identity` bắt buộc);
  - commit chỉ mang tên thành viên nhóm (job `identity`);
  - dữ liệu thô đóng băng theo sha256;
  - contract `/api/route` v1 chỉ được thêm trường;
  - không số liệu nào chưa đo; mọi số trong tài liệu có `run_id`.
- **Chưa biết:** nền tile OSM thật (UI-1) trên giao diện mới, vì mạng các máy kiểm hiện chặn `tile.openstreetmap.org`.

## Đang ở đâu
- R0 (tài liệu khớp thực tế): EXPERIMENTS đã sửa và thêm E2b (#127); PR đồng bộ PROGRESS, STATUS, ROADMAP, DEMO, ARCHITECTURE đang review.
- Tiếp theo: R1, lập lại tour sau khi đóng đường. Đây là khoảng trống lớn nhất so với proposal (slide 3, 7, 12): backend `plan_tour()` đã nhận `blocked_edge_ids`, nhưng chế độ tour trên UI chưa gửi cạnh đóng, chưa cho bấm đóng đoạn, và chưa có so sánh giữ thứ tự cũ / sắp lại.

## Bị chặn / rủi ro
- UI-1 chưa kiểm được trên máy này; nền dự phòng `/api/network` đã có (T56 R8). Kiểm ở R3 trên mạng khác; chuẩn bị video demo.
- Các PR cũ đã có PR khác thay (#97, #104, #107, #108) còn mở; cần đóng tay trên GitHub.
- MVP 08/11 không đạt đúng hạn (PROGRESS mục 1); không ảnh hưởng kế hoạch mới vì không còn hạn nộp.

## Quyết định
| Quyết định | Trạng thái | Nguồn |
|---|---|---|
| Kế hoạch R0–R4 thay lịch M9 (D18) | **Đã chốt** | Tiến ủy quyền, 14/11 |
| R1: báo cả "giữ thứ tự cũ" và "sắp lại" trên cùng snapshot; cho đóng đoạn trên tour; thêm case "tour không còn khả thi" | **Đã chốt** | Tiến ủy quyền, 14/11 (ROADMAP mục 7) |
| Bỏ khỏi DEMO: nhật ký snapshot, so Dijkstra/A* trên một chặng của tour | **Đã chốt** | D18 |
| Giữ ALT, Dijkstra hai chiều, Or-opt làm phần mở rộng | **Đã chốt** | D17 |
| Giao diện React + Astryx | **Đã merge** (#103) | D15 |
| Ngưỡng snap 150 m | Giả định hiện hành, đã dùng trong mọi thí nghiệm | — |

## Bước tiếp theo
1. Merge PR đồng bộ tài liệu R0.
2. R1: viết phiếu `docs/tasks/R1-tour-closure.md` (mức Standard), rồi làm API, UI, test, case demo mới.
3. R2: E5 thêm n = 5, báo max và p90; thí nghiệm nhỏ giữ thứ tự cũ / sắp lại sau khi đóng.
4. R3: chạy trên máy thứ hai theo README; kiểm UI-1 ở mạng khác.
5. R4: essay, slide, video demo.

## Bộ kiểm nhanh (chạy đầu mỗi session)
- `.venv\Scripts\python.exe -m pytest -q` → 14/11 trên main: 429 passed, 6 skipped (6 test của `test_crops.py` tự bỏ qua khi máy chưa dựng 4 file `crop_r*.json` bằng `make_crops.py`; có đồ thị demo thì các test `realdata` khác vẫn chạy)
- `cd frontend; npm run build` → build được (Vite cảnh báo chunk > 500 KB, chấp nhận vì chạy local)
- `python scripts/tracking/create_backlog.py --dry-run` → không lỗi (48 task, 147 giờ ước lượng)
- Mỗi tuần: `.venv\Scripts\python.exe -m pip_audit -r requirements-lock.txt` · `cd frontend; npm audit` (job `audit` trong CI chạy ở mỗi PR)

## Lệnh khác
- Dựng môi trường: `powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1` (thêm `-Data` cho OSMnx)
- Dữ liệu: tải Release `data-raw-20261024` rồi `python scripts/prepare_data.py build --area demo` (ONBOARDING mục 3)
- Chạy: `$env:SAIGO_GRAPH = "data/processed/hcm-benthanh-r2000-20261024.json"; uvicorn app.main:app --reload --app-dir backend` + `cd frontend; npm run dev` → http://localhost:5173
- Thí nghiệm: E2 `run_benchmarks.py --suite demo` · E3 `run_scaling.py` · E4 `run_scenarios.py` · E5 `run_tour.py` · E2b `compare_algorithms.py`; bảng: `summarize_results.py results/<run_id>`; hình: `plot_results.py results/<run_id>`
- Burndown: `python scripts/tracking/burndown.py --out build/tracking`

## Tài liệu lệch với code / với quyết định
- README: dòng trạng thái đã cập nhật 14/11; phần phạm vi và kết quả chính viết lại ở R4 cùng essay.
- `docs/ALGORITHMS.md` chưa có ALT, Dijkstra hai chiều, Or-opt (T81, R4).
- TOPIC.md là đặc tả gốc 01/10; khi khác PROJECT_BRIEF thì PROJECT_BRIEF được ưu tiên.
