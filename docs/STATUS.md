# STATUS
Cập nhật: 26/10/2026, chiều · Người tích hợp: Tiến · Đọc file này đầu mỗi session; giữ ≤ 100 dòng, ghi đè mỗi cuối session.

Bộ nhớ dự án: mục tiêu/phạm vi/deadline ở [PROJECT_BRIEF.md](PROJECT_BRIEF.md) · quyết định kỹ thuật ở [ARCHITECTURE.md](ARCHITECTURE.md) và [DATA_MODEL.md](DATA_MODEL.md) · mốc, quyết định đắt nếu đổi, kế hoạch tuần ở [ROADMAP.md](ROADMAP.md) · từng task ở [TASKS.md](TASKS.md) + GitHub Issues · bằng chứng chi tiết và lỗi tồn tại ở [PROGRESS.md](PROGRESS.md).

## Tóm tắt
- **Hiện tại (main `e172ea9`):** trên `main` đã có bộ nạp đồ thị (T01), hàm địa lý (T10), Dijkstra (T11), A* (T20), đối chứng NetworkX trên đồ thị ngẫu nhiên (T21), báo cáo heuristic (T22), snapshot ùn tắc (T40), đóng đường (T41), khung benchmark (T60), biểu đồ (T64), tour trên ma trận (T70, T71), API skeleton `/api/route` trên `mini.json` (T13). Chưa có: dữ liệu thật dùng chung, bản đồ (T14), số đo benchmark.
- **Mong muốn:** walking skeleton chạy trên 2 máy trước 29/10; **điểm kiểm bằng chứng 05/11**; MVP tích hợp 08/11 (gồm cả tour); final 12/11.
- **Phải giữ nguyên:**
  - `main` chỉ nhận PR có review + CI xanh;
  - commit chỉ mang tên thành viên nhóm (job `identity`);
  - dữ liệu thô đóng băng theo sha256;
  - contract `/api/route` v1 chỉ được thêm trường;
  - không số liệu nào chưa đo.
- **Chưa biết:** máy thứ hai build lại dữ liệu có ra cùng sha256 không; Python chạy đồ thị lớn nhất mất bao lâu.

