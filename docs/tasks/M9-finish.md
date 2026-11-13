# M9 — Hoàn thiện (G1, T65, T80–T83)

> **14/11 (D18):** lịch và thứ tự ưu tiên trong phiếu này được thay bằng [ROADMAP](../ROADMAP.md) mục 7 (R0–R4). Định nghĩa từng task (mục tiêu, đầu ra, xác minh) vẫn dùng. G1 đã ghi lại ở PROGRESS mục 2.

**Mức Mini (13/11):** việc tài liệu, kiểm tay và viết, dễ sửa lại, không đổi code hay contract. Người làm: Tiến; review: Minh (D14). Mỗi mục: mục tiêu · đầu ra · cách xác minh.

| Task | Mục tiêu | Đầu ra | Xác minh |
|---|---|---|---|
| G1 | Ghi lại điểm kiểm 05/11 đã bị bỏ qua, để hồ sơ không có lỗ | Một dòng PROGRESS: từng điều kiện ở ROADMAP mục 3 đạt/không, kèm PR hoặc `run_id` (đúng đắn: #90, #93; CSV đầu tiên: `20261031-1556-demo-054f300`; đóng đường: #100) | Minh đọc lại, mọi link mở được |
| T65 | Mọi số trong EXPERIMENTS truy ngược được | E2 (đã có, #97), E3 (T62), E4 (T63), E5 (T74): bảng theo EXPERIMENT_PLAN mục 9, mỗi bảng ghi `run_id`, `dataset_id`, máy đo; phần diễn giải tách khỏi số đo | Minh chạy lại **một** bảng trên máy mình, ra số cùng bậc |
| T80 | Chạy được trên máy khác chỉ theo README | Biên bản: clone sạch → tải dữ liệu từ Release → kiểm hash → chạy demo; ghi mọi bước vướng | Minh làm trên máy Minh, khi review T56 |
| T81 | Tài liệu không mô tả điều chưa làm như đã làm | README (cách chạy, kết quả thật, giới hạn), DEMO.md khớp UI mới, ARCHITECTURE khớp API (`/api/network`, `/api/tour`), STATUS cập nhật | Đọc chéo với app đang chạy |
| T82 | Demo ≤ 4 phút, có video dự phòng | Chạy kịch bản DEMO 3 lần có bấm giờ; quay bản tốt nhất; checklist DEMO mục 3 | Video ≤ 4 phút; máy demo có DNS 1.1.1.1 và hotspot dự phòng |
| T83 | Essay 10 trang double spaced | Theo khung TOPIC mục 21.1; số liệu chỉ lấy từ EXPERIMENTS kèm `run_id`; phần giới hạn nêu các thay đổi so với proposal (D1, D11–D15) | Minh đọc chéo; không có câu nào nói về việc dùng công cụ AI (nhóm tự khai báo riêng) |

## Lịch đề xuất (Tiến làm, Minh review)

| Ngày | Việc |
|---|---|
| 13/11 | T62 (code + chạy) |
| 14/11 | T63 |
| 15/11 | T74; T65 phần E3 |
| 16/11 | T65 phần E4, E5; T81; essay phần phương pháp |
| 17/11 | Hạn chót T56 (Minh chạy lại): merge hoặc demo bằng giao diện cũ (#100, #104); **đóng băng tính năng**; T80 |
| 18/11 | T82 (tập + video); slide |
| 19/11 | Thuyết trình |
| 20–22/11 | Essay hoàn chỉnh (T83), nộp |

**Nếu trễ (đã duyệt 13/11):** giữ ưu tiên E3 > E4 ùn tắc > E5 > E4 đóng đoạn; cắt trước bộ không còn đường (T63 C4), rồi đóng đoạn (T63 C3). Không cắt T65, T83.

**Đóng băng tính năng: 17/11** (D16). Sau 17/11 chỉ sửa lỗi, chạy thí nghiệm và viết.
