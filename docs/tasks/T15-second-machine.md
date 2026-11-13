# T15 — Chạy walking skeleton trên máy thứ hai

Tuần mục tiêu: 2 (29/10) · Giao cho: Bảo · Nhánh: `t15-second-machine` (chỉ khi cần sửa tài liệu) · Issue: [#51](https://github.com/NeitLN/SaiGo/issues/51)
Review: Tiến · Người tích hợp: Tiến
Phụ thuộc: T13 và T14 **đã merge vào `main`** (**bắt đầu**) · Ước lượng: 2 giờ

## Mục tiêu
Chứng minh người khác chạy được app chỉ bằng tài liệu, từ code đã merge. Đây là điều kiện để MW được tính là xong.

## Việc cần làm
1. Trên máy của Bảo: `git switch main; git pull`, rồi chạy `scripts\setup_dev.ps1`.
2. Chạy backend + frontend theo ONBOARDING mục 3.
3. Làm lại thao tác ✅ của T14: bấm gần S rồi gần T → 80 s; đảo lại → 100 s.
4. Chụp màn hình, lưu `docs/img/skeleton-bao.png`.
5. Vướng ở bước nào thì mở issue *Lỗi*, rồi sửa ONBOARDING trong PR của task này.

## Sở hữu (chỉ task này được tạo/sửa)
- `docs/img/skeleton-bao.png`
- Phần ONBOARDING cần sửa (nếu có)
- Dòng T15 trong PROGRESS

## Tiêu chí chấp nhận
- [ ] Thấy tuyến 80 s / 100 s trên máy Bảo mà không cần ai sửa tay, hoặc tài liệu đã được sửa cho tới khi chạy được
- [ ] Ghi vào PROGRESS: commit `main` đã chạy, phiên bản Python/Node, thời gian chạy `setup_dev`

## Ngoài phạm vi
Sửa code của T13/T14. Nếu có lỗi code thì mở issue *Lỗi* giao Minh (người làm T13, T14); Tiến điều phối. Bảo đã chạy được bản khung (`/api/health`) ngày 25/10 khi review #55; việc đó chưa tính là xong T15.
