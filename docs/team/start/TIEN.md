# Phiếu bắt đầu — Võ Việt Tiến (@NeitLN)

> **Từ 26/10 phân công đã đổi** (cắt T32; Duy Anh vắng sáng 26/10 rồi quay lại chiều 26/10). Danh sách task dưới đây là của tuần 1; việc hiện tại xem [phiếu giao việc](../../tasks/README.md), [ROADMAP](../../ROADMAP.md) mục 6 và tab Issues.

**Vai trò:** điều phối; snapshot/kịch bản, API, benchmark, tích hợp tour; review phần lớn PR của nhóm.

## Việc điều phối tuần này

1. **Thứ tự merge:** PR #43 (T04) trước, rồi PR onboarding (T05). PR T05 tách ra từ branch T04; khi #43 đã squash-merge, bấm *Update branch* ở PR T05 cho diff gọn lại.
2. **Buổi họp khởi động** theo [KICKOFF.md](../KICKOFF.md); ghi biên bản bằng template *Biên bản họp*.
3. **Theo dõi T01 (Duy Anh) và T02 (Minh):** hai task này chặn gần như toàn bộ tuần 2.
4. **Nếu buổi họp đổi người phụ trách hoặc ước lượng:** sửa `docs/TASKS.md` qua PR, rồi chạy `python scripts/tracking/create_backlog.py --sync` và `python scripts/tracking/setup_project.py --sync`.
5. **Trên giao diện Project:** tạo các view và bật workflow *Item closed → Done* ([tracking/README.md](../../tracking/README.md) mục cuối).

## Task của bạn theo thứ tự

| Issue | Task | Dự kiến | Review bởi |
|---|---|---|---|
| [#42](https://github.com/NeitLN/SaiGo/issues/42) | T04 · Sửa hệ thống theo dõi (PR #43) | 24/10 | Duy Anh |
| [#2](https://github.com/NeitLN/SaiGo/issues/2) | T00 · Môi trường và xác nhận khung chạy | 23–24/10 | Duy Anh |
| [#8](https://github.com/NeitLN/SaiGo/issues/8) | T12 · CLI tìm đường (sau T11) | 25–26/10 | Duy Anh |
| [#13](https://github.com/NeitLN/SaiGo/issues/13) | T31 · GraphML → JSON (cùng Minh) | 25–27/10 | Duy Anh |
| [#15](https://github.com/NeitLN/SaiGo/issues/15) | T33 · Dữ liệu thật + đối chứng (cùng Duy Anh) | 28–29/10 | Minh |
| [#16](https://github.com/NeitLN/SaiGo/issues/16) | T40 · Snapshot ùn tắc theo vùng | 29–30/10 | Duy Anh |
| [#17](https://github.com/NeitLN/SaiGo/issues/17) | T41 · Đóng đường | 30–31/10 | Duy Anh |
| [#20](https://github.com/NeitLN/SaiGo/issues/20) | T51 · API `/api/route` | 31/10–02/11 | Duy Anh |
| [#25](https://github.com/NeitLN/SaiGo/issues/25) | T60 · Benchmark 1.000 truy vấn | 02–03/11 | Duy Anh |
| [#23](https://github.com/NeitLN/SaiGo/issues/23) | T54 · UI đóng đường (cùng Minh) | 03–04/11 | Duy Anh |
| [#27](https://github.com/NeitLN/SaiGo/issues/27) | T62 · Thí nghiệm tăng quy mô | 03–05/11 | Duy Anh |
| [#28](https://github.com/NeitLN/SaiGo/issues/28) | T63 · Thí nghiệm ùn tắc/đóng đường | 04–05/11 | Duy Anh |
| [#30](https://github.com/NeitLN/SaiGo/issues/30) | G1 · Cổng MVP | 05/11 | cả nhóm |
| [#34](https://github.com/NeitLN/SaiGo/issues/34), [#36](https://github.com/NeitLN/SaiGo/issues/36) | T72, T74 · Tour trên API + benchmark (chỉ khi qua G1) | 05–08/11 | Duy Anh |
| [#38](https://github.com/NeitLN/SaiGo/issues/38) | T81 · Đồng bộ tài liệu | 08–10/11 | Duy Anh |

Thêm: điều phối [#31](https://github.com/NeitLN/SaiGo/issues/31) (T65) và [#40](https://github.com/NeitLN/SaiGo/issues/40) (T83).

## T00 (#2): phần còn lại

`scripts\setup_dev.ps1` đã chạy thành công trên máy này ngày 24/10: test `1 passed`, frontend build được. Phiên bản: Python 3.11.9, Node 24.12.0, FastAPI 0.162.0. Còn phải làm:

1. Chạy backend + frontend (ONBOARDING mục 3), mở http://localhost:5173, xác nhận thấy "Server chạy, chưa nạp dataset".
2. Ghi phiên bản và kết quả vào PROGRESS.md, mở PR `Closes #2`.
3. Repo đang ở thư mục có dấu tiếng Việt. App vẫn chạy được nhờ script không dùng `pip install -e`. Nếu sau này OSMnx hoặc công cụ khác lỗi đường dẫn, clone lại vào `C:\dev\SaiGo`.

## Hàng đợi review của bạn

Duy Anh: T01, T10, T11, T20, T21, T22, T70, T71 · Minh: T02, T30, T32, T50, T52, T53, T61 · Bảo: T42, T55, T64, T80. Theo [CONTRIBUTING.md](../../../CONTRIBUTING.md) mục 2: trả lời trong 24 giờ, nhận xét cụ thể, chạy test khi chạy nhanh.