## Đang ở đâu
- **Chiều 26/10 Duy Anh quay lại** và merge 10 PR (#64–#73). Phần thuật toán và khung thực nghiệm gần như đã xong trên fixture; đường găng giờ là **dữ liệu thật (T34)** và **bản đồ (T14 → T52–T54)**.
- **26/10, lịch sử `main` đã được viết lại** để bỏ 2 dòng đồng tác giả ngoài nhóm. Ai clone trước đó: `git fetch origin; git switch main; git reset --hard origin/main`.
- Chờ review / merge:
  - PR đồng bộ phạm vi (branch `t07b-sync-scope`): tài liệu theo quyết định 26/10.
  - **Minh:** #46 → #47 → #53 mất approve vì Duy Anh gộp `main` vào (và đã sửa `test_load_graph_reads_file`); cần approve lại rồi merge, sau đó tạo Release (T34).
- Còn lại tuần 2: Minh T34, T14; Bảo T15, T12. MW chỉ còn chờ T14 (phía API đã xong ở #73). Chi tiết: [ROADMAP](ROADMAP.md) mục 6.

## Bị chặn / rủi ro
- `outer.graphml` (sha256 `24a28327…`) chỉ có trên máy Minh; chưa có Release. Mọi tiêu chí trên dữ liệu thật (T01, T22, T33, T60) chờ việc này.
- Review vội: 9 PR của Duy Anh (300–1.100 dòng) được approve sau 0–6 phút, không có nhận xét. Từ nay người review chạy test và để lại ít nhất một nhận xét cụ thể.
- Minh dùng Python 3.14 (networkx 3.7); nhóm chuẩn là 3.11 (networkx 3.6.1). Benchmark chỉ chạy trên 3.11.

## Quyết định
| Quyết định | Trạng thái | Nguồn |
|---|---|---|
| Walking skeleton MW (T13–T15) trước 29/10 | **Đã duyệt** | Tiến, 25/10 |
| Contract `/api/route` v1 ([ARCHITECTURE](ARCHITECTURE.md) mục 4.1) | **Đã chốt** | 25/10 |
| Khóa phiên bản (`requirements-lock.txt`, Python 3.11), job `audit` | **Đã duyệt** | 25/10 |
| Kế hoạch tuần 2 ([ROADMAP](ROADMAP.md) mục 6): T13 → Minh, T12 → Bảo | **Đã duyệt** (#56, ghi nhận ở #63) | Nhóm, sáng 26/10 |
| Đổi phạm vi ([đề xuất](proposals/2026-10-26-pham-vi.md)): bỏ T32, RQ1b chỉ fixed trips (4 kích thước, chốt 28/10), bản đồ rút gọn, điểm kiểm 05/11 + MVP 08/11 | **Đã duyệt** | Nhóm, sáng 26/10 |
| Tour (D10): sáng cắt, **chiều giữ lại**; T72–T74 trước 08/11 | **Đã chốt** | Tiến, chiều 26/10 |
| Không gửi thư riêng cho giảng viên; lý do đổi phạm vi ghi trong PROJECT_BRIEF mục 4 và essay | **Đã chốt** | Tiến, chiều 26/10 |
| Q1–Q5, Q7 ([ROADMAP](ROADMAP.md) mục 5) | **Đã duyệt**; Q2 còn chờ Release (T34) | Nhóm, 26/10 |
| Ngưỡng snap 150 m | **[Đề xuất]**, giả định hiện hành | — |
| Khoản cắt 4 (đóng đường qua API/CLI) và 5 (RQ1b còn 2 kích thước) | **Chưa kích hoạt**; cần nhóm đồng ý riêng | — |

## Bước tiếp theo
1. Merge PR đồng bộ; đóng T32 *not planned*; chạy `create_backlog.py --sync` và `setup_project.py --sync` (tạo T34, đổi người làm và mô tả issue theo TASKS).
2. Đưa `identity` vào check bắt buộc của branch `main`.
3. Minh: approve lại #46 → #47 → #53, merge, tạo Release (T34); rồi T14.
4. Bảo: T15 (29/10), T12 (30–31/10).
5. Họp 01/11: rà ngân sách tuần 3 khi đã có Duy Anh, gồm T72–T74; chia lại người trả lời câu hỏi bảo vệ.

## Bộ kiểm nhanh (chạy đầu mỗi session)
- `.venv\Scripts\python.exe -m pytest -q` → tại `main` `a86cf9e` (26/10): 231 passed, 1 skipped (test `realdata`, chưa có dữ liệu)
- `cd frontend; npm run build` → build được
- `python scripts/tracking/create_backlog.py --dry-run` → không lỗi, in tổng số task/giờ
- Mỗi tuần: `.venv\Scripts\python.exe -m pip_audit -r requirements-lock.txt` · `cd frontend; npm audit` (job `audit` trong CI làm việc này ở mỗi PR)

## Lệnh khác
- Dựng môi trường: `powershell -ExecutionPolicy Bypass -File scripts\setup_dev.ps1` (thêm `-Data` cho OSMnx)
- Chạy: `uvicorn app.main:app --reload --app-dir backend` + `cd frontend; npm run dev`
- Burndown: `python scripts/tracking/burndown.py --out build/tracking`
- Đồng bộ backlog: `create_backlog.py --sync`, `setup_project.py --sync`

## Tài liệu lệch với code / với quyết định
- [ARCHITECTURE.md](ARCHITECTURE.md) mục 3 và 4 mô tả file/API **dự kiến**. API có `/api/health` và `/api/route` (skeleton, `services/routing.py`); chưa có `cli.py`, `snap.py`.
- Issue trên GitHub (người làm, mô tả T32/T53/T54/T61/T62/G1) còn theo kế hoạch cũ cho tới khi chạy `--sync` sau PR đồng bộ. Khi lệch, TASKS.md được ưu tiên.
