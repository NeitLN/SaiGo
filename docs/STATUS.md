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
- R0 xong (#127, #128).
- R1 xong (#129): lập lại tour sau khi đóng đường, giữ thứ tự cũ / sắp lại, case "Tour không còn khả thi"; bằng chứng ở [phiếu R1](tasks/R1-tour-closure.md).
- R2 xong (#130): E5 thêm n = 5, cột p90 và max Gap; E5b tour sau khi đóng đường; Or-opt ghi rõ chỉ minh họa. Phần "Minh chạy lại một bảng trên máy mình" chuyển sang R3 vì cần máy khác.
- Review UI 14/11 (chạy thử toàn app, 6 vai: QA, người dùng cuối, UI/UX, frontend + a11y, PM, giảng viên; biên bản ngoài repo). Đợt 1 (an toàn demo, số đúng) gồm 4 PR: bấm trượt bản đồ không xoá kết quả, sửa Đảo chiều/bấm marker/kịch bản lệch; API trả hình học cạnh đóng, vẽ cạnh đóng của case, tô đỏ điểm hỏng, tự thu phóng; nhãn và số trung thực; case dựng sẵn cho bước 10. Đợt 2 (5 PR, #138–#142): chênh lệch trước/sau kèm tuyến lần trước vẽ mờ; công tắc lớp node đã mở rộng (tĩnh, trace bằng request riêng); thẻ Held–Karp xem được (badge "Rẻ nhất" so cả tối ưu); bố cục theo độ rộng cho máy chiếu 1024–1280 px và điện thoại; kiểm điểm ngay lúc bấm (`/api/snap`), nút "Bỏ điểm cuối", viền vùng có dữ liệu. Đợt 3 (5 PR, #143–#147): vùng ùn tắc màu cảnh báo, nhãn ở mép, tuyến có viền tối, chú giải nổi; tour có mũi tên chiều, kho là ô vuông, tên điểm cạnh số; đặt điểm từ danh sách địa danh (dùng được bằng bàn phím); công tắc "Phần mở rộng" (ALT, hai chiều, Or-opt); đọc kết quả cho trình đọc màn hình, lỗi role="alert", nút zoom tiếng Việt, bận/lỗi tách theo chế độ, badge server tự cập nhật mỗi 10 s, nền dự phòng tự thử lại, gzip. Tách state App.tsx (làm luôn 14/11, Tiến quyết định không đợi sau demo): logic thuần sang `appLogic.ts` có test, trạng thái server sang hook `useServerStatus`; App.tsx 835 → 714 dòng.
- T81 xong (14/11): ALGORITHMS.md có tóm tắt mọi thuật toán đã cài; README có kết quả chính kèm `run_id`; TOPIC.md trỏ sang PROJECT_BRIEF mục 4. #107, #108 đã đóng.
- R4, phần làm được trên máy này đã xong: bản nháp essay tiếng Anh [essay/essay.md](essay/essay.md) (#131; khoảng 2.640 từ trước phần tham khảo, tức khoảng 10 trang double spaced); slide 15 phút (15 slide, có ghi chú cho người nói, số liệu theo essay; Tiến giữ bản slide, không để trong repo).
- **Phần còn lại cần người:** điền MSSV ở bìa essay, cả nhóm đọc chéo, dàn trang Word để đếm trang thật; tập demo có bấm giờ và quay video dự phòng (T82); R3: chạy trên máy thứ hai theo README, Minh chạy lại một bảng EXPERIMENTS, kiểm UI-1 ở mạng không chặn tile.

## Bị chặn / rủi ro
- UI-1 chưa kiểm được trên máy này; nền dự phòng `/api/network` đã có (T56 R8). Kiểm ở R3 trên mạng khác; chuẩn bị video demo.
- MVP 08/11 không đạt đúng hạn (PROGRESS mục 1); không ảnh hưởng kế hoạch mới vì không còn hạn nộp.

## Quyết định
| Quyết định | Trạng thái | Nguồn |
|---|---|---|
| Kế hoạch R0–R4 thay lịch M9 (D18) | **Đã chốt** | Tiến ủy quyền, 14/11 |
| R1: báo cả "giữ thứ tự cũ" và "sắp lại" trên cùng snapshot; cho đóng đoạn trên tour; thêm case "tour không còn khả thi" | **Đã chốt** | Tiến ủy quyền, 14/11 (ROADMAP mục 7) |
| Bỏ khỏi DEMO: nhật ký snapshot, so Dijkstra/A* trên một chặng của tour | **Đã chốt** | D18 |
| Giữ ALT, Dijkstra hai chiều, Or-opt làm phần mở rộng | **Đã chốt** | D17 |
| Lớp node đã mở rộng: tĩnh, có công tắc, mặc định tắt, trace bằng request riêng; không animation | **Đã chốt** | Review UI 14/11 (6/6 vai đồng ý) |
| Giao diện React + Astryx | **Đã merge** (#103) | D15 |
| Ngưỡng snap 150 m | Giả định hiện hành, đã dùng trong mọi thí nghiệm | — |

## Bước tiếp theo
1. Essay: điền MSSV, đọc chéo, dàn trang Word (Times New Roman 12, double spaced, lề 1 inch), đếm trang.
2. T82: tập kịch bản DEMO ba lần có bấm giờ (≤ 4 phút), quay video dự phòng trên máy tải được tile OSM.
3. R3 / T80: clone sạch trên máy thứ hai → tải dữ liệu từ Release → kiểm hash → chạy demo theo README; Minh chạy lại một bảng EXPERIMENTS; kiểm UI-1.

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
- README: phạm vi và kết quả chính đã cập nhật 14/11, mỗi kết quả kèm `run_id`.
- `docs/ALGORITHMS.md`: đã có tóm tắt mọi thuật toán đã cài, gồm ALT, Dijkstra hai chiều, Or-opt (T81, 14/11).
- TOPIC.md là đặc tả gốc 01/10; khi khác PROJECT_BRIEF thì PROJECT_BRIEF được ưu tiên.
